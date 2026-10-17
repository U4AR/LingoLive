"""Compose the approved utility-first v2 video; no network, no time stretching.

Actual browser clips retain their speed and complete model waits. End frames may
hold for reading. One real ASR error and the visible typed correction are kept.
Synthetic voices/ambience/illustration and simulated place/time are disclosed.
"""
import argparse,hashlib,json,math,os,re,subprocess,textwrap,wave
from check_submission_audio_v2 import verify_audio
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
W,H,FPS=1920,1080,25
RAW_OFFSET=-.90 # Cross-checked against four recorded microphone-button changes.
DURATIONS={'problem':26,'solution':11,'plan':9,'cab':17,'express':15,'cafe':16,'place':23,'learn':14,'close':11}

def speech_gain(file):
 # Analyze independently, then apply a constant gain. loudnorm can emit NOPTS
 # while flushing short WAVs; applying adelay to that stream lost dialogue.
 result=subprocess.run(['ffmpeg','-hide_banner','-i',str(file),'-af',
  'loudnorm=I=-18:TP=-2:LRA=7:print_format=json','-f','null','-'],
  capture_output=True,text=True,check=True)
 stats=json.JSONDecoder().raw_decode(result.stderr[result.stderr.rfind('{'):])[0];level=float(stats['input_i']);peak=float(stats['input_tp'])
 assert math.isfinite(level) and math.isfinite(peak),str(file)
 return round(min(-18-level,-2.5-peak),3)

def duration(p):
 with wave.open(str(p)) as f:return f.getnframes()/f.getframerate()
def clock(t,ass=False):
 n=round(t*(100 if ass else 1000));units=100 if ass else 1000;h,n=divmod(n,3600*units);m,n=divmod(n,60*units);s,n=divmod(n,units)
 return f'{h}:{m:02}:{s:02}.{n:02}' if ass else f'{h:02}:{m:02}:{s:02},{n:03}'
