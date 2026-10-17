/* Local browser fixture verifies context transport/persistence; Google is mocked. */
const {chromium}=require('playwright');const assert=require('node:assert/strict');
const fs=require('node:fs');const path=require('node:path');
const ROOT=path.resolve(__dirname,'..'),ORIGIN='http://127.0.0.1:8096';
const EXAMPLE=JSON.parse(fs.readFileSync(path.join(ROOT,'web/example.json'),'utf8'));
const results=[];let browser;
async function check(name,fn){await fn();results.push({name,passed:true});console.log('PASS '+name);}
(async()=>{try{
 browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 const context=await browser.newContext({viewport:{width:390,height:844}});const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 let requestOffset=0;
 const requests=()=>page.request.get(ORIGIN+'/fixture/status').then(r=>r.json()).then(x=>x.requests.slice(requestOffset));
 const settings=()=>page.locator('#context-settings').evaluate(n=>n.open=true);
 const setGoal=async text=>{await settings();await page.locator('#conversation-goal').fill(text);await page.getByRole('button',{name:'Save goal',exact:true}).click();};
 const type=async text=>{const count=Number(await page.locator('#saved-count').textContent());await page.locator('#type-details').evaluate(n=>n.open=true);await page.locator('#phrase-input').fill(text);await page.locator('#phrase-form button[type=submit]').click();await page.waitForFunction(n=>document.querySelector('#saved-count').textContent===String(n),count+1);};
 const finished=()=>page.waitForFunction(()=>[...document.querySelectorAll('.transcript .phrase-meta')].every(n=>/Lesson saved|Not the learning language/.test(n.textContent)));
 await page.goto(ORIGIN);await page.waitForFunction(()=>document.querySelector('#known-language').value==='en-US');await page.locator('#tutorial-skip').click();await page.locator('#connection-open').click();await page.locator('#access-code').fill('test-only-browser-access-code-32-characters');await page.locator('#connect-submit').click();await page.locator('#connection-dialog').waitFor({state:'hidden'});requestOffset=(await requests()).length;
 await check('Saving an explicit goal makes no model request',async()=>{
  await setGoal('I want vegetarian takeaway.');assert.equal((await requests()).length,0);assert.match(await page.locator('#goal-summary').textContent(),/vegetarian takeaway/);
 });
 await check('The current goal reaches a lesson without modifying the source words',async()=>{
  await type(EXAMPLE.text);await finished();const values=await requests();assert.equal(values[0].user_goal,'I want vegetarian takeaway.');assert.deepEqual(values[0].recent_turns,[]);
  assert.equal(await page.locator('.source-words').textContent(),EXAMPLE.text);assert.match(await page.locator('.reply-goal').textContent(),/vegetarian takeaway/);
 });
 const spokenGoal='I want vegetarian takeaway before my train.';
 await check('A spoken or typed phrase becomes user intent only when explicitly selected',async()=>{
  await type(spokenGoal);await finished();let values=await requests();assert.equal(values[1].recent_turns[0].speaker,'unattributed');
  await page.locator('.reply-context-tools').evaluate(n=>n.open=true);await page.getByRole('button',{name:'Use these words as my goal',exact:true}).click();assert.equal(await page.locator('#conversation-goal').inputValue(),spokenGoal);
  await type(EXAMPLE.text);await finished();values=await requests();assert.equal(values[2].user_goal,spokenGoal);assert.equal(values[2].recent_turns[1].speaker,'user');assert.equal(values[2].recent_turns[1].text,spokenGoal);assert.match(values[2].conversation_summary,/cafe conversation/);
 });
 await check('Reload remembers the goal and earlier context on this browser',async()=>{
  await page.reload();await page.getByText('Connected',{exact:true}).waitFor();assert.equal(await page.locator('#conversation-goal').inputValue(),spokenGoal);
  await type(EXAMPLE.text);await finished();const values=await requests();assert.equal(values[3].user_goal,spokenGoal);assert.equal(values[3].recent_turns.length,3);
 });
 await check('Changing the goal and refreshing replies uses the new intent',async()=>{
  await setGoal('I want to eat here instead.');assert.equal((await requests()).length,4);
  await page.locator('.reply-context-tools').evaluate(n=>n.open=true);await page.getByRole('button',{name:'Update replies for my goal',exact:true}).click();await finished();const values=await requests();assert.equal(values.length,5);assert.equal(values[4].user_goal,'I want to eat here instead.');assert.equal(values[4].text,EXAMPLE.text);
  await page.screenshot({path:path.join(ROOT,'validation/web-context.png'),fullPage:true});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 });
 await check('New conversation clears intent/history sent to Google while retaining Saved',async()=>{
  await settings();await page.getByRole('button',{name:'New conversation',exact:true}).click();assert.equal(await page.locator('#conversation-goal').inputValue(),'');assert.equal(await page.locator('#saved-count').textContent(),'4');
  await type(EXAMPLE.text);await finished();const values=await requests();assert.equal(values[5].user_goal,'');assert.deepEqual(values[5].recent_turns,[]);assert.equal(values[5].conversation_summary,'');
 });
 await check('Deleting a goal-source phrase clears its stored intent',async()=>{
  await page.locator('.reply-context-tools').evaluate(n=>n.open=true);await page.getByRole('button',{name:'Use these words as my goal',exact:true}).click();const id=await page.locator('.transcript').last().getAttribute('data-record');
  await page.locator('#saved-tab').click();await page.locator('.saved-card[data-record="'+id+'"]').getByRole('button',{name:/Remove saved phrase/}).click();
  await page.waitForFunction(()=>document.querySelector('#conversation-goal').value==='');assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('lingolive-conversation')).goal),'');
 });
 await check('Late audio finals retain their original conversation and latest goal',async()=>{
  const received=await page.evaluate(async()=>{
   const {LiveMicrophone}=await import('/assets/microphone.js');const original=window.WebSocket;let socket;const events=[];
   class FixtureSocket{static OPEN=1;constructor(){socket=this;this.readyState=1;queueMicrotask(()=>this.onopen?.());}send(text){if(JSON.parse(text).setup)queueMicrotask(()=>this.onmessage?.({data:JSON.stringify({setupComplete:{}})}));}close(){this.readyState=3;}}
   window.WebSocket=FixtureSocket;
   const microphone=new LiveMicrophone({status(){},final:(text,pair,conversation)=>events.push({text,conversation:{...conversation}}),interim(){},error(){}});
   try{
    microphone.running=true;microphone.generation=1;microphone.pair={known_code:'en-US',learning_code:'ja-JP'};
    const old={id:'old-conversation',goal:'Original goal'};microphone.conversationSnapshot=old;await microphone.connect(1);
    old.goal='Goal edited during listening';microphone.conversationSnapshot={id:'new-conversation',goal:'Another goal'};
    socket.onmessage({data:JSON.stringify({serverContent:{inputTranscription:{text:'Late final words'}}})});return events;
   }finally{microphone.running=false;clearTimeout(microphone.renewTimer);socket?.close();window.WebSocket=original;}
  });
  assert.equal(received[0].conversation.id,'old-conversation');assert.equal(received[0].conversation.goal,'Goal edited during listening');
 });
 assert.deepEqual(errors,[]);fs.writeFileSync(path.join(ROOT,'validation/web-context-browser-results.json'),JSON.stringify({passed:results.length,checks:results,google_mocked:true},null,2)+'\n');console.log('All '+results.length+' context browser checks passed.');
}catch(error){console.error(error);process.exitCode=1;}finally{await browser?.close();}})();
