import {VoiceTurns} from './speech-routing.mjs';
import {pcmWav,base64Bytes} from './signals.mjs';
const delay = ms => new Promise(resolve=>setTimeout(resolve,ms));
export class LiveMicrophone {
  constructor(events) { this.events=events; this.running=false; this.generation=0; this.sockets=new Set(); this.pending=[];this.ambience=[];this.voiceTurns=new VoiceTurns(); }
  async start() {
    if(this.running) return;
    if(!navigator.mediaDevices?.getUserMedia || !window.AudioWorkletNode) throw new Error('Use a current browser over HTTPS and allow microphone access. You can also type a phrase.');
    this.running=true; this.stopping=false;this.ambience=[];this.voiceTurns.reset(); const own=++this.generation; this.events.status('Requesting microphone…');
    try {
      const stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true},video:false});
      if(!this.running||own!==this.generation) {stream.getTracks().forEach(t=>t.stop());return;}
      this.stream=stream;
      const Context=window.AudioContext||window.webkitAudioContext;
      const context=new Context();this.context=context; await context.resume(); await context.audioWorklet.addModule('/assets/pcm-worklet.js');
      if(!this.running||own!==this.generation) {stream.getTracks().forEach(t=>t.stop());if(context.state!=='closed')await context.close();return;}
      this.node=new AudioWorkletNode(context,'lingolive-pcm'); this.source=context.createMediaStreamSource(stream);
      this.node.port.onmessage=e=>{ if(e.data.stopped) {this.flushDone?.();return;} if(e.data.pcm&&(this.running||this.stopping))this.frame(e.data.pcm); };
      this.source.connect(this.node); this.node.connect(this.context.destination);
      stream.getAudioTracks()[0].onended=()=>{if(this.running)this.fail('Microphone disconnected. Your completed phrases are saved.');};
      await this.connect(own);
    } catch(error) {
      if(own===this.generation) {await this.stop(false);throw new Error(error.name==='NotAllowedError'?'Microphone access was not allowed. Enable it in your browser or type a phrase.':error.name==='NotFoundError'?'No microphone was found. Connect one or type a phrase.':error.message||'Could not start listening.');}
    }
  }
  connect(own) {
    if(!this.running||own!==this.generation)return Promise.resolve();
    this.ready=false;const pair=this.pair,conversation=this.conversationSnapshot;this.events.status('Connecting to Google…');
    return new Promise((resolve,reject)=>{
      const socket=new WebSocket(location.origin.replace(/^http/,'ws')+'/v1/listen'); this.socket=socket;this.sockets.add(socket);let settled=false;
      const timer=setTimeout(()=>{if(!settled){settled=true;socket.close();reject(new Error('The listening service did not connect. Check your connection and demo allowance.'));}},15000);
      const error=message=>{if(!settled){settled=true;clearTimeout(timer);reject(new Error(message));}else if(this.running&&own===this.generation)this.fail(message);};
      socket.onopen=()=>{if(!this.running||own!==this.generation){socket.close();return;}socket.send(JSON.stringify({setup:{}}));};
      socket.onmessage=event=>{
        if(event.data.length>500000)return error('The listening response was too large. Please reconnect.');
        let value;try{value=JSON.parse(event.data);}catch{return error('Could not read the listening response. Please reconnect.');}
        if(value.error)return error(value.error.message||'Transcription is unavailable. Please reconnect later.');
        if(value.setupComplete||value.setup_complete){
          if(!this.running||own!==this.generation)return;
          this.ready=true;settled=true;clearTimeout(timer);this.events.status('Listening · all languages');
          for(const frame of this.pending.splice(0))this.send(frame);resolve();
          clearTimeout(this.renewTimer);this.renewTimer=setTimeout(()=>this.rotate(own),570000);
        }
        const content=value.serverContent||value.server_content;
        const final=content?.inputTranscription||content?.input_transcription;
        const interim=content?.interimInputTranscription||content?.interim_input_transcription;
        if(final?.text?.trim())this.events.final(final.text,pair,conversation,{voice:socket===this.socket?this.voiceTurns.finish():null});
        if(interim?.text&&this.running&&own===this.generation)this.events.interim(interim.text);
        if((value.goAway||value.go_away)&&this.running&&own===this.generation)this.rotate(own);
      };
      socket.onerror=()=>error('The listening connection failed. Check your connection and demo allowance.');
      socket.onclose=()=>{this.sockets.delete(socket);clearTimeout(timer);if(!settled){settled=true;reject(new Error('Could not connect. Open Connect and try again.'));}else if(this.running&&own===this.generation)this.fail('Listening disconnected. Your completed phrases are saved; tap to reconnect.');};
    });
  }
  async rotate(own) {
    if(!this.running||own!==this.generation)return;
    const previous=this.socket;this.ready=false;this.voiceTurns.reset();this.generation++;const next=this.generation;
    if(previous?.readyState===WebSocket.OPEN)previous.send(JSON.stringify({realtimeInput:{audioStreamEnd:true}}));
    setTimeout(()=>previous?.close(1000,'Session renewed'),3500);
    try {await this.connect(next);}catch(e){if(this.running&&next===this.generation)this.fail(e.message);}
  }
  audioContextSnippet(){
    if(!this.includeAmbience)return null;
    const wav=pcmWav(this.ambience);return wav?{mime_type:'audio/wav',data:base64Bytes(wav)}:null;
  }
  frame(buffer) {
    this.voiceTurns.push(buffer);
    if(this.includeAmbience){this.ambience.push(buffer.slice(0));let size=this.ambience.reduce((n,b)=>n+b.byteLength,0);while(size>128000&&this.ambience.length>1)size-=this.ambience.shift().byteLength;}
    if(this.ready&&this.socket?.readyState===WebSocket.OPEN)this.send(buffer);
    else if(this.running){this.pending.push(buffer);if(this.pending.reduce((n,b)=>n+b.byteLength,0)>160000)this.fail('The connection is too slow. Listening paused; the last few words may not have arrived.');}
  }
  send(buffer) {
    if(this.socket.bufferedAmount>128000){this.fail('The connection is too slow. Listening paused; tap to reconnect.');return;}
    let data='';for(const byte of new Uint8Array(buffer))data+=String.fromCharCode(byte);
    this.socket.send(JSON.stringify({realtimeInput:{audio:{data:btoa(data),mimeType:'audio/pcm;rate=16000'}}}));
  }
  async cleanupAudio() {
    this.stream?.getTracks().forEach(t=>t.stop());this.stream=null;
    try{this.source?.disconnect();this.node?.disconnect();}catch{}
    const context=this.context;this.context=null;this.node=null;this.source=null;
    if(context&&context.state!=='closed')await context.close();
  }
  async stop(flush=true) {
    if(!this.running&&!this.context)return;
    this.running=false;this.stopping=flush;this.generation++;clearTimeout(this.renewTimer);
    const closing=[...this.sockets];const current=this.socket;
    if(flush&&this.node)await Promise.race([new Promise(resolve=>{this.flushDone=resolve;this.node.port.postMessage('stop');}),delay(120)]);
    await this.cleanupAudio();this.stopping=false;this.ready=false;this.pending=[];setTimeout(()=>{if(!this.running)this.ambience=[];},flush?5000:0);
    if(flush&&current?.readyState===WebSocket.OPEN)current.send(JSON.stringify({realtimeInput:{audioStreamEnd:true}}));
    setTimeout(()=>closing.forEach(s=>s.close(1000,'Stopped')),flush?4500:0);
    this.events.status('Ready when you are');
  }
  async fail(message) {await this.stop(false);this.events.error(message);}
}
