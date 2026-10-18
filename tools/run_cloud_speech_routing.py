"""Opt-in live check. Existing operator auth and host code stay in RAM/stdin."""
import argparse,base64,json,shutil,subprocess
from pathlib import Path
import requests
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-live',action='store_true');a=p.parse_args()
if not a.run_live:p.error('--run-live is required (two lessons / four model generation calls)')
root=Path(__file__).resolve().parents[1];url=json.loads((root/'validation/cloud-v1.10-staged-deployment.json').read_text())['url'];sdk=shutil.which('gcloud') or '/workspace/.cloud-tools/gcloud';token=subprocess.check_output([sdk,'auth','print-access-token'],text=True).strip()
r=requests.get('https://secretmanager.googleapis.com/v1/projects/locateassist/secrets/lingolive-private-access/versions/latest:access',headers={'Authorization':'Bearer '+token},timeout=30);r.raise_for_status();code=base64.b64decode(r.json()['payload']['data']).decode();token=''
result=subprocess.run(['node',str(root/'tools/check_cloud_speech_routing.cjs')],input=json.dumps({'url':url,'access_code':code}),text=True,cwd=root);code='';raise SystemExit(result.returncode)
