"""Make disclosed synthetic low-level ambience and microphone mixes, not field audio."""
import argparse,math,random,struct,subprocess,wave
from pathlib import Path

def ambient(target,kind,seconds=30):
 rate=24000;rng=random.Random({'street':11,'cafe':29,'home':47}[kind]);brown=0.;low=0.;data=bytearray();clinks=[(4.1,2700),(11.3,3400),(19.2,2400),(25.1,3900)]
 for i in range(round(seconds*rate)):
  t=i/rate;white=rng.uniform(-1,1);brown=.995*brown+.005*white;low=.80*low+.20*white
  if kind=='street':
   passing=.35+.65*math.exp(-((t-12)/6)**2);value=.09*brown+.009*low+passing*(.007*math.sin(2*math.pi*78*t)+.002*math.sin(2*math.pi*157*t))
  elif kind=='cafe':
   value=.035*brown+.007*low
   for start,hz in clinks:
    d=t-start
    if 0<=d<.35:value+=.035*math.exp(-22*d)*(math.sin(2*math.pi*hz*d)+.4*math.sin(2*math.pi*hz*1.47*d))
  else:value=.012*brown+.001*low
  data.extend(struct.pack('<h',max(-32768,min(32767,round(value*32767)))))
 with wave.open(str(target),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(data)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=Path('/tmp/lingolive-video-v2'));a=p.parse_args();audio=a.output/'audio';audio.mkdir(parents=True,exist_ok=True)
 for kind in ['street','cafe','home']:ambient(audio/('ambience-'+kind+'.wav'),kind)
 for name,kind in [('driver-question','street'),('learner-english','street'),('cafe-question','cafe'),('shop-question','cafe')]:
  subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(audio/(name+'.wav')),'-i',str(audio/('ambience-'+kind+'.wav')),'-filter_complex','[0:a]loudnorm=I=-18:LRA=7:TP=-2[s];[s][1:a]amix=inputs=2:duration=first:normalize=0[a]','-map','[a]','-ar','48000','-ac','1',str(audio/(name+'-mic.wav'))],check=True)
 print('Synthetic ambience and actual microphone input mixes prepared.')
if __name__=='__main__':main()