def metadata(p):return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(p)],text=True))
def clean(s):return s.replace('\\','/').replace('{','(').replace('}',')')
def run(args):subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',*args],check=True,env=dict(os.environ,XDG_CACHE_HOME='/tmp/lingolive-video-v2/cache'))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=Path('/tmp/lingolive-video-v2'));p.add_argument('--only',choices=list(DURATIONS));a=p.parse_args();out=a.output.resolve();audio=out/'audio';renders=out/'renders';renders.mkdir(exist_ok=True)
 r=json.loads((out/'recording.json').read_text());assert r['success'] and r['no_place_context_away'] and r['saved_review_without_ai']
 rows={x['id']:x for x in r['scenes']};specs={x['id']:x for x in json.loads((out/'scene-plan.json').read_text())};selected=r['selected']
 assert sum(DURATIONS.values())<180 and json.loads((ROOT/'docs/submission/submission.json').read_text())['demo_v2']['approval_status']=='approved'
 offsets={};off=0
 for name,D in DURATIONS.items():offsets[name]=off;off+=D
 all_cues=[];timeline=[];clips=[]
 for name,D in DURATIONS.items():
  narration=specs[name]['narration'];events=[]
  def voice(id,start,text,role='Narrator',mic=False):
   # The recorded microphone mixes remain evidence; use the same dry voice
   # in the film so the artificial traffic tone is not in the soundtrack.
   file=audio/(id.removesuffix('-mic')+'.wav');end=start+duration(file);assert start>=0 and end<=D-.1,(name,id,start,end,D)
   events.append(dict(id=id,file=str(file),start=round(start,3),end=round(end,3),text=text,role=role,microphone_mix=mic,gain_db=speech_gain(file)));return end
  if name=='problem':
   t=voice('narration-problem',.4,narration)+.55
   t=voice('driver-question',t,'Where do you need to go?','Driver · Kannada')+.7
   t=voice('learner-problem',t,'The railway station… could we stop for tea first?','Newcomer · English')+.7
   t=voice('driver-confused',t,"I didn't understand. Where do you need to go?",'Driver · Kannada')+.8
   voice('learner-unsure',t,"I know what I mean. I just don't know how to say it.",'Newcomer · English')
  elif name in ('cab','express','cafe'):
   row=rows[name];inp=row['input_start']-row['start'];source={'cab':('driver-question-mic','Where do you need to go?','Driver · Kannada'),'express':('learner-english-mic','Could we stop for tea first?','Newcomer · English'),'cafe':('cafe-question-mic','Having it here, or taking it away?','Shopkeeper · Kannada')}[name]
   source_end=voice(source[0],inp,source[1],source[2],True);ne=voice('narration-'+name,source_end+.45,narration)
   ready=(row.get('correction_end',row['response_ready'])-row['start']);at=max(ne+.55,ready+.8);le=voice('learner-'+name,at,selected[name]['translation'],'Newcomer · Kannada')
   if name in ('cab','express'):voice('driver-okay',le+.6,'Okay.','Driver · Kannada')
  elif name=='place':
   ne=voice('narration-place',.35,narration);return_start=12.4;row=rows['place-return'];at=return_start+row['input_start']-row['start'];se=voice('shop-question-mic',at,'What would you like?','Shopkeeper · Kannada',True);assert at>ne+.15
   ready=return_start+(row.get('correction_end',row['response_ready'])-row['start']);voice('learner-place',max(se+.8,ready+.8),selected['place']['translation'],'Newcomer · Kannada')
  else:voice('narration-'+name,.4,narration)
  # English captions timed to each actual audio file, with no speed modification.
  cues=[]
  for event in events:
   if event['role']=='Narrator':
    words=event['text'].split();n=len(words)
    group=math.ceil(n/math.ceil(n/12))
    for i in range(0,n,group):
     j=min(n,i+group);cues.append(dict(start=event['start']+(event['end']-event['start'])*i/n,end=event['start']+(event['end']-event['start'])*j/n,text=' '.join(words[i:j]),role='Narrator'))
   else:cues.append(dict(start=event['start'],end=event['end'],text=event['text'],role=event['role']))
  cues.sort(key=lambda v:v['start']);timeline.append(dict(id=name,duration=D,offset=offsets[name],audio=events,cues=cues))
  for c in cues:all_cues.append(dict(start=c['start']+offsets[name],end=c['end']+offsets[name],text=c['text'],role=c['role']))
  if a.only and name!=a.only:continue
  # ASS draws presentation captions only; the phone is the actual recorded app.
  color='&H00FFFFFF' if name=='problem' else '&H003D4B23'
  header=f'''[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\nWrapStyle: 2\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Caption,DejaVu Sans,39,{color},{color},&H000F2019,&H000F2019,0,0,0,0,100,100,0,0,1,{1 if name=='problem' else 0},0,1,120,780,72,1\nStyle: Dialogue,DejaVu Sans,47,{color},{color},&H000F2019,&H000F2019,0,0,0,0,100,100,0,0,1,{1 if name=='problem' else 0},0,7,120,785,550,1\nStyle: Notice,DejaVu Sans,28,&H003D4B23,&H003D4B23,&H00F0F6F5,&H00F0F6F5,0,0,0,0,100,100,0,0,3,12,0,7,120,785,795,1\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n'''
  lines=[]
  for c in cues:
   if c['role']!='Narrator':continue # Actor callouts already provide burned English captions.
   label=''
   text=r'\N'.join(textwrap.wrap(clean(label+c['text']),width=49));lines.append(f"Dialogue: 2,{clock(c['start'],True)},{clock(c['end'],True)},Caption,,0,0,0,,{text}")
  actors=[e for e in events if e['role']!='Narrator']
  for i,e in enumerate(actors):
   end=min(D,e['end']+1.1,actors[i+1]['start']-.12 if i+1<len(actors) else D)
   text=r'{\fs25\b1}'+clean(e['role'].upper())+r'{\fs47\b0}\N'+r'\N'.join(textwrap.wrap(clean(e['text']),width=38));lines.append(f"Dialogue: 1,{clock(e['start'],True)},{clock(end,True)},Dialogue,,0,0,0,,{text}")
  if name=='cafe' and 'correction_start' in rows[name]:
   row=rows[name];b=row['response_ready']-row['start'];e=min(D,row['correction_end']-row['start']+2);lines.append(f"Dialogue: 3,{clock(b,True)},{clock(e,True)},Notice,,0,0,0,,Speech misheard — correction typed")
  if name=='place':lines.append('Dialogue: 3,0:00:10.50,0:00:15.00,Notice,,0,0,0,,A later visit — simulated location and time')
  ass=renders/(name+'.ass');ass.write_text(header+'\n'.join(lines)+'\n')
  args=['-loop','1','-framerate',str(FPS),'-i',str(out/'frames'/(name+'.png'))];filters=[];vi=1
  if name=='problem':
   args+=['-loop','1','-framerate',str(FPS),'-i',str(out/'establishing.png')];filters.append(f"[1:v]scale=1958:1102,zoompan=z='1.0+0.000012*on':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1920x1080:fps=25[photo];[photo][0:v]overlay=0:0[base]");vi=2
  elif name in ('solution','close'):
   still=out/'shots'/('cab.png' if name=='solution' else 'place-return.png');args+=['-loop','1','-framerate',str(FPS),'-i',str(still)];filters.append('[1:v]scale=500:978[phone];[0:v][phone]overlay=1300:50[base]');vi=2
  elif name=='place':
   setup=rows['place-setup'];back=rows['place-return'];args+=['-ss',str(max(0,setup['start']+RAW_OFFSET)),'-i',str(out/'raw/app.webm'),'-ss',str(max(0,back['start']+RAW_OFFSET)),'-i',str(out/'raw/app.webm')]
   filters += [f"[1:v]trim=duration={setup['seconds']},setpts=PTS-STARTPTS,fps=25,tpad=stop_mode=clone:stop_duration=13,trim=duration=12.4[setup]",f"[2:v]trim=duration={back['seconds']},setpts=PTS-STARTPTS,fps=25,tpad=stop_mode=clone:stop_duration=15,trim=duration={D-12.4}[back]",'[setup][back]concat=n=2:v=1:a=0,scale=500:978[phone];[0:v][phone]overlay=1300:50[base]'];vi=3
  else:
   row=rows[name];length=row['seconds']-(.65 if name=='plan' else 0);args+=['-ss',str(max(0,row['start']+RAW_OFFSET)),'-i',str(out/'raw/app.webm')];filters.append(f"[1:v]trim=duration={length},setpts=PTS-STARTPTS,fps=25,tpad=stop_mode=clone:stop_duration={D},trim=duration={D},scale=500:978[phone];[0:v][phone]overlay=1300:50[base]");vi=2
  filters.append(f"[base]ass='{ass}'[v]")
  # No generated ambience bed. Keep dialogue clear and preserve source cadence.
  labels=[]
  for i,event in enumerate(events):
   args+=['-i',event['file']]
   filters.append(f"[{vi}:a]aresample=48000,asetpts=N/SR/TB,volume={event['gain_db']}dB,adelay={round(event['start']*1000)}:all=1,asetpts=N/SR/TB,apad,atrim=duration={D}[a{i}]")
   labels.append(f'[a{i}]');vi+=1
  filters.append(''.join(labels)+f'amix=inputs={len(labels)}:normalize=0:duration=longest,alimiter=limit=0.95:level=false:latency=true[a]')
  clip=renders/(name+'.mp4');run([*args,'-filter_complex',';'.join(filters),'-map','[v]','-map','[a]','-t',str(D),'-r','25','-c:v','libx264','-preset','veryfast','-crf','23','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-ar','48000','-ac','2','-threads','2',str(clip)]);clips.append(clip);print('Rendered '+name,flush=True)
 (out/'edit-timeline.json').write_text(json.dumps({'raw_time_offset_seconds':RAW_OFFSET,'alignment_method':'Four microphone-button colour transitions; raw starts about 0.90 s after recorder wall origin; original frame timing retained.','scenes':timeline,'seconds':sum(DURATIONS.values())},ensure_ascii=False,indent=2)+'\n')
 if a.only:return
 all_cues.sort(key=lambda c:c['start']);srt='\n\n'.join(f"{i}\n{clock(c['start'])} --> {clock(c['end'])}\n"+('' if c['role']=='Narrator' else '['+c['role']+'] ')+c['text'] for i,c in enumerate(all_cues,1))+'\n';(out/'LingoLive-Demo.srt').write_text(srt);(out/'LingoLive-Demo.vtt').write_text('WEBVTT\n\n'+re.sub(r'(\d{2}:\d{2}:\d{2}),(\d{3})',r'\1.\2',srt))
 concat=renders/'concat.txt';concat.write_text(''.join("file '"+str(p)+"'\n" for p in clips));target=out/'LingoLive-Demo.mp4';run(['-f','concat','-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',str(target)])
 info=metadata(target);seconds=float(info['format']['duration']);assert 0<seconds<180;assert any(s['codec_name']=='h264' and s['width']==W and s['height']==H for s in info['streams']);assert any(s['codec_name']=='aac' for s in info['streams']);run(['-i',str(target),'-f','null','-'])
 report={'file':target.name,'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'seconds':seconds,'video':'H.264 1920x1080 / 25fps','audio':'AAC stereo; Google Gemini 3.1 Flash TTS preview, Kannada and Indian English','voice_model':'gemini-3.1-flash-tts-preview','voices':{'narrator':'Kore','newcomer':'Orus','driver':'Charon','shopkeeper':'Algieba'},'synthetic_speech_disclosed':True,'synthetic_ambience_disclosed':True,'soundtrack_ambience':'Removed artificial ambience; dry source voices. Original noisy microphone inputs retained as recording evidence.','generated_establishing_image_disclosed':True,'physical_microphone':False,'geolocation_and_elapsed_time_simulated':True,'human_native_voice_review':False,'independent_audio_transcription_checks':'source-voice-check.json and reply-voice-check.json','burned_english_captions':True,'sidecar_captions':['LingoLive-Demo.srt','LingoLive-Demo.vtt'],'decode_verified':True,'scene_count':9,'live_google_lesson_requests_in_final_take':r['lesson_requests'],'raw_generation_calls_in_final_take':r['google_generation_calls'],'previous_incomplete_take_lesson_requests':3,'google_mocked':False,'visual_speed':'Original speed and complete inference waits, with end-frame holds for reading. No audio time stretching.','asr_error_and_typed_correction_visible':True,'asr_notes':'Tea-stall Kannada was misidentified as Bengali; explicit typed correction shown. Return question had mixed Telugu/Kannada script but retained useful meaning/context.','learning_introduced_near_end_seconds':sum(DURATIONS[x] for x in ['problem','solution','plan','cab','express','cafe','place']),'public_submission_status':'Prepared media only; no Hack2skill receipt or accepted video-host link claimed'}
 report.update(verify_audio(target,out/'edit-timeline.json',out/'audio-verification.json'))
 (out/'video-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
