"""One bounded independent audio transcription check; no human-review claim."""
import shutil
import argparse,base64,json,subprocess
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-live',action='store_true');p.add_argument('--sources',action='store_true');p.add_argument('--output',type=Path,default=Path('/tmp/lingolive-video-v2'));a=p.parse_args()
 if not a.run_live:p.error('--run-live is required')
 assert json.loads((ROOT/'docs/submission/submission.json').read_text())['demo_v2']['approval_status']=='approved'
 names=['driver-question','cafe-question','shop-question'] if a.sources else ['learner-cab','learner-express','learner-cafe','learner-place']
 parts=[{'text':'Listen to the speech clips in order. Transcribe the exact words you hear in their native script; identify language and whether speech is clear. No translation or inferred missing words. Return JSON {"clips":[{"language":"...","text":"...","clear":true}]}.'}]
 for name in names:parts.extend([{'text':'Next clip: '+name},{'inlineData':{'mimeType':'audio/wav','data':base64.b64encode((a.output/'audio'/(name+'.wav')).read_bytes()).decode()}}])
 token=subprocess.check_output([shutil.which('gcloud') or '/workspace/.cloud-tools/gcloud','auth','print-access-token'],text=True).strip();r=requests.post('https://aiplatform.googleapis.com/v1/projects/locateassist/locations/global/publishers/google/models/gemini-3.1-flash-lite:generateContent',headers={'Authorization':'Bearer '+token},json={'contents':[{'role':'user','parts':parts}],'generationConfig':{'responseMimeType':'application/json','maxOutputTokens':1500,'thinkingConfig':{'thinkingLevel':'minimal'}}},timeout=60);r.raise_for_status();d=r.json();result=json.loads(''.join(x.get('text','') for x in d['candidates'][0]['content']['parts'] if not x.get('thought')));assert len(result['clips'])==len(names)
 result.update(files=names,independent_model='gemini-3.1-flash-lite',human_native_review=False,source='Generated speech, without supplying expected transcripts to the check model');(a.output/('source-voice-check.json' if a.sources else 'reply-voice-check.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
