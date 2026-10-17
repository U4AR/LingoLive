/* Optional local place memory. The AI never supplies coordinates or bypasses these guards. */
const DAY=86400000, DWELL=60000, FRESH=90000, GAP=30*60000, RADIUS=250, ROUNDING=80;
const safe=text=>typeof text==='string'&&text.trim()&&!/(?:ya29\.|AIza[\w-]{20}|AQ\.[\w-]{15}|bearer\s|api.?key|password|access.?token|[\w.+-]+@[\w.-]+\.[a-z]{2}|\b\d{7,}\b|[-+]?\d{1,3}\.\d+\s*,\s*[-+]?\d{1,3}\.\d+)/i.test(text);
export const distance=(a,b)=>{
 const rad=x=>x*Math.PI/180,dlat=rad(b.latitude-a.latitude),dlon=rad(b.longitude-a.longitude);
 return 6371000*2*Math.asin(Math.min(1,Math.sqrt(Math.sin(dlat/2)**2+Math.cos(rad(a.latitude))*Math.cos(rad(b.latitude))*Math.sin(dlon/2)**2)));
};
export function placeFix(position,now=Date.now()){
 const c=position?.coords,t=Number(position?.timestamp);
 if(!c||!Number.isFinite(c.latitude)||!Number.isFinite(c.longitude)||Math.abs(c.latitude)>85||Math.abs(c.longitude)>180||!Number.isFinite(c.accuracy)||c.accuracy<0||c.accuracy>75||!Number.isFinite(t)||now-t>FRESH||t-now>5000||c.speed!==null&&c.speed!==undefined&&(!Number.isFinite(c.speed)||c.speed>2.5||c.speed<0))return null;
 return {latitude:c.latitude,longitude:c.longitude,accuracy:c.accuracy,at:t}; // RAM only; never transmitted.
}
export class Places {
 constructor(profile,persist=()=>{},now=()=>Date.now()){
  this.profile=profile;this.persist=persist;this.now=now;this.fix=null;this.stay=null;this.autoStay=null;
  const d=profile.places;if(!d||d.version!==1||!Array.isArray(d.items))profile.places={version:1,enabled:false,epoch:0,items:[],auto_times:[]};
  this.data=profile.places;this.data.enabled=false;this.data.epoch=Number.isSafeInteger(this.data.epoch)?this.data.epoch:0;
  this.data.items=this.data.items.filter(p=>p&&safe(p.label)&&p.label.length<=60&&typeof p.id==='string'&&Number.isFinite(p.latitude)&&Math.abs(p.latitude)<=85&&Number.isFinite(p.longitude)&&Math.abs(p.longitude)<=180&&Number.isFinite(p.updated)&&p.updated+90*DAY>now()&&Array.isArray(p.facts)).slice(0,5);
  for(const p of this.data.items){p.latitude=Math.round(p.latitude*1000)/1000;p.longitude=Math.round(p.longitude*1000)/1000;p.facts=p.facts.filter(f=>f&&safe(f.text)&&f.text.length<=160&&['possible','confirmed'].includes(f.status)).slice(0,3);}
  this.data.auto_times=Array.isArray(this.data.auto_times)?this.data.auto_times.filter(t=>Number.isFinite(t)&&now()-t<DAY).slice(-2):[];
 }
 get epoch(){return this.data.epoch;}
 get enabled(){return this.data.enabled===true;}
 items(){return this.data.items.filter(p=>p.updated+90*DAY>this.now());}
 enable(value){this.data.enabled=!!value;this.data.epoch++;this.reset();this.persist();}
 reset(){this.fix=null;this.stay=null;}
 update(position){
  const now=this.now(),fix=placeFix(position,now);if(!this.enabled||!fix){this.reset();return;}
  if(!this.fix||fix.at-this.fix.at>FRESH||!this.stay||distance(fix,this.stay.origin)>60+fix.accuracy)this.stay={origin:fix,since:fix.at,samples:0,last:0};
  if(fix.at>this.stay.last){this.stay.samples++;this.stay.last=fix.at;}this.fix=fix;
  let changed=false;
  for(const p of this.items()){
   const d=distance(p,fix);
   if(d-fix.accuracy-ROUNDING>RADIUS){if(!p.away){p.away=true;p.returning=false;changed=true;}}
   else if(d+fix.accuracy+ROUNDING<=RADIUS){
    if(p.last_seen&&now-p.last_seen>=GAP)p.away=true;
    if(this.ready()&&p.away){p.away=false;p.returning=true;changed=true;}
    if(!p.last_seen||now-p.last_seen>=60000){p.last_seen=now;changed=true;}
   }
  }
  if(changed)this.persist();
 }
 ready(){return this.enabled&&this.fix&&this.now()-this.fix.at<=FRESH&&this.stay?.samples>=2&&this.now()-this.stay.since>=DWELL;}
 nearby(){if(!this.ready())return null;return this.items().map(p=>({p,d:distance(p,this.fix)})).filter(x=>x.d+this.fix.accuracy+ROUNDING<=RADIUS).sort((a,b)=>a.d-b.d)[0]?.p||null;}
 context(){const p=this.nearby();return p?.returning?p.facts.slice(0,2).map(f=>({label:p.label,fact:f.text,status:f.status})):[];}
 ticket(){return this.ready()?{epoch:this.epoch,origin:{...this.fix},stay:this.stay.since}:null;}
 eligible(ticket){return this.ready()&&ticket?.epoch===this.epoch&&ticket.stay===this.stay.since&&distance(ticket.origin,this.fix)<100;}
 canPropose(){const p=this.nearby(),times=this.data.auto_times.filter(t=>this.now()-t<DAY);return !!this.ready()&&this.autoStay!==this.stay.since&&(p?p.facts.length<3:this.items().length<5)&&times.length<2&&(!times.length||this.now()-times.at(-1)>=GAP);}
 add(label,text,{automatic=false,ticket=null}={}){
  label=typeof label==='string'?label.trim():'';text=typeof text==='string'?text.trim():'';
  if(!safe(label)||label.length>60||!safe(text)||text.length>160)throw new Error('Use a short place name and note without contact details or credentials.');
  if(!this.ready()||automatic&&(!this.eligible(ticket)||!this.canPropose()))throw new Error('Stay here with a fresh accurate location for a minute before saving.');
  let p=this.nearby();const now=this.now();
  if(!p){if(this.items().length>=5)throw new Error('Five places are saved. Forget one before adding another.');p={id:crypto.randomUUID(),label,latitude:Math.round(this.fix.latitude*1000)/1000,longitude:Math.round(this.fix.longitude*1000)/1000,created:now,updated:now,last_seen:now,away:false,returning:false,facts:[]};this.data.items.push(p);}
  if(p.facts.some(f=>f.text.toLocaleLowerCase()===text.toLocaleLowerCase()))return p;
  if(p.facts.length>=3)throw new Error('This place has three notes. Edit or forget a note first.');
  p.facts.push({id:crypto.randomUUID(),text,status:automatic?'possible':'confirmed'});p.updated=now;
  if(automatic){this.autoStay=this.stay.since;this.data.auto_times=[...this.data.auto_times.filter(t=>now-t<DAY),now].slice(-2);}
  this.data.items=this.items().slice(0,5);this.persist();return p;
 }
 observe(candidates,{text,speaker,confidence,confirmed=false,ticket}){
  if(!this.eligible(ticket)||speaker!=='user'||!confirmed&&confidence!=='high'||!Array.isArray(candidates))return;
  const c=candidates[0];if(!c||!safe(c.evidence)||c.evidence.length>200||!text.includes(c.evidence))return;
  try{this.add(c.label,c.fact,{automatic:true,ticket});}catch{} // Rejected proposals never affect the lesson.
 }
 edit(id,label,factId,text){const p=this.items().find(p=>p.id===id),f=p?.facts.find(f=>f.id===factId);if(!f||!safe(label)||label.length>60||!safe(text)||text.length>160)throw new Error('Use a short place name and note.');p.label=label.trim();f.text=text.trim();f.status='confirmed';p.updated=this.now();this.data.epoch++;this.persist();}
 forget(id){this.data.items=this.data.items.filter(p=>p.id!==id);this.data.epoch++;this.persist();}
 forgetFact(id,factId){const p=this.items().find(p=>p.id===id);if(p){p.facts=p.facts.filter(f=>f.id!==factId);if(!p.facts.length)this.data.items=this.data.items.filter(x=>x.id!==id);this.data.epoch++;this.persist();}}
 clear(){this.data.items=[];this.data.enabled=false;this.data.epoch++;this.reset();this.persist();}
}
