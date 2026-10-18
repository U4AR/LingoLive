/* Local turn routing. Voice features are estimates, kept only in session RAM. */
function canonical(value){
 return String(value||'').normalize('NFKD').replace(/(\p{Script=Latin})\p{M}+/gu,'$1').normalize('NFKC').toLocaleLowerCase().replace(/[’‘]/g,"'").replace(/\b(?:uh|um|erm|hmm)\b/gu,' ');
}
const tokens=value=>canonical(value).match(/[\p{L}\p{M}\p{N}]+/gu)||[];
const clean=value=>tokens(value).join('');
const pairEqual=(a,b)=>a?.known_code===b?.known_code&&a?.learning_code===b?.learning_code;
function editDistance(a,b){let row=Array.from({length:b.length+1},(_,i)=>i);for(let i=0;i<a.length;i++){const next=[i+1];for(let j=0;j<b.length;j++)next.push(Math.min(next[j]+1,row[j+1]+1,row[j]+(a[i]!==b[j])));row=next;}return row[b.length];}
const negative=new Set(['no','not','never','without','dont','cannot','cant','nahi','nahin','beda','illa','non','pas','nein','nicht','nunca','नहीं','मत','नाही','नको','ಬೇಡ','ಇಲ್ಲ','ಬೇಡಪ್ಪ','వద్దు','కాదు','இல்லை','வேண்டாம்','വേണ്ട','ഇല്ല','না','নয়','안','못']);
function negated(value){const text=canonical(value);return tokens(text).some(w=>negative.has(w))||/\b(?:don' t|don't|can't|won't|isn't|doesn't|wouldn't)\b/u.test(text)||/ಬೇಡ|ません|ない|不|没|別|别/u.test(text);}
function numbers(value){const t=tokens(value),words={one:'1',two:'2',three:'3',four:'4',five:'5',ಒಂದು:'1',ಎರಡು:'2',ಮೂರು:'3',एक:'1',दो:'2',दोन:'2',तीन:'3'};return t.filter(w=>/\p{N}/u.test(w)||words[w]).map(w=>words[w]||w).sort().join('|');}
function changedMeaning(a,b){
 if(negated(a)!==negated(b))return true;
 const na=numbers(a),nb=numbers(b);if(na&&nb&&na!==nb)return true;
 const x=tokens(a),y=tokens(b),question=w=>['what','where','when','why','how','do','does','did','are','is','ನೀವು','ಏನು','ಎಲ್ಲಿ','ಎಷ್ಟು','ಯಾಕೆ','ಹೇಗೆ'].includes(w[0]);
 return question(x)!==question(y)&&(/[?？]/u.test(a)||/[?？]/u.test(b));
}
function dice(a,b){const x=new Set(a),y=new Set(b);return 2*[...x].filter(t=>y.has(t)).length/Math.max(1,x.size+y.size);}
export function replySimilarity(text,candidate){
 const a=clean(text),b=clean(candidate);if(!a||!b||a.length>500||b.length>500)return null;
 if(a===b)return {method:'normalized',score:1,exact:true};
 if(Math.min(a.length,b.length)<8)return null;
 const ratio=Math.min(a.length,b.length)/Math.max(a.length,b.length),character=1-editDistance(a,b)/Math.max(a.length,b.length),ta=tokens(text),tb=tokens(candidate),overlap=dice(ta,tb),shared=ta.filter(t=>tb.includes(t)).length;
 const bigrams=v=>Array.from({length:Math.max(0,v.length-1)},(_,i)=>v.slice(i,i+2));const grams=dice(bigrams(a),bigrams(b));
 const partial=Math.min(a.length,b.length)>=12&&ratio>=.38&&(a.includes(b)||b.includes(a))&&(Math.min(ta.length,tb.length)>=2||Math.min(a.length,b.length)>=16);
 const method=character>=.78&&ratio>=.60?'characters':overlap>=.70&&shared>=3&&ratio>=.55?'words':grams>=.78&&ratio>=.60?'character_pairs':partial?'partial':null;
 if(!method)return null;
 return {method,score:Math.max(character,overlap*.7+ratio*.3,grams),exact:false,meaning_changed:changedMeaning(text,candidate)};
}
export function recentReplyMatch(text,records,record,now=Date.now()){
 const value=clean(text);if(!value||value.length>500)return null;
 const eligible=[...records].reverse().filter(r=>r.id!==record.id&&r.created<=record.created&&r.conversation_id===record.conversation_id&&r.profile_id===record.profile_id&&pairEqual(r.pair,record.pair)&&!r.example&&r.lesson?.replies?.length&&now-r.created>=0&&now-r.created<180000);
 const source=eligible.find(r=>r.id===record.reply_source_hint)||eligible[0];if(!source)return null;
 let best=null,changed=null;
 for(const reply of source.lesson.replies){
  const variants=[reply.words.map(w=>w.text).join(''),reply.words.filter(w=>w.is_word).map(w=>w.reading).join(' '),reply.translation];
  for(const variant of variants){const similarity=replySimilarity(text,variant);if(!similarity)continue;
   const kind=similarity.meaning_changed?'meaning_check':similarity.exact?(value.length>=12?'specific':source.id===record.reply_source_hint&&now-source.created<45000&&value.length>=2?'recent_short':'short'):'approximate';
   const match={source,reply,kind,...similarity};
   if(kind==='meaning_check'){if(!changed||match.score>changed.score)changed=match;}
   else if(!best||match.score>best.score)best=match;
  }
 }
 return best||changed;
}
const N=512,RATE=16000,mel=hz=>2595*Math.log10(1+hz/700),hz=m=>700*(10**(m/2595)-1);
const edges=Array.from({length:26},(_,i)=>Math.floor((N+1)*hz(mel(100)+(mel(7600)-mel(100))*i/25)/RATE));
const cosine=(a,b)=>a.reduce((sum,v,i)=>sum+v*b[i],0)/Math.max(1e-9,Math.hypot(...a)*Math.hypot(...b));
export const voiceDistance=(a,b)=>1-cosine(a.vector,b.vector)+Math.min(.5,Math.abs(Math.log(a.pitch/b.pitch)))*.25;
function fftPower(input){
 const re=Float64Array.from(input),im=new Float64Array(N);
 for(let i=1,j=0;i<N;i++){let bit=N>>1;for(;j&bit;bit>>=1)j^=bit;j^=bit;if(i<j)[re[i],re[j]]=[re[j],re[i]];}
 for(let len=2;len<=N;len<<=1)for(let i=0;i<N;i+=len)for(let j=0;j<len/2;j++){const angle=-2*Math.PI*j/len,c=Math.cos(angle),s=Math.sin(angle),k=i+j,l=k+len/2,tr=c*re[l]-s*im[l],ti=s*re[l]+c*im[l];re[l]=re[k]-tr;im[l]=im[k]-ti;re[k]+=tr;im[k]+=ti;}
 return Array.from({length:N/2+1},(_,i)=>re[i]**2+im[i]**2);
}
function frameFeature(samples){
 const mean=samples.reduce((a,x)=>a+x,0)/N,x=samples.map(v=>v-mean),energy=x.reduce((a,v)=>a+v*v,0);if(Math.sqrt(energy/N)<.008)return null;
 let best=0,lag=0;for(let k=48;k<=240;k++){let xy=0,aa=0,bb=0;for(let i=0;i<N-k;i++){xy+=x[i]*x[i+k];aa+=x[i]**2;bb+=x[i+k]**2;}const c=xy/Math.sqrt(aa*bb+1e-12);if(c>best){best=c;lag=k;}}
 if(best<.65||!lag)return null;
 const power=fftPower(x.map((v,i)=>(v-.97*(x[i-1]||0))*(.54-.46*Math.cos(2*Math.PI*i/(N-1)))));
 const bands=Array.from({length:24},(_,j)=>{let e=0;for(let k=edges[j];k<edges[j+2];k++){const weight=k<edges[j+1]?(k-edges[j])/Math.max(1,edges[j+1]-edges[j]):(edges[j+2]-k)/Math.max(1,edges[j+2]-edges[j+1]);e+=weight*(power[k]||0);}return Math.log(Math.max(e,1e-9));});
 const vector=Array.from({length:12},(_,k)=>bands.reduce((a,v,j)=>a+v*Math.cos(Math.PI*(k+1)*(j+.5)/24),0)/(k<2?3:1));
 return {vector,pitch:RATE/lag};
}
export class VoiceTurns{
 constructor(){this.reset();}
 reset(){this.frames=[];this.since=Date.now();}
 push(buffer,now=Date.now()){
  const view=new DataView(buffer);for(let offset=0;offset+N*2<=view.byteLength;offset+=N*2){const f=frameFeature(Array.from({length:N},(_,i)=>view.getInt16(offset+i*2,true)/32768));if(f)this.frames.push({...f,at:now});}
  this.frames=this.frames.filter(f=>now-f.at<10000).slice(-240);
 }
 finish(now=Date.now()){
  const frames=this.frames.filter(f=>now-f.at<8000);this.reset();if(frames.length<18)return null;
  const vector=frames[0].vector.map((_,i)=>frames.reduce((s,f)=>s+f.vector[i],0)/frames.length),pitches=frames.map(f=>f.pitch).sort((a,b)=>a-b),pitch=pitches[Math.floor(pitches.length/2)];
  const spread=frames.reduce((s,f)=>s+1-cosine(f.vector,vector),0)/frames.length;
  if(spread>.75)return null;return {vector,pitch,frames:frames.length,spread};
 }
}
export class SessionSpeakers{
 constructor(){this.reset();}
 reset(scope=''){this.scope=scope;this.user=[];this.other=[];}
 observe(role,sample,now=Date.now()){
  if(!sample||!['user','other'].includes(role)||sample.frames<18)return;
  this[role]=this[role].filter(x=>now-x.at<180000).slice(-2);this[role].push({sample,at:now});
 }
 classify(sample,now=Date.now()){
  if(!sample)return 'unknown';
  const distances=role=>this[role].filter(x=>now-x.at<180000).map(x=>voiceDistance(sample,x.sample));
  const user=distances('user'),other=distances('other');if(!user.length||!other.length)return 'unknown';
  const me=Math.min(...user),them=Math.min(...other);
  // Both anchors and a clear margin are required; similar/mixed voices abstain.
  if(me<.16&&them>.10&&me<them*.5)return 'user';
  if(them<.16&&me>.10&&them<me*.5)return 'other';return 'unknown';
 }
}
