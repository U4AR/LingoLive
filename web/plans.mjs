/* A short-lived explicit intention, separate from remembered facts and current GPS. */
const DAY=86400000;
const bounded=(value,max)=>typeof value==='string'?value.trim().slice(0,max):'';
export class Plans {
 constructor(profile,persist=()=>{},now=()=>Date.now()){this.profile=profile;this.persist=persist;this.now=now;}
 get plan(){const p=this.profile.task_plan;return p?.version===1&&typeof p.intent==='string'&&p.intent.length<=600&&Array.isArray(p.steps)&&p.steps.length<=6&&p.steps.every(s=>s&&typeof s.label==='string'&&s.label.length<=100&&typeof s.optional==='boolean'&&['pending','done','skipped'].includes(s.state))&&Number.isInteger(p.current)&&p.current>=0&&p.current<=p.steps.length?p:null;}
 save(intent,lines=''){
  intent=bounded(intent,600);if(!intent)throw new Error('Describe what you want to do.');
  const raw=lines.split('\n').map(s=>s.trim()).filter(Boolean);if(raw.length>6||raw.some(s=>s.length>100))throw new Error('Use at most six short steps, one per line.');
  const steps=raw.map(label=>({label:label.replace(/\s*(?:\(optional\)|\?)\s*$/i,'').trim(),optional:/(?:\(optional\)|\?)\s*$/i.test(label),state:'pending'}));if(steps.some(s=>!s.label))throw new Error('Give each step a name.');
  const p={version:1,id:crypto.randomUUID(),revision:0,intent,steps,current:0,paused:false,expires:this.now()+DAY};this.profile.task_plan=p;this.persist();return p;
 }
 context(){const p=this.plan;if(!p||p.paused||!Number.isFinite(p.expires)||p.expires<=this.now()||p.steps.length&&p.current===p.steps.length)return null;return {intent:p.intent,steps:p.steps.map(s=>({...s})),current_step:p.steps.length?p.current:null};}
 ticket(){const p=this.plan;return p?{id:p.id,revision:p.revision}:null;}
 suggestions(value,ticket){const p=this.plan;if(!this.context()||p.steps.length||ticket?.id!==p.id||ticket.revision!==p.revision||!Array.isArray(value)||!value.length||value.length>6||value.some(s=>!s||typeof s.label!=='string'||!s.label.trim()||s.label.length>100||typeof s.optional!=='boolean'))return;p.suggested=value.map(s=>({label:s.label,optional:s.optional}));this.persist();}
 useSuggestions(){const p=this.plan;if(!p?.suggested?.length)return;p.steps=p.suggested.map(s=>({...s,state:'pending'}));p.current=0;delete p.suggested;this.changed();}
 changed(){this.plan.revision++;this.persist();}
 advance(skip=false){const p=this.plan;if(!p||p.current>=p.steps.length)return;p.steps[p.current].state=skip?'skipped':'done';p.current++;this.changed();}
 back(){const p=this.plan;if(!p||!p.current)return;p.current--;p.steps[p.current].state='pending';this.changed();}
 optional(index,value){const p=this.plan;if(!p?.steps[index])return;p.steps[index].optional=!!value;this.changed();}
 pause(value){if(!this.plan)return;this.plan.paused=!!value;this.changed();}
 clear(){delete this.profile.task_plan;this.persist();}
}
