"""Compose an under-three-minute narrated demo from real browser capture.

Uses ffmpeg/ffprobe and prepared local narration WAVs. No network or model calls.
Scene content stays at recorded speed; narration can be gently sped up to fit.
"""
import argparse,hashlib,json,subprocess,textwrap,wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def clock(seconds):
    value=round(seconds*1000);hours,value=divmod(value,3600000);minutes,value=divmod(value,60000);seconds,ms=divmod(value,1000)
    return f'{hours:02}:{minutes:02}:{seconds:02},{ms:03}'

def ass_clock(seconds):
    return clock(seconds)[:-1].replace(',', '.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/lingolive-submission'))
    args=parser.parse_args();out=args.output.resolve()
    recording=json.loads((out/'recording.json').read_text());assert recording['success'] and len(recording['lessons'])==3
    scenes=json.loads((ROOT/'docs/submission/demo-scenes.json').read_text());assert sum(s['duration'] for s in scenes)<180
    subprocess.run(['node',str(ROOT/'tools/render_submission_frames.cjs'),str(out)],check=True,cwd=ROOT)
    all_cues=[];offset=0;clips=[]
    for spec,row in zip(scenes,recording['scenes']):
        assert spec['id']==row['id'];name=spec['id'];duration=spec['duration'];audio=out/'audio'/f'{name}.wav'
        with wave.open(str(audio),'rb') as wav:audio_seconds=wav.getnframes()/wav.getframerate()
        speed=max(1.0,audio_seconds/(duration-.65));assert speed<1.35,'Shorten narration instead of excessively speeding it up'
        spoken_duration=audio_seconds/speed;words=spec['narration'].split();cues=[];total=len(words)
        for start in range(0,total,13):
            end=min(total,start+13);cues.append((.3+spoken_duration*start/total,.3+spoken_duration*end/total,'\n'.join(textwrap.wrap(' '.join(words[start:end]),width=90))))
        inputs=['-ss',str(row['start_seconds']),'-i',str(out/'raw/demo.webm'),'-i',str(audio),'-loop','1','-i',str(out/'scenes'/f'{name}-background.png')]
        audio_filter=f'[1:a]atempo={speed:.5f},adelay=300,apad[narration]'
        if name=='speech':
            speech_start=recording['microphone_start_seconds']-row['start_seconds']+3
            inputs+=['-i',str(out/'audio/spoken-input.wav')]
            audio_filter+=f';[3:a]adelay={round(speech_start*1000)},apad[spoken];[narration][spoken]amix=inputs=2:normalize=0[a]'
            with wave.open(str(out/'audio/spoken-input.wav'),'rb') as wav:spoken_seconds=wav.getnframes()/wav.getframerate()
            assert speech_start>spoken_duration+.3,'Narration must finish before the demonstrated phrase is audible'
            cues.append((speech_start,speech_start+spoken_seconds,'[Synthesized microphone input]\nWould you like a window seat or an aisle seat?'))
        else:audio_filter+=';[narration]anull[a]'
        subtitle=out/'scenes'/f'{name}.srt'
        subtitle.write_text('\n\n'.join(f'{i}\n{clock(start)} --> {clock(end)}\n{text}' for i,(start,end,text) in enumerate(cues,1))+'\n')
        for start,end,text in cues:all_cues.append((offset+start,offset+end,text))
        ass=subtitle.with_suffix('.ass')
        header='''[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720
WrapStyle: 2
[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,DejaVu Sans,20,&H00303B19,&H00303B19,&H00E7F1ED,&H00E7F1ED,0,0,0,0,100,100,0,0,1,1,0,2,30,30,10,1
[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
'''
        lines=[]
        for start,end,text in cues:
            value=text.replace('\\','\\\\').replace('{','').replace('}','').replace('\n',r'\N')
            lines.append(f'Dialogue: 0,{ass_clock(start)},{ass_clock(end)},Default,,0,0,0,,{value}')
        ass.write_text(header+'\n'.join(lines)+'\n')
        filters=f"[0:v]fps=24,scale=1000:620[ui];[2:v][ui]overlay=260:30:shortest=1,ass='{ass}'[v];{audio_filter}"
        clip=out/'scenes'/f'{name}.mp4';clips.append(clip)
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',*inputs,'-filter_complex',filters,'-map','[v]','-map','[a]','-t',str(duration),'-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-c:a','aac','-b:a','96k','-ar','48000','-ac','2','-threads','2',str(clip)],check=True)
        offset+=duration;print('Rendered '+name,flush=True)
    (out/'LingoLive-Demo.srt').write_text('\n\n'.join(f'{i}\n{clock(start)} --> {clock(end)}\n{text}' for i,(start,end,text) in enumerate(all_cues,1))+'\n')
    concat=out/'scenes/concat.txt';concat.write_text(''.join("file '"+str(p)+"'\n" for p in clips))
    video=out/'LingoLive-Demo.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',str(video)],check=True)
    metadata=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(video)],text=True))
    actual=float(metadata['format']['duration']);assert 0<actual<180
    assert any(s['codec_name']=='h264' and s['width']==1280 and s['height']==720 for s in metadata['streams'])
    assert any(s['codec_name']=='aac' for s in metadata['streams'])
    subprocess.run(['ffmpeg','-hide_banner','-v','error','-i',str(video),'-f','null','-'],check=True)
    report={'file':video.name,'bytes':video.stat().st_size,'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'seconds':actual,'video':'H.264 1280x720 / 24fps','audio':'AAC stereo / English synthetic narration','burned_english_captions':True,'sidecar_captions':'LingoLive-Demo.srt','decode_verified':True,'scene_count':len(scenes),'live_google_lessons':len(recording['lessons']),'maximum_live_lessons':3,'google_mocked':False,'physical_microphone':False,'synthetic_speech_disclosed':True,'visual_speed':'Recorded speed; scene waits retained, no model result substituted','voice':{'model':'rhasspy/piper-voices en_US-ljspeech-high','model_sha256':'5d4f08ba6a2a48c44592eed3ce56bf85e9de3dd4e20df90541ae68a8310c029a','dataset_license':'public domain per model card','model_card':'https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/ljspeech/high/MODEL_CARD'},'submission_status':'Prepared; no Hack2skill receipt or accepted video-host link claimed'}
    (out/'video-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
