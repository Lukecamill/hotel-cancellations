"""Grounding-contract evaluation; deterministic facts, not an LLM experiment."""
import argparse
import json
from pathlib import Path

from rdflib import Graph
from hotel_cancel.knowledge import KB_DIR, policy_facts, membership, ROOT, validate_graph
from hotel_cancel.quality_gate import sha


def semantic_facts(graph, case):
    if case['kind']=='membership':
        value=membership(graph,case['code'],case['at'])
        return None if value is None else {'isEU':value}
    return policy_facts(graph,case['kind'],case['code'],case['at'])


def render(context, facts):
    # Copy numerical facts from the context only. Semantic codes are never instructions.
    return dict(hotel=context['hotel'],arrival=context['arrival'],oversell_rooms=context['oversell_rooms'],
                expected_releases=context['expected_releases'],semantic_facts=facts,
                semantic_status='supported' if facts is not None else 'unknown: human review',
                message_to_guest=None)


def evaluate(graph,cases):
    reports={};outputs=[]
    for mode in ['codes only (abstain)','codes + temporal KB']:
        asserted=correct=covered=available=exact=numeric=0
        for i,case in enumerate(cases):
            context=dict(hotel='City Hotel' if i%2==0 else 'Resort Hotel',arrival='2017-08-15',
                         oversell_rooms=3 if i%2==0 else 0,expected_releases=4.269602 if i%2==0 else .463106)
            facts=semantic_facts(graph,case) if mode=='codes + temporal KB' else None
            value=render(context,facts)
            if case['expected'] is not None:available+=1
            if facts is not None:
                covered+=1
                for prop,answer in facts.items():
                    asserted+=1
                    correct+=int(case['expected'] is not None and case['expected'].get(prop)==answer)
            exact+=int(facts==case['expected'])
            numeric+=int(all(value[k]==v for k,v in context.items()))
            outputs.append(dict(mode=mode,id=case['id'],expected=case['expected'],output=value))
        reports[mode]=dict(cases=len(cases),supported_cases=available,semantic_cases_answered=covered,
                           semantic_coverage=covered/available,asserted_semantic_claims=asserted,
                           correct_semantic_claims=correct,unsupported_semantic_claims=asserted-correct,
                           semantic_claim_precision=correct/asserted if asserted else None,
                           exact_case_answers=exact,numeric_context_exact_cases=numeric)
    return reports,outputs


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',default=str(ROOT/'docs/evidence/stage10/briefing'))
    args=p.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    graph=Graph().parse(KB_DIR/'hotel.ttl',format='turtle');cases=json.loads((KB_DIR/'briefing-golden.json').read_text())
    if not validate_graph(graph)[0]:raise ValueError('Knowledge graph fails SHACL')
    reports,outputs=evaluate(graph,cases)
    kb=reports['codes + temporal KB']
    if kb['exact_case_answers']!=len(cases) or kb['unsupported_semantic_claims']!=0:raise ValueError('Grounding factuality check failed')
    result=dict(status='VERIFIED',scope='deterministic grounding contract; no language model run',reports=reports,
                golden_sha256=sha(KB_DIR/'briefing-golden.json'),knowledge_sha256=sha(KB_DIR/'hotel.ttl'),
                limitations=['Synthetic context numbers and curated semantic cases, not real guest messages',
                             'No-KB baseline abstains rather than inventing semantic meanings',
                             'Does not establish LLM factuality or complete the Stage 13 30-night evaluation',
                             'Unknown and expired mappings produce explicit abstention, not guessed facts'])
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'cases.json').write_text(json.dumps(outputs,indent=2)+'\n');print(json.dumps(result,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
