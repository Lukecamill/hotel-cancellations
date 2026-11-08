"""Reproduce measured inputs and explicitly assumed economics for Diary 1."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess

import yaml

root=Path(__file__).resolve().parents[1]
inputs={name:root/name for name in ['config/diary1-comparison.json','config/config.yaml',
                                    'docs/evidence/stage7/performance.json','docs/evidence/stage7/batch.json',
                                    'docs/evidence/stage7/replay/policy-summary.csv']}
assumptions=json.loads(inputs['config/diary1-comparison.json'].read_text())
settings=yaml.safe_load(inputs['config/config.yaml'].read_text())
performance=json.loads(inputs['docs/evidence/stage7/performance.json'].read_text())
batch=json.loads(inputs['docs/evidence/stage7/batch.json'].read_text())
hotels=len(settings['hotels']);wage=assumptions['reviewer_cost_eur_per_hour']
minutes=assumptions['review_minutes_per_hotel_per_day']
review=hotels*minutes*wage/60
walk=settings['walk_cost_eur']
sensitivity=[]
for minutes_i in assumptions['review_minutes_sensitivity']:
    saving=hotels*minutes_i*wage/60
    for w in assumptions['walking_cost_sensitivity_eur']:
        sensitivity.append(dict(review_minutes_per_hotel=minutes_i,assumed_hourly_cost_eur=wage,
                                assumed_daily_review_cost_eur=saving,walking_cost_eur=w,
                                break_even_extra_walks_per_day=saving/w,
                                break_even_days_per_extra_walk=w/saving))
with inputs['docs/evidence/stage7/replay/policy-summary.csv'].open() as stream:
    costs=list(csv.DictReader(stream))
chosen=[r for r in costs if r['policy']!='no overbooking']
none=[r for r in costs if r['policy']=='no overbooking']
report=dict(scope='architecture_comparison_not_a_new_policy_experiment',
            base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
            working_tree_dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip()),
            assumptions=assumptions,
            measured=dict(booking_burst_p95_seconds=performance['phases'][0]['p95_seconds'],
                          shifted_burst_p95_seconds=performance['phases'][1]['p95_seconds'],
                          measured_requests=sum(x['sent'] for x in performance['phases']),
                          errors=sum(x['errors'] for x in performance['phases']),
                          nightly_batch_seconds=batch['batch_seconds'],nightly_example_bookings=81),
            derived=dict(hotels=hotels,assumed_review_cost_eur_per_day=review,
                         configured_walk_cost_eur=walk,
                         break_even_extra_walks_per_day=review/walk,
                         break_even_days_per_extra_walk=walk/review,
                         baseline_2017_policy_cost_per_hotel_night={r['hotel']:float(r['cost_per_night']) for r in chosen},
                         baseline_2017_no_overbooking_cost_per_hotel_night={r['hotel']:float(r['cost_per_night']) for r in none},
                         baseline_2017_pair_policy_cost_per_night=sum(float(r['cost_per_night']) for r in chosen),
                         baseline_2017_pair_no_overbooking_cost_per_night=sum(float(r['cost_per_night']) for r in none)),
            sensitivity=sensitivity,
            limitations=['No measured manager review time or labour rate','No measured platform electricity/hardware cost',
                         'Automatic inventory connector and extra control costs are unimplemented/unpriced',
                         'No measured reduction in walking from human approval',
                         'If both options accept identical quantities, the simulated policy losses are identical',
                         'Policy costs are Jan-Aug 2017 reference-policy replay, not Stage 5 validation or real hotel revenue'],
            input_sha256={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in inputs.items()},
            calculation_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
out=root/'docs/evidence/diary1';out.mkdir(parents=True,exist_ok=True)
(out/'pattern-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
with (out/'pattern-cost-sensitivity.csv').open('w',newline='') as stream:
    writer=csv.DictWriter(stream,fieldnames=list(sensitivity[0]));writer.writeheader();writer.writerows(sensitivity)
assert review==2.5 and report['derived']['break_even_days_per_extra_walk']==100
print(json.dumps({'measured':report['measured'],'derived':report['derived']},indent=2))
