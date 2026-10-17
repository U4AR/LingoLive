"""Opt-in demo capture: three real lessons and one short synthesized speech stream.

Use the existing normal Cloud SDK login. Credentials stay in RAM and stdin;
never record the sign-in screen with a real credential populated.
"""
import argparse,base64,json,os,shutil,subprocess
from pathlib import Path
import requests

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-live',action='store_true')
    parser.add_argument('--output',type=Path,default=Path('/tmp/lingolive-submission'))
    args=parser.parse_args()
    if not args.run_live:parser.error('--run-live is required for real Google calls')
    if not (args.output/'audio/microphone.wav').is_file():parser.error('Prepare the disclosed synthesized microphone WAV first')
    sdk=shutil.which('gcloud') or '/workspace/.cloud-tools/gcloud'
    token=subprocess.check_output([sdk,'auth','print-access-token'],text=True).strip()
    response=requests.get('https://secretmanager.googleapis.com/v1/projects/locateassist/secrets/lingolive-private-access/versions/latest:access',headers={'Authorization':'Bearer '+token},timeout=30)
    response.raise_for_status();code=base64.b64decode(response.json()['payload']['data']).decode().strip()
    root=Path(__file__).resolve().parents[1]
    # Reuse the installed, trusted system ffmpeg instead of downloading another
    # encoder. Only this recording's temporary Playwright cache is affected.
    package=Path(subprocess.check_output(['node','-p','require.resolve("playwright-core/package.json")'],text=True,cwd=root).strip())
    metadata=json.loads(package.with_name('browsers.json').read_text())
    revision=next(b['revision'] for b in metadata['browsers'] if b['name']=='ffmpeg')
    cache=args.output/'playwright-browsers';binary=cache/('ffmpeg-'+revision)/'ffmpeg-linux'
    binary.parent.mkdir(parents=True,exist_ok=True)
    if not binary.exists():binary.symlink_to(shutil.which('ffmpeg'))
    child_env=dict(os.environ,PLAYWRIGHT_BROWSERS_PATH=str(cache.resolve()))
    result=subprocess.run(['node',str(root/'tools/record_submission_demo.cjs'),str(args.output)],input=json.dumps({'access_code':code}),text=True,cwd=root,env=child_env)
    return result.returncode

if __name__=='__main__':raise SystemExit(main())
