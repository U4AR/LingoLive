/* Bounded, editable browser memory. No coordinates, recordings, model training or sync. */
const DAY=86400000, KINDS=['activity','place','preference'];
const SETTINGS=['any','home','office','travelling','train','cafe','restaurant','shop','other'];
const clean=value=>typeof value==='string'?value.trim():'';
const key=value=>clean(value).normalize('NFKC').toLocaleLowerCase().replace(/[^\p{L}\p{N}]+/gu,' ').trim();
const tokens=value=>new Set(key(value).split(' ').filter(x=>x.length>2));
// Do not turn credentials, contact details or coordinates into personal memories.
const unsafe=text=>/(?:ya29\.|AIza[\w-]{20}|AQ\.[\w-]{15}|bearer\s|api.?key|password|access.?token|[\w.+-]+@[\w.-]+\.[a-z]{2}|\b\d{7,}\b|[-+]?\d{1,3}\.\d+\s*,\s*[-+]?\d{1,3}\.\d+)/i.test(text);
export class PersonalMemory {
  constructor(profile,persist=()=>{},now=()=>Date.now()){
    this.profile=profile;this.persist=persist;this.now=now;
    const old=profile.memory;
    if(!old||old.version!==1||!Array.isArray(old.items))profile.memory={version:1,enabled:true,epoch:0,items:[],blocked:[]};
    const data=this.data;data.epoch=Number.isSafeInteger(data.epoch)?data.epoch:0;data.enabled=data.enabled!==false;data.sequence=Number.isSafeInteger(data.sequence)?data.sequence:0;
    data.blocked=Array.isArray(data.blocked)?data.blocked.filter(x=>typeof x==='string').slice(-120):[];
    data.items=data.items.filter(m=>m&&typeof m.id==='string'&&KINDS.includes(m.kind)&&typeof m.text==='string'&&m.text.length<=160&&typeof m.topic==='string'&&m.topic.length<=40&&SETTINGS.includes(m.setting)&&['possible','confirmed'].includes(m.status)&&Number.isFinite(m.updated)&&Number.isFinite(m.expires)&&m.expires>now()&&!unsafe(m.text)).slice(-60);
  }
  get data(){return this.profile.memory;}
  get epoch(){return this.data.epoch;}
  get enabled(){return this.data.enabled;}
  items(){return this.data.items.filter(m=>m.expires>this.now()).sort((a,b)=>b.updated-a.updated||(b.order||0)-(a.order||0));}
  changed(){this.data.items=this.items().slice(0,60);this.persist();}
  enable(value){this.data.enabled=!!value;this.data.epoch++;this.changed();}
  clear(){this.data.items=[];this.data.blocked=[];this.data.enabled=false;this.data.epoch++;this.changed();}
  forget(id){const m=this.data.items.find(m=>m.id===id);if(!m)return;this.data.blocked.push(m.kind+':'+key(m.topic));this.data.blocked=this.data.blocked.slice(-120);this.data.items=this.data.items.filter(x=>x.id!==id);this.data.epoch++;this.changed();}
  confirm(id,text){const m=this.data.items.find(m=>m.id===id);if(!m)return;const value=clean(text??m.text);if(!value||value.length>160||unsafe(value))throw new Error('Use a short activity, broad place or preference without credentials or contact details.');m.text=value;m.status='confirmed';m.updated=this.now();m.expires=this.now()+(m.duration==='recent'?1:180)*DAY;this.data.items=this.data.items.filter(x=>x.id===id||x.kind!==m.kind||key(x.topic)!==key(m.topic));this.data.epoch++;this.changed();}
  add({kind,text,setting='any'}){
    text=clean(text);if(!KINDS.includes(kind)||!SETTINGS.includes(setting)||!text||text.length>160||unsafe(text))throw new Error('Use a short activity, broad place or preference without credentials or contact details.');
    const now=this.now(),m={id:crypto.randomUUID(),order:++this.data.sequence,kind,text,topic:key(text).slice(0,40),setting,status:'confirmed',observations:1,scenes:[],evidence:'Added by you',created:now,updated:now,expires:now+180*DAY};
    this.data.items.push(m);this.data.epoch++;this.changed();return m;
  }
  observe(candidates,{text,speaker,confidence,scene,record,epoch,confirmed=false}){
    if(!this.enabled||epoch!==this.epoch||speaker!=='user'||(!confirmed&&!['medium','high'].includes(confidence))||!Array.isArray(candidates))return;
    const now=this.now();
    for(const c of candidates.slice(0,2)){
      if(!c||!KINDS.includes(c.kind)||c.kind==='place'||!SETTINGS.includes(c.setting)||!['recent','routine'].includes(c.duration))continue;
      if(!clean(c.text)||c.text.length>160||!clean(c.topic)||c.topic.length>40||!clean(c.evidence)||c.evidence.length>200||!text.includes(c.evidence)||unsafe(c.text+' '+c.evidence))continue;
      const topic=c.kind+':'+key(c.topic);if(this.data.blocked.includes(topic))continue;
      let m=this.data.items.find(m=>m.kind===c.kind&&key(m.topic)===key(c.topic)&&m.status==='possible');
      const fixed=this.data.items.find(m=>m.kind===c.kind&&key(m.topic)===key(c.topic)&&m.status==='confirmed');
      if(fixed&&key(fixed.text)===key(c.text))continue;
      if(!m){m={id:crypto.randomUUID(),kind:c.kind,topic:c.topic,text:c.text,setting:c.setting,status:'possible',observations:0,scenes:[],created:now,updated:now,expires:now};this.data.items.push(m);}
      // One utterance/retry is one observation. Repetition never becomes confirmation.
      if((m.records||[]).includes(record)){if(confirmed){m.status='confirmed';m.updated=now;m.expires=now+(c.duration==='recent'?1:180)*DAY;this.data.items=this.data.items.filter(x=>x.id===m.id||x.kind!==m.kind||key(x.topic)!==key(m.topic));}continue;}
      m.duration=c.duration;m.records=[...(m.records||[]),record].slice(-20);m.order=++this.data.sequence;m.observations=Math.min(99,m.observations+1);m.scenes=[...new Set([...(m.scenes||[]),scene])].slice(-10);m.last_record=record;m.evidence=c.evidence;m.text=c.text;m.setting=c.setting;m.updated=now;m.expires=now+(c.duration==='recent'?1:30)*DAY;
      if(confirmed){m.status='confirmed';m.expires=now+(c.duration==='recent'?1:180)*DAY;this.data.items=this.data.items.filter(x=>x.id===m.id||x.kind!==m.kind||key(x.topic)!==key(m.topic));}
    }
    this.changed();
  }
  relevant(text,setting='auto'){
    const words=tokens(text),now=this.now();
    return this.items().filter(m=>m.kind!=='place').map(m=>{
      const overlap=[...tokens(m.text+' '+m.topic)].filter(t=>words.has(t)).length;
      const match=setting!=='auto'&&m.setting===setting;
      const general=m.kind==='preference'&&m.setting==='any';
      return {m,score:overlap*4+(match?5:0)+(general?2:0)+(m.status==='confirmed'?1:0)+Math.min(2,(m.scenes||[]).length)/4+1/(1+(now-m.updated)/DAY)};
    }).filter(x=>setting==='auto'||x.m.setting==='any'||x.m.setting===setting||[...tokens(x.m.text)].some(t=>words.has(t)))
      .sort((a,b)=>b.score-a.score).slice(0,5).map(({m})=>({kind:m.kind,text:m.text,status:m.status,setting:m.setting,observations:m.observations||1}));
  }
}
