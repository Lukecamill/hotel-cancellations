"""Compare Ubuntu test collection and source files with the recorded Mac inventory."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parents[1]
os.chdir(root)
expected=json.loads((root/'config/stage8-test-inventory.json').read_text())
# Fail before running if a test or Python source file differs or is missing.
actual_tests={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/'tests').glob('*.py'))}
actual_sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/'src/hotel_cancel').glob('*.py'))}
assert actual_tests==expected['test_sha256'], 'Test files differ from the Mac inventory'
assert actual_sources==expected['source_sha256'], 'Python source files differ from the Mac inventory'
code='''
import json
from pathlib import Path
import pytest
class Inventory:
    def pytest_collection_finish(self, session):
        value={'collected': len(session.items), 'nodeids': [item.nodeid for item in session.items]}
        Path('/project/docs/evidence/stage8-ubuntu/test-inventory.json').write_text(json.dumps(value,indent=2)+'\\n')
raise SystemExit(pytest.main(['--collect-only','-q'],plugins=[Inventory()]))
'''
output=root/'docs/evidence/stage8-ubuntu'
output.mkdir(parents=True,exist_ok=True)
subprocess.run(['docker','run','--rm','--user',f'{os.getuid()}:{os.getgid()}',
                '-e','PYTHONPATH=/project/src','-v',f'{root}:/project','-w','/project',
                'hotel-cancel:stage8-check','python','-c',code],check=True)
actual=json.loads((output/'test-inventory.json').read_text())
assert actual['nodeids']==expected['nodeids'], 'Collected test identifiers differ'
result=dict(status='PASS',collected=actual['collected'],all_test_ids_identical=True,
            all_test_files_identical=True,all_python_sources_identical=True,
            previous_difference='Diary 1 checkout-date audit module and four tests were omitted from the Stage 8 transfer',
            added_tests=[n for n in actual['nodeids'] if n.startswith('tests/test_stay_audit.py::')])
(output/'test-parity.json').write_text(json.dumps(result,indent=2)+'\n')
print('STAGE8_TEST_PARITY_VERIFIED\n'+json.dumps(result,indent=2))
