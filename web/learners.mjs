/* Independent local profiles, without a cloud history database or account sync. */
const UUID=/^[a-f0-9-]{36}$/i;
export class Learners {
  constructor(storage){
    try{this.storage=storage||globalThis.localStorage;}catch{this.storage=null;}
    try{this.data=JSON.parse(this.storage.getItem('lingolive-learners')||'null');}catch{}
    if(!Array.isArray(this.data?.profiles)||!this.data.profiles.length||!this.data.profiles.every(p=>UUID.test(p.id)&&typeof p.name==='string'&&typeof p.namespace==='string'))this.data={active:'',profiles:[{id:crypto.randomUUID(),name:'Me',namespace:'',notes:''}]};
    if(!this.data.profiles.some(p=>p.id===this.data.active))this.data.active=this.data.profiles[0].id;
    this.persist();
  }
  get current(){return this.data.profiles.find(p=>p.id===this.data.active);}
  persist(){try{this.storage.setItem('lingolive-learners',JSON.stringify(this.data));}catch{}}
  key(base,profile=this.current){return base+(profile.namespace?':'+profile.namespace:'');}
  create(name){
    if(this.data.profiles.length>=8)throw new Error('This browser supports up to eight learner profiles.');
    const id=crypto.randomUUID();const profile={id,name:name.trim().slice(0,40)||'Learner '+(this.data.profiles.length+1),namespace:id,notes:''};this.data.profiles.push(profile);this.persist();return profile;
  }
  select(id){if(!this.data.profiles.some(p=>p.id===id))throw new Error('Choose an existing learner.');this.data.active=id;this.persist();return this.current;}
  setNotes(text){this.current.notes=text.trim().slice(0,800);this.persist();}
}
