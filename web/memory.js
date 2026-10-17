export class Memory {
  constructor(name='lingolive-learning'){this.name=name;}
  async open() {
    this.db=await new Promise((resolve,reject)=>{
      const request=indexedDB.open(this.name,1);
      request.onupgradeneeded=()=>request.result.createObjectStore('phrases',{keyPath:'id'});
      request.onsuccess=()=>resolve(request.result); request.onerror=()=>reject(request.error);
    });
    this.db.onversionchange=()=>this.db.close(); return this;
  }
  async all() { return new Promise((resolve,reject)=>{const r=this.db.transaction('phrases').objectStore('phrases').getAll(); r.onsuccess=()=>resolve(r.result.sort((a,b)=>a.created-b.created)); r.onerror=()=>reject(r.error);}); }
  async change(method,value) { return new Promise((resolve,reject)=>{const tx=this.db.transaction('phrases','readwrite');tx.objectStore('phrases')[method](value);tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error);}); }
  put(value) { return this.change('put',value); }
  remove(id) { return this.change('delete',id); }
  clear() { return this.change('clear'); }
}
