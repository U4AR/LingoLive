"""Check every expected voice in the decoded MP4, not just its global volume."""
import argparse,array,json,math,re,subprocess
from pathlib import Path
RATE=8000

def pcm(file,start=None,seconds=None):
 args=['ffmpeg','-v','error']
 if start is not None:args+=['-ss',str(start)]
 args+=['-i',str(file)]
 if seconds is not None:args+=['-t',str(seconds)]
 raw=subprocess.check_output(args+['-vn','-ac','1','-ar',str(RATE),'-f','s16le','-'])
 return array.array('h',raw)

def db(value):return round(20*math.log10(max(value,1e-9)/32768),3)
def rms(x):return math.sqrt(sum(v*v for v in x)/max(1,len(x)))

def match(source,rendered):
 # AAC priming/concat may shift the decoded waveform by a few milliseconds.
 # Compare actual waveform, so ambience or unrelated speech cannot pass the check.
 stride=4;indices=range(0,len(source),stride)
 def score(lag):
  pairs=[(source[i],rendered[i+lag]) for i in indices if 0<=i+lag<len(rendered)]
  xy=sum(a*b for a,b in pairs);den=math.sqrt(sum(a*a for a,b in pairs)*sum(b*b for a,b in pairs))
  return xy/den if den else 0
 coarse=range(0,min(800,max(1,len(rendered)-len(source)+1)),8)
 lag=max(coarse,key=score);lag=max(range(max(0,lag-8),min(800,lag+9)),key=score)
 return round(score(lag),4),round(lag/RATE,4)

def verify_audio(video,timeline,output,strict=True):
 t=json.loads(Path(timeline).read_text());events=[]
 for scene in t['scenes']:
  for event in scene['audio']:
   source=pcm(event['file']);at=scene['offset']+event['start'];rendered=pcm(video,at,len(source)/RATE+.12)
   correlation,lag=match(source,rendered)
   active_threshold=max(map(abs,source))*.025;shift=round(lag*RATE)
   active=[rendered[i+shift] for i,v in enumerate(source) if abs(v)>active_threshold and i+shift<len(rendered)]
   level=db(rms(active));passed=correlation>=.82 and level>-30
   events.append(dict(scene=scene['id'],voice=event['id'],start=round(at,3),end=round(scene['offset']+event['end'],3),waveform_correlation=correlation,alignment_lag_seconds=lag,active_speech_rms_dbfs=level,passed=passed))
 stats=subprocess.run(['ffmpeg','-hide_banner','-i',str(video),'-af','loudnorm=I=-18:TP=-2:LRA=7:print_format=json','-f','null','-'],capture_output=True,text=True,check=True).stderr
 loud=json.JSONDecoder().raw_decode(stats[stats.rfind('{'):])[0];detect=subprocess.run(['ffmpeg','-hide_banner','-i',str(video),'-af','silencedetect=noise=-35dB:d=0.8','-f','null','-'],capture_output=True,text=True,check=True).stderr
 gaps=[dict(start=float(a),end=float(b),seconds=float(c)) for a,b,c in re.findall(r'silence_start: ([\d.]+).*?silence_end: ([\d.]+) \| silence_duration: ([\d.]+)',detect,re.S)]
 peak=float(loud['input_tp']);longest=max((g['seconds'] for g in gaps),default=0)
 report=dict(all_expected_voices_audible=all(e['passed'] for e in events),expected_voice_events=len(events),events=events,silence_threshold_dbfs=-35,silences_over_0_8_seconds=gaps,longest_silence_seconds=longest,integrated_loudness_lufs=float(loud['input_i']),true_peak_dbtp=peak,audio_clipping_detected=peak>=0,verification_method='Decoded final MP4 compared with each source waveform (correlation >=0.82 and active speech RMS >-30 dBFS). AAC alignment tolerance 100 ms; no new model calls.')
 Path(output).write_text(json.dumps(report,indent=2)+'\n')
 if strict:
  assert report['all_expected_voices_audible'],[e['voice'] for e in events if not e['passed']]
  assert longest<5.5,('Unexplained long pause',longest)
  assert peak<0,('Clipping',peak)
 print(json.dumps({k:v for k,v in report.items() if k not in ('events','silences_over_0_8_seconds')}),flush=True)
 return {k:v for k,v in report.items() if k not in ('events','silences_over_0_8_seconds')}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('video',type=Path);p.add_argument('timeline',type=Path);p.add_argument('output',type=Path);p.add_argument('--report-only',action='store_true');a=p.parse_args();verify_audio(a.video,a.timeline,a.output,not a.report_only)
