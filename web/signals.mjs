export function approximateLocation(position,now=Date.now()){
  const c=position.coords;if(!Number.isFinite(c.latitude)||!Number.isFinite(c.longitude)||Math.abs(c.latitude)>90||Math.abs(c.longitude)>180)throw new Error('Location is unavailable.');
  const result={latitude:Math.round(c.latitude*100)/100,longitude:Math.round(c.longitude*100)/100,accuracy_m:Math.min(1000000,Math.max(1000,Math.round(c.accuracy||1000))),captured_at:Math.floor(now/1000)};
  if(Number.isFinite(c.speed)&&c.speed>=0)result.speed_kmh=Math.min(500,Math.round(c.speed*3.6));return result;
}
export function pcmWav(buffers){
  const length=buffers.reduce((n,b)=>n+b.byteLength,0);if(!length)return null;
  const bytes=new Uint8Array(44+Math.min(length,128000)),view=new DataView(bytes.buffer);
  const write=(offset,text)=>{for(let i=0;i<text.length;i++)bytes[offset+i]=text.charCodeAt(i);};
  write(0,'RIFF');view.setUint32(4,bytes.length-8,true);write(8,'WAVE');write(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,16000,true);view.setUint32(28,32000,true);view.setUint16(32,2,true);view.setUint16(34,16,true);write(36,'data');view.setUint32(40,bytes.length-44,true);
  let skip=Math.max(0,length-128000),at=44;
  for(const buffer of buffers){const data=new Uint8Array(buffer);if(skip>=data.length){skip-=data.length;continue;}const part=data.subarray(skip);bytes.set(part,at);at+=part.length;skip=0;}
  return bytes;
}
export function base64Bytes(bytes){let text='';for(const byte of bytes)text+=String.fromCharCode(byte);return btoa(text);}
