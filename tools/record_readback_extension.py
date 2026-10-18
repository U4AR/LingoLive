"""Opt-in bounded real-app capture plus approved actor TTS; credentials stay in RAM."""
import argparse,base64,json,os,shutil,subprocess
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1];OUT=Path('/tmp/lingolive-submission-current/extension')
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-live',action='store_true');a=p.parse_args()
if not a.run_live:p.error('--run-live is required')
assert 'Approve added narration' in (ROOT/'docs/submission/DEMO-EXTENSION-APPROVED.md').read_text()
OUT.mkdir(parents=True,exist_ok=True);(OUT/'audio').mkdir(exist_ok=True);shutil.copy2('/tmp/lingolive-submission-current/assets/LingoLive-Media/audio/driver-question.wav',OUT/'audio/driver-question.wav')
meta=Path(subprocess.check_output(['node','-p','require.resolve("playwright-core/package.json")'],cwd=ROOT,text=True).strip());rev=next(x['revision'] for x in json.loads(meta.with_name('browsers.json').read_text())['browsers'] if x['name']=='ffmpeg');cache=OUT/'playwright';binary=cache/('ffmpeg-'+rev)/'ffmpeg-linux';binary.parent.mkdir(parents=True,exist_ok=True)
if not binary.exists():binary.symlink_to(shutil.which('ffmpeg'))
token=subprocess.check_output(['/workspace/.cloud-tools/gcloud','auth','print-access-token'],text=True).strip();r=requests.get('https://secretmanager.googleapis.com/v1/projects/locateassist/secrets/lingolive-private-access/versions/latest:access',headers={'Authorization':'Bearer '+token},timeout=30);r.raise_for_status();code=base64.b64decode(r.json()['payload']['data']).decode();token=''
child=subprocess.Popen(['node',str(ROOT/'tools/record_readback_extension.cjs'),str(OUT)],cwd=ROOT,env=dict(os.environ,PLAYWRIGHT_BROWSERS_PATH=str(cache),XDG_CACHE_HOME=str(OUT/'cache')),stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,bufsize=1);child.stdin.write(json.dumps({'access_code':code})+'\n');child.stdin.flush();code=''
def synth(lines,name):
 file=OUT/name;file.write_text(json.dumps(lines,ensure_ascii=False,indent=2)+'\n');subprocess.run([str(ROOT/'backend/.venv/bin/python'),str(ROOT/'tools/make_submission_audio_v2.py'),'--run-live','--output',str(OUT),'--replies',str(file)],cwd=ROOT,check=True)
def line(id,text,voice='Orus'):return dict(id=id,text=text,voice=voice,language='kn-IN',style='Natural, calm conversational Kannada. A Bengaluru cab driver asking a passenger a question.' if voice=='Charon' else 'A young newcomer politely speaking Kannada at a careful, natural conversational pace. No added words.')
for output in child.stdout:
 print(output.rstrip(),flush=True)
 if output.strip()=='READY_FOR_READBACK_AUDIO':
  d=json.loads((OUT/'selected.json').read_text());synth([line('learner-readback-full',d['text']),line('learner-readback-partial',d['partial']),line('driver-followup','ನೇರವಾಗಿ ರೈಲ್ವೆ ನಿಲ್ದಾಣಕ್ಕೆ ಹೋಗೋಣವಾ?','Charon')],'readback-lines.json');child.stdin.write('capture\n');child.stdin.flush()
code=child.wait();child.stdin.close()
if code:raise SystemExit(code)
d=json.loads((OUT/'recording.json').read_text());assert d['success'];synth([line('learner-final',d['final_reply']['text'])],'final-line.json')
