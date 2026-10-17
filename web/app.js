import {baseLanguage,validateLesson,wordPieces} from './core.mjs';
import {Memory} from './memory.js';
import {Learners} from './learners.mjs';
import {approximateLocation} from './signals.mjs';
import {newConversation,restoreConversation,contextForRecord,latestContextSummary,matchesSuggestedReply} from './context.mjs';
import {LiveMicrophone} from './microphone.js';
import {renderGoogleSignIn,forgetGoogleSelection} from './google-signin.js';
const $=id=>document.getElementById(id);
const element=(tag,className,text)=>{const node=document.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=text;return node;};
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const welcomeTemplate=$('lesson-panel').firstElementChild.cloneNode(true);
const conversationTemplate=$('transcripts').firstElementChild.cloneNode(true);
const learners=new Learners(),profileStores=new Map(),audioSamples=new Map(),deletedRecords=new Set();
const state={records:[],selected:null,languages:[],pronunciation:false,connected:false,queue:[],processing:false,lastRequest:0,storage:null,view:'conversation',memoryFailed:false,queueEpoch:0,conversation:newConversation(),learner:learners.current,location:null};
const learnerKey=base=>learners.key(base);
let noticeTimer,locationWatch=null;
function notice(message,error=false){$('notice').textContent=message;$('notice').classList.toggle('error',error);$('notice').hidden=false;clearTimeout(noticeTimer);noticeTimer=setTimeout(()=>$('notice').hidden=true,error?14000:6000);}
function profile(){const known=state.languages.find(x=>x.code===$('known-language').value);const learning=state.languages.find(x=>x.code===$('learning-language').value);return {known_code:known.code,known_name:known.name,learning_code:learning.code,learning_name:learning.name};}
function validProfile(){if(!state.languages.length){notice('The language list is still loading. Try again in a moment.',true);return false;}const pair=profile();if(baseLanguage(pair.known_code)===baseLanguage(pair.learning_code)){notice('Choose different languages to understand and learn.',true);return false;}return true;}
function connected(value,mode='access_code'){state.connected=value;state.connectionMode=value?mode:null;$('connection-dot').classList.toggle('connected',value);$('connection-label').textContent=value?'Connected':'Connect';$('disconnect').hidden=!value;}
async function api(path,options={}){
  let response;
  try {response=await fetch(path,{credentials:'same-origin',...options,headers:{'Content-Type':'application/json',...options.headers}});}catch{throw new Error('Could not reach your learning space. Check your internet connection; saved lessons are still available.');}
  if(response.status===204)return null;
  let data;try{data=await response.json();}catch{throw new Error('The service returned an unreadable response. Try again shortly.');}
  if(!response.ok){if(response.status===401)connected(false);const error=new Error(response.status===429?'A little pause: the lesson limit was reached. Your phrase is saved; try again shortly.':typeof data.detail==='string'?data.detail:'That phrase could not be processed. Try a shorter phrase.');error.status=response.status;throw error;}
  return data;
}
async function save(record){const store=profileStores.get(record.profile_id)||state.storage;if(!store||deletedRecords.has(record.id))return;try{const {audio_context,context_location,lesson_context,...stored}=record;if(lesson_context){const {location_context,...textContext}=lesson_context;stored.lesson_context=textContext;}await store.put(stored);}catch{state.memoryFailed=true;notice('Browser storage is full or unavailable. This conversation is only kept until you close the page.',true);}}
function updateCount(){$('saved-count').textContent=state.records.length.toString();}
function statusLabel(record){const prefix=record.speaker==='likely_user'?'Likely you · ':record.speaker==='likely_other'?'Likely other speaker · ':'';return prefix+({confirmed:'You said this',queued:'Waiting for a lesson',loading:'Understanding…',error:'Lesson needs a retry',familiar:'Not the learning language',transcribed:'Transcript saved',ready:'Lesson saved'}[record.status]||'Transcript saved');}
function timeLabel(stamp){return new Date(stamp).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});}
function renderTranscripts(){
  const list=$('transcripts');if(!state.records.some(r=>r.conversation_id===state.conversation.id)){list.replaceChildren(conversationTemplate.cloneNode(true));return;}
  list.replaceChildren();
  for(const record of state.records.filter(r=>r.conversation_id===state.conversation.id).slice(-100)){
    const button=element('button','transcript'+(state.selected?.id===record.id?' selected':''));button.type='button';button.dataset.record=record.id;button.setAttribute('aria-pressed',state.selected?.id===record.id?'true':'false');
    const phrase=element('span','phrase',record.text);phrase.dir='auto';button.append(phrase);
    const meta=element('span','phrase-meta');meta.append(element('span','',statusLabel(record)),element('span','',timeLabel(record.created)));button.append(meta);button.onclick=()=>{state.selected=record;renderTranscripts();renderLesson();};list.append(button);
  }
  list.scrollTop=list.scrollHeight;
}
function wordDialog(word,anchor){
  const bubble=$('word-dialog');if(bubble.open)bubble.close();$('word-original').textContent=word.text;$('word-reading').textContent=word.reading;$('word-meaning').textContent=word.meaning;$('word-note').textContent=word.note;$('word-note').hidden=!word.note;
  bubble.show();const rect=anchor.getBoundingClientRect(),width=bubble.offsetWidth,height=bubble.offsetHeight;
  const above=rect.bottom+height+12>innerHeight;const left=Math.max(10,Math.min(innerWidth-width-10,rect.left+rect.width/2-width/2));
  bubble.style.left=left+'px';bubble.style.top=Math.max(10,above?rect.top-height-10:rect.bottom+10)+'px';bubble.dataset.placement=above?'above':'below';
}
$('settings-open').onclick=()=>{const settings=$('context-settings');settings.open=!settings.open;$('settings-open').setAttribute('aria-expanded',String(settings.open));if(settings.open)settings.scrollIntoView({block:'start',behavior:'smooth'});};
$('settings-close').onclick=()=>{$('context-settings').open=false;$('settings-open').setAttribute('aria-expanded','false');$('settings-open').focus();};
document.addEventListener('click',event=>{if($('word-dialog').open&&!event.target.closest('#word-dialog,.word'))$('word-dialog').close();});
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&$('word-dialog').open)$('word-dialog').close();});
window.addEventListener('resize',()=>{if($('word-dialog').open)$('word-dialog').close();});
function renderWords(words,className){const node=element('div',className);node.dir='auto';for(const piece of wordPieces(words,state.pronunciation)){if(piece.prefix)node.append(document.createTextNode(piece.prefix));if(piece.word.is_word){const button=element('button','word',piece.text);button.type='button';button.setAttribute('aria-label',piece.text+' · word meaning');button.onclick=()=>wordDialog(piece.word,button);node.append(button);}else node.append(document.createTextNode(piece.text));}return node;}
async function speak(text,code){await stopListening();if(!('speechSynthesis' in window)){notice('Pronunciation playback is not supported by this browser.',true);return;}speechSynthesis.cancel();const utterance=new SpeechSynthesisUtterance(text);utterance.lang=code;utterance.rate=.88;utterance.onerror=()=>notice('This voice is unavailable. Install a voice for the learning language or read the pronunciation text.',true);speechSynthesis.speak(utterance);}
function renderLesson(){
  const record=state.selected;if(!record){$('lesson-panel').replaceChildren(welcomeTemplate.cloneNode(true));$('try-example').onclick=showExample;return;}
  const panel=$('lesson-panel');panel.replaceChildren();
  if(record.example)panel.append(element('div','example-banner','Prepared Japanese / English example · not saved to your history'));
  const content=element('div','lesson-content');panel.append(content);
  if(!record.example){
    const intent=element('details','intent-actions reply-context-tools');intent.append(element('summary','','More options'));const goal=element('button','text-button','Use these words as my goal');goal.type='button';
    goal.onclick=async()=>{
      $('conversation-goal').value=record.text.slice(0,600);$('context-settings').open=true;$('settings-open').setAttribute('aria-expanded','true');
      if(record.text.length>600){$('conversation-goal').focus();notice('Shorten this to the part you want to do, then save your goal.');return;}
      record.speaker='user';await save(record);setGoal(record.text,record.id);notice('Goal saved. New replies will use what you want to do.');
    };intent.append(goal);content.append(intent);
  }
  if(!record.lesson?.contains_learning_language||['queued','loading'].includes(record.status)){
    content.classList.add('lesson-status');content.append(element('p','eyebrow',record.pair.learning_name.toUpperCase()+' → '+record.pair.known_name.toUpperCase()));
    const phrase=element('div','source-words',record.text);phrase.dir='auto';content.append(phrase);
    content.append(element('h2','',record.status==='loading'?'Finding the meaning…':record.status==='queued'?'A little lesson is on its way.':record.status==='familiar'?'A phrase to keep.':'Your phrase is here.'));
    content.append(element('p','',record.error||record.lesson?.explanation||(record.status==='queued'||record.status==='loading'?'Your words stay here while Google prepares the explanation.':'Turn it into a word-by-word lesson whenever you’re ready.')));
    if(!['loading','queued'].includes(record.status)){const retry=element('button','small-button','Teach this phrase →');retry.onclick=()=>queueLesson(record);content.append(retry);}return;
  }
  const lesson=record.lesson;content.append(element('p','heard-label',record.speaker==='user'||record.speaker==='likely_user'?'You said':'Heard'));const replyGoal=record.lesson_context?.user_goal??record.context_goal;
  if(record.error)content.append(element('p','reply-goal',record.error));
  const top=element('div','lesson-top');top.append(element('p','eyebrow',record.pair.learning_name.toUpperCase()+' → '+record.pair.known_name.toUpperCase()));
  const toggle=element('div','mode-switch');toggle.setAttribute('role','group');toggle.setAttribute('aria-label','Text display');for(const [value,label]of [[false,'Original'],[true,'Pronunciation']]){const button=element('button',state.pronunciation===value?'active':'',label);button.setAttribute('aria-pressed',String(state.pronunciation===value));button.onclick=()=>{state.pronunciation=value;renderLesson();};toggle.append(button);}top.append(toggle);content.append(top,renderWords(lesson.words,'source-words'),element('p','translation',lesson.translation));
  const explanation=element('details','phrase-explanation');explanation.append(element('summary','','Meaning & usage'),element('p','explanation',lesson.explanation));if(lesson.tip)explanation.append(element('div','tip',lesson.tip));content.append(explanation);
  const heading=element('div','reply-heading');heading.append(element('h3','','Try saying'),element('span','',''));content.append(heading);
  if(replyGoal)explanation.append(element('p','reply-goal','Your goal · '+replyGoal));
  else if(lesson.context_summary)explanation.append(element('p','reply-goal','Possible context · '+lesson.context_summary.slice(0,180)+(lesson.context_summary.length>180?'…':'')));
  if(!record.example&&record.conversation_id===state.conversation.id){const refresh=element('button','text-button','Update replies for my goal');refresh.onclick=()=>{record.context_goal=state.conversation.goal;record.context_notes=state.learner.notes||'';record.context_setting=state.conversation.place||'auto';queueLesson(record);};content.querySelector('.reply-context-tools')?.append(refresh);}
  for(const reply of lesson.replies){const card=element('div','reply');card.append(element('div','reply-label',reply.label),renderWords(reply.words,'reply-words'));const foot=element('div','reply-footer');foot.append(element('p','reply-translation',reply.translation));const actions=element('div','reply-actions');const text=reply.words.map(x=>x.text).join('');const listen=element('button','icon-button','▷');listen.setAttribute('aria-label','Hear reply: '+reply.label);listen.onclick=()=>speak(text,record.pair.learning_code);const said=element('button','text-button','I said this');said.onclick=()=>confirmReply(reply,record);const more=element('details','reply-more');const menu=element('summary','','⋯');menu.setAttribute('aria-label','More reply options');more.append(menu,said);actions.append(more);const copy=element('button','icon-button','⧉');copy.setAttribute('aria-label','Copy reply: '+reply.label);copy.onclick=async()=>{try{await navigator.clipboard.writeText(text);notice('Reply copied.');}catch{notice('Copy is unavailable. You can select and copy the original text.',true);}};actions.append(listen,copy);foot.append(actions);card.append(foot);content.append(card);}
}
function refresh(record){updateCount();renderTranscripts();if(state.selected?.id===record.id)renderLesson();if(state.view==='saved')renderSaved();}
async function accept(text,pair=profile(),conversation=state.conversation){
  if(!text?.trim())return;
  const record={id:crypto.randomUUID(),text,created:Date.now(),pair,status:'transcribed',lesson:null,conversation_id:conversation.id,profile_id:conversation.profile_id||state.learner.id,context_goal:conversation.goal,inferred_goal:conversation.inferred_goal||'',context_notes:conversation.memory_notes||'',context_setting:conversation.place||'auto',speaker:'unattributed'};if(record.profile_id!==state.learner.id){await profileStores.get(record.profile_id)?.put(record);return;}
  const snippet=conversation.id===state.conversation.id?microphone.audioContextSnippet():null;if(snippet)audioSamples.set(record.id,snippet);
  if(conversation.id===state.conversation.id&&state.location&&Date.now()/1000-state.location.captured_at<=300)record.context_location=state.location;
  state.records.push(record);persistConversation();if(conversation.id===state.conversation.id){state.selected=record;$('interim').textContent='';}await save(record);refresh(record);
  if(conversation.id!==state.conversation.id)return;
  if(text.length>1000){audioSamples.delete(record.id);record.error='This phrase is long. Copy a shorter part into the text box to make a lesson.';record.status='error';await save(record);refresh(record);return;}
  queueLesson(record);
}
function queueLesson(record){
  if(!state.connected){audioSamples.delete(record.id);record.status='transcribed';refresh(record);openConnection();return;}
  if(['queued','loading'].includes(record.status))return;
  if(state.queue.length>=20){audioSamples.delete(record.id);record.status='error';record.error='Several lessons are waiting. Your phrase is saved; retry it when the queue is shorter.';save(record);refresh(record);return;}
  record.status='queued';record.queue_epoch=state.queueEpoch;delete record.error;state.queue.push(record);save(record);refresh(record);processQueue();
}
async function processQueue(){
  if(state.processing)return;state.processing=true;
  try{while(state.queue.length){const record=state.queue.shift();if(!state.records.some(x=>x.id===record.id))continue;
    await sleep(Math.max(0,2500-(Date.now()-state.lastRequest)));if(!state.records.some(x=>x.id===record.id))continue;
    if(record.queue_epoch!==state.queueEpoch){record.status='transcribed';await save(record);refresh(record);continue;}
    record.status='loading';refresh(record);state.lastRequest=Date.now();
    try{const context={...contextForRecord(state.records,record),memory_notes:record.context_notes||'',setting:record.context_setting||'auto',...seenVocabulary(record)};
      if(record.context_location&&Date.now()/1000-record.context_location.captured_at<=300)context.location_context=record.context_location;
      const sample=audioSamples.get(record.id);const lesson=await api('/v1/teach',{method:'POST',body:JSON.stringify({text:record.text,...record.pair,...context,...(sample?{audio_context:sample}:{})})});record.lesson=validateLesson(lesson,record.text);record.lesson_context=context;
      if(record.speaker!=='user'){
        if(lesson.current_speaker==='user'&&['medium','high'].includes(lesson.speaker_confidence))record.speaker='likely_user';
        else if(lesson.current_speaker==='other'&&['medium','high'].includes(lesson.speaker_confidence))record.speaker='likely_other';
        else if(matchesSuggestedReply(record.text,context.previous_replies))record.speaker='likely_user';
        else record.speaker='unattributed';
      }
      if(record.conversation_id===state.conversation.id&&record.profile_id===state.learner.id&&!state.conversation.goal&&['user','likely_user'].includes(record.speaker)&&lesson.inferred_user_intent){state.conversation.inferred_goal=lesson.inferred_user_intent.slice(0,300);}
      record.status=lesson.contains_learning_language?'ready':'familiar';delete record.error;}
    catch(error){record.status='error';record.error=error.message;if(error.status===401)notice('Your connection expired. Open Connect to sign in again; your phrases are saved.',true);}
    audioSamples.delete(record.id);await save(record);const present=state.records.findIndex(x=>x.id===record.id);if(present>=0&&!deletedRecords.has(record.id)){state.records[present]=record;if(state.selected?.id===record.id)state.selected=record;refresh(record);renderContext();persistConversation();}
  }}finally{state.processing=false;}
}
function renderSaved(){
  const query=$('saved-search').value.toLocaleLowerCase();const list=$('saved-list');list.replaceChildren();
  const found=state.records.filter(record=>JSON.stringify([record.text,record.lesson,record.pair]).toLocaleLowerCase().includes(query)).slice().reverse();
  if(!found.length){list.append(element('div','saved-empty',query?'No matching phrases yet. Try a different word.':'A little library starts with one conversation. Your saved phrases will appear here.'));return;}
  for(const record of found){const card=element('article','saved-card');card.dataset.record=record.id;const meta=element('div','saved-meta');meta.append(element('span','',record.pair.learning_name+' · '+new Date(record.created).toLocaleDateString()));const remove=element('button','text-button','Remove');remove.setAttribute('aria-label','Remove saved phrase: '+record.text);remove.onclick=async()=>{deletedRecords.add(record.id);audioSamples.delete(record.id);state.records=state.records.filter(x=>x.id!==record.id);state.queue=state.queue.filter(x=>x.id!==record.id);try{await state.storage?.remove(record.id);}catch{notice('Could not remove this phrase from browser storage.',true);}if(state.selected?.id===record.id)state.selected=null;if(state.conversation.goal_source_id===record.id)setGoal('');updateCount();renderTranscripts();renderLesson();renderSaved();};meta.append(remove);card.append(meta);const button=element('button','open-saved');const phrase=element('h2','',record.text);phrase.dir='auto';button.append(phrase,element('p','',record.lesson?.translation||statusLabel(record)));button.onclick=()=>{state.selected=record;setView('conversation');renderLesson();renderTranscripts();$('lesson-panel').scrollIntoView({behavior:'smooth',block:'start'});};card.append(button);list.append(card);}
}
function seenVocabulary(record){
  const index=state.records.findIndex(r=>r.id===record.id),words=[],seen=new Set();
  for(const old of state.records.slice(0,index).reverse()){
    if(old.pair?.learning_code!==record.pair.learning_code||old.pair?.known_code!==record.pair.known_code)continue;
    for(const word of old.lesson?.words||[]){if(word.is_word&&word.text.length<=40&&!seen.has(word.text)){seen.add(word.text);words.push({text:word.text,meaning:word.meaning.slice(0,120)});if(words.length===12)return {previously_seen_words:words};}}
  }
  return words.length?{previously_seen_words:words}:{};
}
async function confirmReply(reply,source){
  if(source.conversation_id!==state.conversation.id){notice('Start a new conversation to use this older reply.');return;}
  const record={id:crypto.randomUUID(),text:reply.words.map(w=>w.text).join(''),created:Date.now(),pair:source.pair,status:'confirmed',lesson:null,speaker:'user',profile_id:state.learner.id,conversation_id:state.conversation.id,context_goal:state.conversation.goal};
  state.records.push(record);await save(record);updateCount();renderTranscripts();persistConversation();notice('Remembered as something you said.');
}
function renderLearners(){
  $('learner-profile').replaceChildren();for(const p of learners.data.profiles){const option=element('option','',p.name);option.value=p.id;$('learner-profile').append(option);}$('learner-profile').value=state.learner.id;
}
function clearSignals(){
  if(locationWatch!==null)navigator.geolocation?.clearWatch(locationWatch);locationWatch=null;state.location=null;audioSamples.clear();microphone.includeAmbience=false;microphone.ambience=[];
  $('use-location').checked=false;$('use-audio-context').checked=false;$('location-state').textContent='Location is off';$('open-map').hidden=true;
}
async function switchLearner(id){
  state.queueEpoch++;await stopListening();for(const r of state.queue){r.status='transcribed';await save(r);}state.queue=[];clearSignals();
  state.learner=learners.select(id);state.selected=null;state.records=[];state.storage=null;
  try{state.conversation=restoreConversation(JSON.parse(localStorage.getItem(learnerKey('lingolive-conversation'))||'null'));}catch{state.conversation=newConversation();}
  state.conversation.profile_id=state.learner.id;
  try{state.storage=profileStores.get(id)||await new Memory(learners.key('lingolive-learning')).open();profileStores.set(id,state.storage);state.records=await state.storage.all();for(const r of state.records)r.profile_id=id;}catch{notice('Saved lessons are unavailable for this learner.',true);}
  try{const p=JSON.parse(localStorage.getItem(learnerKey('lingolive-profile'))||'null');$('known-language').value=p?.known_code||'en-US';$('learning-language').value=p?.learning_code||'ja-JP';}catch{}
  $('conversation-goal').value=state.conversation.goal;$('memory-notes').value=state.learner.notes||'';$('saved-search').value='';renderLearners();persistConversation();renderContext();updateCount();renderTranscripts();renderLesson();renderSaved();
}
$('learner-profile').onchange=()=>switchLearner($('learner-profile').value);
$('add-learner').onclick=()=>{try{const p=learners.create($('learner-name').value);$('learner-name').value='';switchLearner(p.id);}catch(error){notice(error.message,true);}};
$('save-memory').onclick=()=>{learners.setNotes($('memory-notes').value);state.learner=learners.current;persistConversation();notice('Memory notes saved for '+state.learner.name+'.');};
$('context-setting').onchange=()=>{state.conversation.place=$('context-setting').value;persistConversation();};
$('use-audio-context').onchange=()=>{microphone.includeAmbience=$('use-audio-context').checked;if(!microphone.includeAmbience){audioSamples.clear();microphone.ambience=[];}};
$('use-location').onchange=()=>{
  if(locationWatch!==null)navigator.geolocation?.clearWatch(locationWatch);locationWatch=null;state.location=null;
  if(!$('use-location').checked){$('location-state').textContent='Location is off';$('open-map').hidden=true;return;}
  if(!navigator.geolocation){$('use-location').checked=false;notice('Location is unavailable. Replies can still use the conversation.',true);return;}
  const owner=state.learner.id;$('location-state').textContent='Requesting approximate location…';
  locationWatch=navigator.geolocation.watchPosition(position=>{
    if(owner!==state.learner.id||!$('use-location').checked)return;
    try{state.location=approximateLocation(position);$('location-state').textContent='Approximate location is on';$('open-map').href='https://www.google.com/maps?q='+state.location.latitude+','+state.location.longitude;$('open-map').hidden=false;}catch(error){notice(error.message,true);}
  },()=>{if(owner!==state.learner.id)return;if(owner===state.learner.id){$('location-state').textContent='Location unavailable; using conversation only';$('use-location').checked=false;}if(locationWatch!==null)navigator.geolocation.clearWatch(locationWatch);locationWatch=null;}, {enableHighAccuracy:false,maximumAge:60000,timeout:12000});
};
function persistConversation(){
  state.conversation.memory_notes=state.learner.notes||'';state.conversation.profile_id=state.learner.id;
  state.conversation.updated=Date.now();
  try{localStorage.setItem(learnerKey('lingolive-conversation'),JSON.stringify(state.conversation));}catch{notice('Your goal is available for this visit, but could not be saved on this browser.',true);}
}
function renderContext(){
  $('goal-summary').textContent=state.conversation.goal?'Your goal: '+state.conversation.goal:state.conversation.inferred_goal?'Likely goal: '+state.conversation.inferred_goal:'Replies follow the conversation';
  $('context-setting').value=state.conversation.place||'auto';
  const summary=latestContextSummary(state.records,state.conversation.id);$('inferred-context').textContent=summary?'From this conversation · '+summary:'';$('inferred-context').hidden=!summary;
}
function setGoal(text,sourceId=''){
  state.conversation.goal=text.trim().slice(0,600);state.conversation.inferred_goal='';state.conversation.goal_source_id=sourceId;
  state.conversation.profile_id=state.learner.id;renderLearners();$('memory-notes').value=state.learner.notes||'';
  $('conversation-goal').value=state.conversation.goal;persistConversation();renderContext();
}
$('goal-form').onsubmit=event=>{event.preventDefault();setGoal($('conversation-goal').value);notice(state.conversation.goal?'Goal saved. It will guide your next replies.':'Goal cleared. Replies will follow the conversation.');};
$('clear-goal').onclick=()=>{setGoal('');notice('Goal cleared.');};
$('new-conversation').onclick=async()=>{
  state.queueEpoch++;await stopListening();
  for(const record of state.queue){record.status='transcribed';await save(record);}
  state.queue=[];audioSamples.clear();state.conversation=newConversation();state.conversation.profile_id=state.learner.id;state.selected=null;$('conversation-goal').value='';persistConversation();renderContext();renderTranscripts();renderLesson();notice('New conversation started. Previous lessons are still in Saved.');
};
async function stopListening(){if(microphone.running||microphone.context){$('listen-button').disabled=true;await microphone.stop();$('listen-button').disabled=false;}listeningUI(false);}
function listeningUI(listening){$('listen-label').textContent=listening?'Stop listening':'Start listening';$('listen-button').classList.toggle('recording',listening);$('listening-wave').hidden=!listening;$('live-state').classList.toggle('live',listening);$('listen-button').setAttribute('aria-pressed',String(listening));}
function setView(view){state.view=view;const saved=view==='saved';$('saved-view').hidden=!saved;$('conversation-view').hidden=saved;$('listen-dock').hidden=saved;$('saved-tab').classList.toggle('active',saved);$('conversation-tab').classList.toggle('active',!saved);$('saved-tab').setAttribute('aria-current',saved?'page':'false');$('conversation-tab').setAttribute('aria-current',saved?'false':'page');if(saved){stopListening();renderSaved();}window.scrollTo({top:0});}
let serverConfigured=false,googleRequired=false,googleCredential='',connectionAttempt=0,connectionConfig=null;
function connectionMode(){return $('method-key').checked?'api_key':'access_code';}
function clearCredentials(){$('access-code').value='';$('personal-api-key').value='';googleCredential='';}
async function applyConnectionMode(attempt){
  googleCredential='';$('google-signin').replaceChildren();$('google-signin').hidden=true;$('connect-submit').disabled=true;
  const ownKey=connectionMode()==='api_key';$('key-fields').hidden=!ownKey;$('code-fields').hidden=ownKey;googleRequired=!ownKey&&Boolean(connectionConfig?.google_required);
  $('connection-description').textContent=ownKey?'Use your Google AI Studio key for listening and replies.':googleRequired?'Sign in with an invited Google account, then enter your private access code.':'Use the access code shared by your host.';
  if(!connectionConfig){$('connection-message').textContent='Could not load connection options. Close and try again.';return;}
  const available=ownKey?connectionConfig.api_key_available:connectionConfig.access_code_available;
  if(!available){$('connection-message').textContent=ownKey?'Personal API keys are disabled by this host.':'Host access is not available. You can use your own Google API key.';return;}
  $('connection-message').textContent=state.connected?('Connected using '+(state.connectionMode==='api_key'?'your Google API key.':'the access code.')):ownKey?'Google checks your key when you listen or request a lesson.':'Your host can share the access code.';
  if(!googleRequired){$('connect-submit').disabled=false;return;}
  $('connection-message').textContent='Only invited Google accounts can use the access code.';$('google-signin').hidden=false;
  try{await renderGoogleSignIn(connectionConfig,$('google-signin'),credential=>{
    if(attempt!==connectionAttempt||!$('connection-dialog').open)return;
    googleCredential=credential;$('connect-submit').disabled=!credential;
    $('connection-message').textContent=credential?'Google account selected. Enter your access code to connect.':'Google sign-in was not completed. Please try again.';
  });}catch(error){if(attempt===connectionAttempt)$('connection-message').textContent=error.message;}
}
async function openConnection(){
  await stopListening();const attempt=++connectionAttempt;clearCredentials();connectionConfig=null;$('google-signin').replaceChildren();$('google-signin').hidden=true;$('connect-submit').disabled=true;
  $('connection-message').textContent='Loading connection options…';
  if(!$('connection-dialog').open)$('connection-dialog').showModal();
  try{
    const config=await api('/v1/auth/config');if(attempt!==connectionAttempt)return;connectionConfig=config;
    if(state.connected)$(state.connectionMode==='api_key'?'method-key':'method-code').checked=true;
    if(!config.access_code_available&&config.api_key_available)$('method-key').checked=true;
    if(!config.api_key_available&&config.access_code_available)$('method-code').checked=true;
    $('method-key').disabled=!config.api_key_available;$('method-code').disabled=!config.access_code_available;
    await applyConnectionMode(attempt);
  }catch(error){if(attempt===connectionAttempt)$('connection-message').textContent=error.message;}
}
for(const id of ['method-code','method-key'])$(id).onchange=()=>{clearCredentials();applyConnectionMode(++connectionAttempt);};
const microphone=new LiveMicrophone({status:message=>{$('live-state').textContent=message;},interim:text=>{$('interim').textContent=text;},final:(text,pair,conversation)=>accept(text,pair,conversation),error:message=>{listeningUI(false);notice(message,true);}});
$('listen-button').onclick=async()=>{
  if(microphone.running){await stopListening();return;}
  if(!validProfile())return;
  if(!state.connected){await openConnection();return;}
  try{await api('/v1/session');microphone.pair=profile();microphone.conversationSnapshot=state.conversation;listeningUI(true);await microphone.start();if(!microphone.running)listeningUI(false);}catch(error){listeningUI(false);notice(error.message,true);}
};
$('phrase-form').onsubmit=async event=>{event.preventDefault();if(!validProfile())return;if(!state.connected){await openConnection();return;}const text=$('phrase-input').value;if(!text.trim())return;$('phrase-input').value='';await accept(text);};
async function showExample(){try{await stopListening();const example=await fetch('/assets/example.json').then(r=>r.json());state.selected={...example,id:'example',example:true,pair:{known_code:'en-US',known_name:'English',learning_code:'ja-JP',learning_name:'Japanese'},status:'ready'};state.pronunciation=false;renderLesson();}catch{notice('The example could not be loaded. Reconnect and refresh the page.',true);}}
$('try-example').onclick=showExample;
$('connection-dialog').addEventListener('cancel',()=>{clearCredentials();connectionAttempt++;});
$('connection-open').onclick=openConnection;$('connection-close').onclick=()=>{clearCredentials();connectionAttempt++;$('connection-dialog').close();};$('word-close').onclick=()=>$('word-dialog').close();
$('connection-form').onsubmit=async event=>{
  event.preventDefault();const mode=connectionMode(),token=$('access-code').value.trim(),key=$('personal-api-key').value.trim();
  if(googleRequired&&!googleCredential){$('connection-message').textContent='Sign in with Google first.';return;}
  if(mode==='api_key'?!key:!token){$('connection-message').textContent=mode==='api_key'?'Enter your Google API key.':'Enter the access code shared by your host.';return;}
  $('connect-submit').disabled=true;
  try{await api('/v1/session',{method:'POST',body:JSON.stringify(mode==='api_key'?{mode,api_key:key}:{mode,token,...(googleRequired?{google_credential:googleCredential}:{})})});connected(true,mode);clearCredentials();connectionAttempt++;$('connection-dialog').close();notice('You’re connected. Ready when you are.');}
  catch(error){$('connection-message').textContent=error.message;}finally{$('connect-submit').disabled=false;}
};
$('disconnect').onclick=async()=>{await stopListening();try{await api('/v1/session',{method:'DELETE'});connected(false);clearCredentials();connectionAttempt++;forgetGoogleSelection();$('connection-dialog').close();notice('Disconnected. Your saved lessons stay on this browser.');}catch(error){$('connection-message').textContent=error.message;}};
$('conversation-tab').onclick=()=>setView('conversation');$('saved-tab').onclick=()=>setView('saved');$('saved-search').oninput=renderSaved;
$('clear-saved').onclick=()=>$('clear-dialog').showModal();$('clear-cancel').onclick=()=>$('clear-dialog').close();$('clear-confirm').onclick=async()=>{try{for(const r of state.records)deletedRecords.add(r.id);audioSamples.clear();await state.storage?.clear();state.records=[];state.queue=[];state.selected=null;localStorage.removeItem(learnerKey('lingolive-conversation'));updateCount();renderSaved();$('clear-dialog').close();location.reload();}catch{notice('Could not clear browser storage. Try clearing this site’s data in browser settings.',true);}};
for(const id of ['known-language','learning-language'])$(id).onchange=async()=>{await stopListening();state.conversation=newConversation(state.conversation.goal);state.conversation.profile_id=state.learner.id;persistConversation();renderContext();renderTranscripts();state.selected=null;renderLesson();try{localStorage.setItem(learnerKey('lingolive-profile'),JSON.stringify(profile()));}catch{}validProfile();};
$('swap-languages').onclick=async()=>{await stopListening();state.conversation=newConversation(state.conversation.goal);state.conversation.profile_id=state.learner.id;persistConversation();renderContext();renderTranscripts();state.selected=null;renderLesson();const known=$('known-language').value;$('known-language').value=$('learning-language').value;$('learning-language').value=known;try{localStorage.setItem(learnerKey('lingolive-profile'),JSON.stringify(profile()));}catch{}};
document.addEventListener('visibilitychange',()=>{if(document.hidden){stopListening();clearSignals();}});window.addEventListener('pagehide',()=>{clearSignals();microphone.stop(false);});window.addEventListener('offline',()=>{stopListening();notice('You’re offline. Saved lessons remain available; new listening needs a connection.',true);});
async function init(){
  if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{});
  state.languages=await fetch('/assets/languages.json').then(r=>r.json());
  for(const id of ['known-language','learning-language']){for(const language of state.languages){const option=element('option','',language.name);option.value=language.code;$(id).append(option);}}
  let preferences;try{preferences=JSON.parse(localStorage.getItem(learnerKey('lingolive-profile'))||'null');}catch{}
  $('known-language').value=state.languages.some(x=>x.code===preferences?.known_code)?preferences.known_code:'en-US';$('learning-language').value=state.languages.some(x=>x.code===preferences?.learning_code)?preferences.learning_code:'ja-JP';
  try{state.conversation=restoreConversation(JSON.parse(localStorage.getItem(learnerKey('lingolive-conversation'))||'null'));}catch{state.conversation=newConversation();}
  state.conversation.profile_id=state.learner.id;renderLearners();$('memory-notes').value=state.learner.notes||'';
  $('conversation-goal').value=state.conversation.goal;persistConversation();renderContext();
  try{state.storage=await new Memory(learners.key('lingolive-learning')).open();profileStores.set(state.learner.id,state.storage);state.records=await state.storage.all();for(const r of state.records)r.profile_id=state.learner.id;for(const record of state.records)if(['queued','loading'].includes(record.status)){record.status='transcribed';record.error='The page was closed before the lesson finished. Your phrase is saved; retry it.';await save(record);}updateCount();renderTranscripts();renderContext();}catch{state.storage=null;state.memoryFailed=true;notice('Persistent browser storage is unavailable. This conversation will only last while this page is open.',true);$('storage-note').textContent='Browser storage is unavailable. This session is temporary.';}
  try{const health=await api('/health');serverConfigured=health.configured;if(serverConfigured||health.byok_available){try{const session=await api('/v1/session');connected(true,session.mode);}catch{connected(false);}}}catch{notice('The live service is unavailable. You can explore the prepared example or your saved lessons.',true);}
}
init().catch(()=>notice('The page could not finish loading. Please refresh to try again.',true));
