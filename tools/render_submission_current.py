"""Extend approved demo to 3–4 minutes using real readback capture and cached audio.

No model calls. Preserve natural capture/audio speed and the capture assertion
failure as evidence. Corrected independent verification compares actual ASR words,
which include a full stop, rather than the intended TTS script without punctuation.
"""
import argparse,copy,hashlib,json,os,subprocess,textwrap,wave
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from render_submission_video_v2 import run,speech_gain,clock,metadata
from check_submission_audio_v2 import verify_audio
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,default=Path('/tmp/lingolive-submission-current'));a=p.parse_args();root=a.directory;ext=root/'extension';out=root/'final';out.mkdir(exist_ok=True);r=json.loads((ext/'recording.json').read_text());ev={e['id']:e for e in r['events']}
assert not r['google_mocked'] and not r['page_errors']
for id in ('full','partial'):
 assert ev[id]['status']=='spoken' and ev[id]['new_lesson_requests']==0
 assert any(t['text']==ev[id]['transcript'] and t['speaker'] in ('user','likely_user') for t in r['requests'][-1]['payload']['recent_turns'])
assert ev['followup']['new_lesson_requests']==1
verification={'original_capture_success':r['success'],'original_capture_error':r.get('error'),'corrected_context_check_passed':True,'correction':'Compare recorded ASR transcript, not intended TTS script: punctuation differs. Both actual full and partial transcripts are in the next request as learner turns.','actual_readback_zero_lesson_requests':True,'partial_reason':ev['partial']['reason'],'real_google_calls':True,'followup_asr_limitation':'Kannada speech rendered as Telugu-script Vangi railway station; actual app output remains visible. No ASR/model output replaced.','new_capture_or_tts_calls_in_renderer':0}
(out/'readback-verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2)+'\n')
raw=next((ext/'raw').glob('*.webm'));pixels=subprocess.check_output(['ffmpeg','-v','error','-i',str(raw),'-vf','fps=25,crop=20:20:0:0,scale=1:1','-f','rawvideo','-pix_fmt','rgb24','-']);frames=[i/25 for i in range(len(pixels)//3) if pixels[3*i]>180 and pixels[3*i+1]<80 and pixels[3*i+2]<80];assert len(frames)>=5;offset=frames[0]-r['marker_on']/1000
# Presentation outside the unchanged recorded phone viewport.
im=Image.new('RGB',(1920,1080),'#f5f6f0');d=ImageDraw.Draw(im);font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';bold='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def text(x,y,s,size=32,color='#234b3d',heavy=False):d.multiline_text((x,y),s,font=ImageFont.truetype(bold if heavy else font,size),fill=color,spacing=15)
text(120,49,'Real Google responses · Simulated microphone · AI voices',22,'#6b7f70');text(120,137,'SPEAK. KEEP THE CONVERSATION MOVING.',25);text(120,215,'Your words.\nThe next turn.',78,heavy=True);text(120,425,'Reads and partial repeats stay in context.\nSuggested replies remain available.',31,'#607568');d.rounded_rectangle((1288,37,1812,1041),radius=35,fill='#dfe7d8',outline='#b6c7b0',width=3);im.save(out/'extension-frame.png')
D=55;parts=[('full',r['capture_start']/1000,ev['partial']['start']/1000,0,20.5),('partial',ev['partial']['start']/1000,ev['followup']['start']/1000,20.5,16.5),('followup',ev['followup']['start']/1000,None,37,18)]
clips=[]
raw_seconds=float(metadata(raw)['format']['duration'])
for id,start,end,at,length in parts:
 raw_start=start+offset;real_length=(end-start) if end else raw_seconds-raw_start
 file=out/(id+'-phone.mp4');run(['-ss',str(raw_start),'-i',str(raw),'-an','-vf',f'trim=duration={real_length},setpts=PTS-STARTPTS,fps=25,tpad=stop_mode=clone:stop_duration={length},trim=duration={length}','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-threads','2',str(file)]);clips.append(file)
concat=out/'phones.txt';concat.write_text(''.join("file '"+str(c)+"'\n" for c in clips));run(['-f','concat','-safe','0','-i',str(concat),'-c','copy',str(out/'phone.mp4')])
lines={l['id']:l['text'] for l in json.loads((root/'extension-lines.json').read_text())};events=[]
def voice(id,start,text,role='Narrator'):
 f=ext/'audio'/(id+'.wav')
 with wave.open(str(f)) as w:seconds=w.getnframes()/w.getframerate()
 assert start+seconds<D
 events.append(dict(id=id,file=str(f),start=start,end=round(start+seconds,3),text=text,role=role,gain_db=speech_gain(f)))
voice('learner-readback-full',(ev['full']['input_start']-r['capture_start'])/1000,r['selected']['translation'],'Learner · Kannada')
voice('narration-repeat-1',5.7,lines['narration-repeat-1'])
voice('learner-readback-partial',20.5+(ev['partial']['input_start']-ev['partial']['start'])/1000,'Bengaluru railway','Learner · Kannada · partial reply')
voice('narration-repeat-2',25.4,lines['narration-repeat-2'])
voice('driver-followup',37+(ev['followup']['input_start']-ev['followup']['start'])/1000,'Shall we go straight to the railway station?','Driver · Kannada')
voice('narration-repeat-3',41.8,lines['narration-repeat-3'])
header='''[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Caption,DejaVu Sans,37,&H003D4B23,&H003D4B23,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,1,120,780,72,1\nStyle: Dialogue,DejaVu Sans,44,&H003D4B23,&H003D4B23,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,120,785,550,1\nStyle: Notice,DejaVu Sans,23,&H003D4B23,&H003D4B23,&H00F0F6F5,&H00F0F6F5,0,0,0,0,100,100,0,0,3,8,0,7,120,785,805,1\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n'''
cues=[];ass=[]
for e in events:
 chunks=textwrap.wrap(e['text'],width=65 if e['role']=='Narrator' else 38)
 if e['role']=='Narrator':
  for i,c in enumerate(chunks):
   start=e['start']+(e['end']-e['start'])*i/len(chunks);end=e['start']+(e['end']-e['start'])*(i+1)/len(chunks);cues.append(dict(start=start,end=end,text=c,role=e['role']));ass.append(f'Dialogue: 2,{clock(start,True)},{clock(end,True)},Caption,,0,0,0,,{c}')
 else:
  cues.append({k:e[k] for k in ('start','end','text','role')});label=r'{\fs24\b1}'+e['role'].upper()+r'{\fs44\b0}\N'+r'\N'.join(chunks);ass.append(f"Dialogue: 1,{clock(e['start'],True)},{clock(e['end']+1,True)},Dialogue,,0,0,0,,{label}")
ass.append('Dialogue: 3,0:00:44.00,0:00:55.00,Notice,,0,0,0,,Speech misheard — actual transcription shown.');(out/'extension.ass').write_text(header+'\n'.join(ass)+'\n')
args=['-loop','1','-framerate','25','-i',str(out/'extension-frame.png'),'-i',str(out/'phone.mp4')];filters=['[1:v]scale=500:978[phone]','[0:v][phone]overlay=1300:50,ass='+str(out/'extension.ass')+'[v]'];labels=[]
for i,e in enumerate(events):
 args+=['-i',e['file']];filters.append(f"[{i+2}:a]aresample=48000,asetpts=N/SR/TB,volume={e['gain_db']}dB,adelay={round(e['start']*1000)}:all=1,asetpts=N/SR/TB,apad,atrim=duration={D}[a{i}]");labels.append(f'[a{i}]')
filters.append(''.join(labels)+f'amix=inputs={len(events)}:normalize=0:duration=longest,alimiter=limit=0.95:level=false:latency=true[a]')
run([*args,'-filter_complex_threads','1','-filter_complex',';'.join(filters),'-map','[v]','-map','[a]','-t',str(D),'-r','25','-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-ar','48000','-ac','2','-threads','2',str(out/'extension.mp4')])
old=root/'LingoLive-Demo.mp4';target=out/'LingoLive-Demo.mp4'
run(['-reinit_filter','0','-i',str(old),'-i',str(out/'extension.mp4'),'-filter_complex_threads','1','-filter_complex','[0:v]split=2[x][y];[0:a]asplit=2[ax][ay];[x]trim=end=78,setpts=PTS-STARTPTS[v0];[ax]atrim=end=78,asetpts=PTS-STARTPTS[a0];[y]trim=start=78,setpts=PTS-STARTPTS[v2];[ay]atrim=start=78,asetpts=PTS-STARTPTS[a2];[1:v]setpts=PTS-STARTPTS[v1];[1:a]asetpts=PTS-STARTPTS[a1];[v0][a0][v1][a1][v2][a2]concat=n=3:v=1:a=1[v][a]','-map','[v]','-map','[a]','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-r','25','-c:a','aac','-b:a','128k','-ar','48000','-ac','2','-threads','2','-movflags','+faststart',str(target)])
timeline=json.loads((root/'assets/LingoLive-Media/edit-timeline.json').read_text())
for s in timeline['scenes']:
 if s['offset']>=78:s['offset']+=D
 for e in s['audio']:e['file']=str(root/'assets/LingoLive-Media/audio'/Path(e['file']).name)
timeline['scenes'].append(dict(id='readback',offset=78,duration=D,audio=events,cues=cues));timeline['scenes'].sort(key=lambda s:s['offset']);timeline['seconds']=float(metadata(target)['format']['duration']);timeline['extension_alignment']={'raw_offset_seconds':offset,'marker_frames':frames,'method':'Discarded red marker, 25fps; original speed and complete waits retained, with end-frame holds.'};(out/'edit-timeline.json').write_text(json.dumps(timeline,ensure_ascii=False,indent=2)+'\n')
allcues=[]
for s in timeline['scenes']:
 for c in s['cues']:allcues.append(dict(c,start=c['start']+s['offset'],end=c['end']+s['offset']))
allcues.sort(key=lambda c:c['start']);srt='\n\n'.join(f"{i}\n{clock(c['start'])} --> {clock(c['end'])}\n"+('' if c['role']=='Narrator' else '['+c['role']+'] ')+c['text'] for i,c in enumerate(allcues,1))+'\n';(out/'LingoLive-Demo.srt').write_text(srt);(out/'LingoLive-Demo.vtt').write_text('WEBVTT\n\n'+__import__('re').sub(r'(\d{2}:\d{2}:\d{2}),(\d{3})',r'\1.\2',srt))
assert 180<=timeline['seconds']<=240
run(['-i',str(target),'-f','null','-'])
report=json.loads((root/'video-verification.json').read_text());report.update(file=target.name,bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),seconds=timeline['seconds'],demo_version='3.0',app_version='1.11 (extension); 1.9 (original scenes)',scene_count=10,learning_introduced_near_end_seconds=117+D,latest_duration_requirement_met=True,extension_verification=verification,asr_notes='Original café error/correction and return mixed-script error retained. Extension followup Kannada was rendered in Telugu script as Vangi railway station; actual app output visible with notice. Full/partial readbacks recognized without extra lesson requests.')
report.update(verify_audio(target,out/'edit-timeline.json',out/'audio-verification.json'));(out/'video-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
