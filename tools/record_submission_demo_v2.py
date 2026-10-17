"""Run approved v2 live capture; normal SDK auth, bounded real model requests."""
import argparse,base64,json,os,shutil,subprocess
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-live',action='store_true');p.add_argument('--output',type=Path,default=Path('/tmp/lingolive-video-v2'));a=p.parse_args()
 if not a.run_live:p.error('--run-live is required for paid Google operations')
 assert json.loads((ROOT/'docs/submission/submission.json').read_text())['demo_v2']['approval_status']=='approved'
 r=requests.get('https://lingolive-358650584819.us-central1.run.app/health',timeout=30);r.raise_for_status();assert r.json()['version']=='1.9'
 assert all((a.output/'audio'/name).is_file() for name in ['driver-question-mic.wav','learner-english-mic.wav','cafe-question-mic.wav','shop-question-mic.wav'])
 token=subprocess.check_output([shutil.which('gcloud') or '/workspace/.cloud-tools/gcloud','auth','print-access-token'],text=True).strip();r=requests.get('https://secretmanager.googleapis.com/v1/projects/locateassist/secrets/lingolive-private-access/versions/latest:access',headers={'Authorization':'Bearer '+token},timeout=30);r.raise_for_status();code=base64.b64decode(r.json()['payload']['data']).decode();token=''
 package=Path(subprocess.check_output(['node','-p','require.resolve("playwright-core/package.json")'],text=True,cwd=ROOT).strip());metadata=json.loads(package.with_name('browsers.json').read_text());rev=next(x['revision'] for x in metadata['browsers'] if x['name']=='ffmpeg');cache=a.output/'playwright-browsers';binary=cache/('ffmpeg-'+rev)/'ffmpeg-linux';binary.parent.mkdir(parents=True,exist_ok=True)
 if not binary.exists():binary.symlink_to(shutil.which('ffmpeg'))
 env=dict(os.environ,PLAYWRIGHT_BROWSERS_PATH=str(cache.resolve()),XDG_CACHE_HOME=str(a.output/'cache'))
 done=subprocess.run(['node',str(ROOT/'tools/record_submission_demo_v2.cjs'),str(a.output)],cwd=ROOT,env=env,input=json.dumps({'access_code':code}),text=True);code=''
 if done.returncode==0:
  recording=json.loads((a.output/'recording.json').read_text())
  lines=[dict(id='learner-'+key,text=v['text'],language='kn-IN',voice='Orus',style='A young newcomer politely saying this Kannada phrase. Clear natural pronunciation at a slightly careful conversational pace, approximately 125 words per minute. No added words or exaggerated accent.') for key,v in recording['selected'].items()]
  (a.output/'reply-lines.json').write_text(json.dumps(lines,ensure_ascii=False,indent=2)+'\n')
 return done.returncode
if __name__=='__main__':raise SystemExit(main())
