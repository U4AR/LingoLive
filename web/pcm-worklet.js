import {PcmResampler} from './core.mjs';
class PcmCapture extends AudioWorkletProcessor {
  constructor() { super(); this.active=true; this.resampler=new PcmResampler(sampleRate); this.port.onmessage=e=>{if(e.data==='stop'){this.active=false;this.resampler.flush(frame=>this.send(frame));this.port.postMessage({stopped:true});}}; }
  send(frame) {
    // Encode explicitly as little endian, including on unusual browser architectures.
    const buffer=new ArrayBuffer(frame.length*2); const view=new DataView(buffer);
    frame.forEach((value,i)=>view.setInt16(i*2,value,true)); this.port.postMessage({pcm:buffer},[buffer]);
  }
  process(inputs) { if(this.active&&inputs[0]?.[0]) this.resampler.push(inputs[0][0],frame=>this.send(frame)); return true; }
}
registerProcessor('lingolive-pcm',PcmCapture);
