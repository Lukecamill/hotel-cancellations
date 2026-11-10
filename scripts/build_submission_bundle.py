"""Prepare reviewable source/runtime archives; exclude data, secrets and Git history."""
import argparse,hashlib,io,json,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def info_clean(info):
 info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
 return info
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args()
 out=Path(args.output).expanduser().resolve();out.mkdir(parents=True,exist_ok=True)
 tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0');names={n for n in tracked if n and (ROOT/n).is_file()}
 new=['docs/revenue-manager-recommendation.md','docs/submission-checklist.md','docs/reproduce-final.md','docs/stage14-final-verification.md',
      'scripts/submission_audit.py','scripts/build_submission_bundle.py','output/pdf/revenue-manager-recommendation.pdf']
 names.update(new);names.update(str(p.relative_to(ROOT)) for p in (ROOT/'docs/evidence/stage14').rglob('*') if p.is_file())
 for name in names:
  path=Path(name)
  if path.parts[0] in ['data','models','artifacts','.git','.venv','.venv-tracking'] or path.name=='.env' or path.name.startswith('.env.') or 'id_ed25519' in name:
   raise ValueError('Excluded private/local path in source set: '+name)
  if any(line.strip().startswith(b'-----BEGIN PRIVATE KEY-----') for line in (ROOT/name).read_bytes().splitlines()):raise ValueError('Private key content: '+name)
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 status=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True)
 manifest=dict(source_commit=commit,working_tree_status=status,tested_commit=json.loads((ROOT/'docs/evidence/stage14/clean-clone-summary.json').read_text())['tested_commit'],
  uncommitted_overlay=bool(status.strip()),files={n:sha(ROOT/n) for n in sorted(names)},production_authorized=False,
  limitations='Quality failures and unconfirmed final rubric/diary requirements remain; see submission checklist')
 archive=out/'hotel-task19-source.tar.gz'
 with tarfile.open(archive,'w:gz') as tar:
  for n in sorted(names):tar.add(ROOT/n,arcname=n,filter=info_clean)
  data=(json.dumps(manifest,indent=2)+'\n').encode();i=tarfile.TarInfo('SUBMISSION-MANIFEST.json');i.size=len(data);tar.addfile(i,io.BytesIO(data))
 runtime=ROOT/'models/serving';m=json.loads((runtime/'manifest.json').read_text())
 reference=json.loads((ROOT/'config/stage11-policy-reference.json').read_text())['bundle_sha256']
 if m['sha256']!=reference:raise ValueError('Reference runtime differs from pinned historical audit pair')
 for n,h in reference.items():
  if sha(runtime/n)!=h:raise ValueError('Runtime hash mismatch: '+n)
 artifact=out/'reference-runtime.tar.gz'
 with tarfile.open(artifact,'w:gz') as tar:
  for n in ['booking_model.joblib','policy_state.joblib','manifest.json']:tar.add(runtime/n,arcname='models/serving/'+n,filter=info_clean)
 checksums={p.name:sha(p) for p in [archive,artifact]}
 (out/'SHA256SUMS.txt').write_text(''.join(h+'  '+n+'\n' for n,h in checksums.items()))
 (out/'submission-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 with tarfile.open(archive) as tar:
  for n,h in manifest['files'].items():
   if hashlib.sha256(tar.extractfile(n).read()).hexdigest()!=h:raise ValueError('Archive verification failed: '+n)
 print(json.dumps(dict(files=len(names),archives=checksums,uncommitted_overlay=manifest['uncommitted_overlay']),indent=2))
if __name__=='__main__':main()
