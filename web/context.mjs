/* Bounded context is kept on this browser and shared only for requested lessons. */
export function newConversation(goal='') {
  return {id:crypto.randomUUID(),goal:String(goal).slice(0,600),goal_source_id:'',inferred_goal:'',place:'auto',updated:Date.now()};
}
export function restoreConversation(value) {
  if(!value||typeof value.id!=='string'||!/^[a-f0-9-]{36}$/i.test(value.id))return newConversation();
  if(value.updated&&Date.now()-value.updated>90*60*1000)return newConversation();
  return {id:value.id,last_plan_id:typeof value.last_plan_id==='string'?value.last_plan_id.slice(0,40):'',last_place_id:typeof value.last_place_id==='string'?value.last_place_id.slice(0,40):'',inferred_goal:typeof value.inferred_goal==='string'?value.inferred_goal.slice(0,300):'',place:['auto','home','office','travelling','train','cafe','restaurant','shop','other'].includes(value.place)?value.place:'auto',goal:typeof value.goal==='string'?value.goal.slice(0,600):'',goal_source_id:typeof value.goal_source_id==='string'?value.goal_source_id:'',updated:Number(value.updated)||Date.now()};
}
const samePair=(a,b)=>a?.known_code===b?.known_code&&a?.learning_code===b?.learning_code;
export function contextForRecord(records,record) {
  const index=records.findIndex(r=>r.id===record.id);
  if(index<0||!record.conversation_id)return {user_goal:record.context_goal||'',conversation_summary:'',recent_turns:[]};
  const earlier=records.slice(0,index).filter(r=>r.conversation_id===record.conversation_id&&(!r.context_plan_id||r.context_plan_id===record.context_plan_id)&&(!r.context_place_id||r.context_place_id===record.context_place_id)&&samePair(r.pair,record.pair)&&(!record.profile_id||r.profile_id===record.profile_id)&&(!r.created||!record.created||record.created-r.created<=90*60*1000)&&!r.example&&typeof r.text==='string'&&r.text.trim());
  const summary=[...earlier].reverse().find(r=>typeof r.lesson?.context_summary==='string')?.lesson.context_summary||'';
  const last=[...earlier].reverse().find(r=>r.lesson?.replies?.length);
  const previous=last?{previous_reply_source:last.text.slice(0,400),previous_replies:last.lesson.replies.slice(0,3).map(r=>({text:r.words.map(w=>w.text).join('').slice(0,300),translation:r.translation.slice(0,300)}))}:{};
  return {...previous,...(record.inferred_goal?{inferred_user_goal:record.inferred_goal.slice(0,300)}:{}),...(record.speaker==='user'?{current_speaker_hint:'user'}:{}),user_goal:(record.context_goal||'').slice(0,600),conversation_summary:summary.slice(0,600),recent_turns:earlier.slice(-8).map(r=>({speaker:['user','likely_user','likely_other'].includes(r.speaker)?r.speaker:'unattributed',text:r.text.slice(0,400)}))};
}
export function latestContextSummary(records,conversationId) {
  return [...records].reverse().find(r=>r.conversation_id===conversationId&&typeof r.lesson?.context_summary==='string')?.lesson.context_summary||'';
}

export function matchesSuggestedReply(text,replies=[]){
  const normalize=value=>String(value).normalize('NFKC').toLocaleLowerCase().replace(/[^\p{L}\p{N}]/gu,'');
  const value=normalize(text);if(['thankyou','thanks','thankyouverymuch','yesplease','ありがとうございます','ありがとう','はいお願いします','お願いします','bonjour','hello','goodmorning','okay'].includes(value))return false;return value.length>=6&&replies.some(r=>normalize(r.text)===value);
}
