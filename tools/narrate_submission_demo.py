"""Create local synthetic narration using the verified public-domain-data voice.

Optional video tooling only: Piper is not a dependency of the deployed app.
The model and matching JSON config must already be downloaded; no network here.
"""
import argparse,hashlib,json,subprocess,wave
from pathlib import Path
from piper import PiperVoice

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('/tmp/lingolive-submission'))
    args=parser.parse_args()
    assert hashlib.sha256(args.model.read_bytes()).hexdigest()=='5d4f08ba6a2a48c44592eed3ce56bf85e9de3dd4e20df90541ae68a8310c029a'
    voice=PiperVoice.load(str(args.model));root=Path(__file__).resolve().parents[1]
    audio=args.output/'audio';audio.mkdir(parents=True,exist_ok=True)
    for scene in json.loads((root/'docs/submission/demo-scenes.json').read_text()):
        with wave.open(str(audio/(scene['id']+'.wav')),'wb') as target:voice.synthesize_wav(scene['narration'],target)
    with wave.open(str(audio/'spoken-input.wav'),'wb') as target:voice.synthesize_wav('Would you like a window seat or an aisle seat?',target)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(audio/'spoken-input.wav'),'-af','adelay=3000,apad=pad_dur=6','-ac','1','-ar','48000',str(audio/'microphone.wav')],check=True)

if __name__=='__main__':main()
