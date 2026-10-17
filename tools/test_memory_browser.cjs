/* Real local browser: isolated learner stores and optional sensor transport. Google mocked. */
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const ROOT=path.resolve(__dirname,'..'),ORIGIN='http://127.0.0.1:8097';const EXAMPLE=JSON.parse(fs.readFileSync(path.join(ROOT,'web/example.json'),'utf8'));
let browser,page;const results=[];async function check(name,fn){await fn();results.push({name,passed:true});console.log('PASS '+name);}
(async()=>{try{
 browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream']});
 const context=await browser.newContext({viewport:{width:390,height:844},permissions:['microphone','geolocation'],geolocation:{latitude:12.971598,longitude:77.594566,accuracy:8}});page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 let offset=0;const requests=()=>page.request.get(ORIGIN+'/fixture/status').then(r=>r.json()).then(x=>x.requests.slice(offset));
 const done=()=>page.waitForFunction(()=>[...document.querySelectorAll('.transcript .phrase-meta')].every(n=>/Lesson saved|Not the learning language|You said this|Transcript saved/.test(n.textContent)));
 const type=async(text=EXAMPLE.text)=>{const n=Number(await page.locator('#saved-count').textContent());await page.locator('#type-details').evaluate(n=>n.open=true);await page.locator('#phrase-input').fill(text);await page.getByRole('button',{name:'Teach me this phrase'}).click();await page.waitForFunction(n=>document.querySelector('#saved-count').textContent===String(n),n+1);await done();};
 const notes=async value=>{await page.locator('#context-settings').evaluate(n=>n.open=true);await page.locator('#memory-notes').fill(value);await page.locator('#save-memory').click();};
 await page.goto(ORIGIN);await page.waitForFunction(()=>document.querySelector('#known-language').value==='en-US');await page.locator('#connection-open').click();await page.locator('#access-code').fill('test-only-browser-access-code-32-characters');await page.locator('#connect-submit').click();await page.locator('#connection-dialog').waitFor({state:'hidden'});offset=(await requests()).length;
 const first=await page.locator('#learner-profile').inputValue();let second;
 await check('No goal is required; learner notes guide the same lesson request',async()=>{
  await notes('I am a beginner travelling by train.');assert.equal((await requests()).length,0);await type();const data=(await requests())[0];assert.equal(data.user_goal,'');assert.equal(data.memory_notes,'I am a beginner travelling by train.');assert.equal(await page.locator('.reply').count(),3);
 });
 await check('Earlier suggestions and previously seen words are included without pretending they were spoken',async()=>{
  await type();const data=(await requests())[1];assert.equal(data.previous_replies.length,3);assert.ok(data.previously_seen_words.length>0);assert.equal(data.recent_turns[0].speaker,'unattributed');assert.equal(data.previous_reply_source,EXAMPLE.text);
 });
 await check('I said this records a confirmed user turn without another model call',async()=>{
  const count=(await requests()).length;await page.locator('.reply-more').first().evaluate(n=>n.open=true);await page.getByRole('button',{name:'I said this',exact:true}).first().click();await page.waitForFunction(()=>document.querySelector('#saved-count').textContent==='3');assert.equal((await requests()).length,count);
  await type();const data=(await requests()).at(-1);assert.equal(data.recent_turns.at(-1).speaker,'user');assert.notEqual(data.recent_turns.at(-1).text,EXAMPLE.text);
 });
 await check('A new learner starts with isolated notes, history and conversation',async()=>{
  await page.locator('#learner-name').fill('Office learner');await page.locator('#add-learner').click();await page.waitForFunction(()=>document.querySelector('#saved-count').textContent==='0');second=await page.locator('#learner-profile').inputValue();assert.notEqual(second,first);assert.equal(await page.locator('#memory-notes').inputValue(),'');
  await notes('Use short office conversations.');await page.locator('#context-setting').selectOption('office');await type();const data=(await requests()).at(-1);assert.equal(data.memory_notes,'Use short office conversations.');assert.equal(data.setting,'office');assert.deepEqual(data.recent_turns,[]);assert.deepEqual(data.previous_replies,[]);assert.deepEqual(data.previously_seen_words,[]);
 });
 await check('Switching back restores only the first learner memory',async()=>{
  await page.locator('#learner-profile').selectOption(first);await page.waitForFunction(()=>document.querySelector('#saved-count').textContent==='4');assert.equal(await page.locator('#memory-notes').inputValue(),'I am a beginner travelling by train.');assert.equal(await page.locator('#context-setting').inputValue(),'auto');
 });
 await check('Location is opt-in, coarse and not written into saved lessons',async()=>{
  assert.equal(await page.locator('#use-location').isChecked(),false);await page.locator('#use-location').check();await page.getByText('Approximate location is on',{exact:true}).waitFor();await type();const data=(await requests()).at(-1);assert.equal(data.location_context.latitude,12.97);assert.equal(data.location_context.longitude,77.59);assert.ok(data.location_context.accuracy_m>=1000);assert.match(await page.locator('#open-map').getAttribute('href'),/12.97,77.59/);
  const rows=await page.evaluate(()=>new Promise((resolve,reject)=>{const r=indexedDB.open('lingolive-learning');r.onsuccess=()=>{const q=r.result.transaction('phrases').objectStore('phrases').getAll();q.onsuccess=()=>resolve(q.result);q.onerror=reject;};r.onerror=reject;}));assert.ok(rows.every(r=>!r.context_location&&!r.lesson_context?.location_context));
 });
 await check('Switching learner stops sensor sharing and restores the other learner independently',async()=>{
  await page.locator('#learner-profile').selectOption(second);await page.waitForFunction(()=>document.querySelector('#saved-count').textContent==='1');assert.equal(await page.locator('#use-location').isChecked(),false);assert.equal(await page.locator('#use-audio-context').isChecked(),false);await type();const data=(await requests()).at(-1);assert.equal(data.location_context,null);assert.equal(data.memory_notes,'Use short office conversations.');
 });
 await check('Optional real AudioWorklet samples reach the lesson but never the history',async()=>{
  await page.locator('#use-audio-context').check();const count=(await requests()).length;await page.locator('#listen-button').click();await page.getByText('Listening · all languages',{exact:true}).waitFor();await page.waitForFunction(()=>document.querySelectorAll('.transcript').length>=3);await done();await page.locator('#listen-button').click();
  const sent=(await requests()).slice(count).find(r=>r.audio_context);assert.ok(sent);const raw=Buffer.from(sent.audio_context.data,'base64');assert.equal(raw.toString('ascii',0,4),'RIFF');assert.ok(raw.length<=128044);
  const saved=await page.evaluate(()=>new Promise((resolve,reject)=>{const profiles=JSON.parse(localStorage.getItem('lingolive-learners')),p=profiles.profiles.find(p=>p.id===profiles.active);const r=indexedDB.open('lingolive-learning:'+p.namespace);r.onsuccess=()=>{const q=r.result.transaction('phrases').objectStore('phrases').getAll();q.onsuccess=()=>resolve(q.result);q.onerror=reject;};r.onerror=reject;}));assert.ok(saved.every(r=>!r.audio_context&&!r.lesson_context?.audio_context));await page.locator('#use-audio-context').uncheck();
 });
 await check('Learner memory survives reload without mixing profiles',async()=>{
  await page.reload();await page.getByText('Connected',{exact:true}).waitFor();assert.equal(await page.locator('#learner-profile').inputValue(),second);assert.equal(await page.locator('#memory-notes').inputValue(),'Use short office conversations.');assert.equal(await page.locator('#use-audio-context').isChecked(),false);assert.equal(await page.locator('#use-location').isChecked(),false);
 });
 await check('Deleting a phrase during a lesson request does not recreate it on completion',async()=>{
  let release,started;const gate=new Promise(resolve=>release=resolve),arrived=new Promise(resolve=>started=resolve);
  await page.route('**/v1/teach',async route=>{started();await gate;await route.continue();});
  const before=Number(await page.locator('#saved-count').textContent());await page.locator('#type-details').evaluate(n=>n.open=true);await page.locator('#phrase-input').fill(EXAMPLE.text);await page.getByRole('button',{name:'Teach me this phrase'}).click();await arrived;
  await page.waitForFunction(n=>document.querySelector('#saved-count').textContent===String(n),before+1);const id=await page.locator('.transcript').last().getAttribute('data-record');await page.locator('#saved-tab').click();await page.locator('.saved-card[data-record="'+id+'"]').getByRole('button',{name:/Remove saved phrase/}).click();await page.waitForFunction(n=>document.querySelector('#saved-count').textContent===String(n),before);
  const response=page.waitForResponse(r=>r.url().endsWith('/v1/teach'));release();await (await response).finished();await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));await page.unroute('**/v1/teach');
  await page.reload();await page.getByText('Connected',{exact:true}).waitFor();await page.locator('#saved-tab').click();assert.equal(await page.locator('.saved-card[data-record="'+id+'"]').count(),0);
 });
 await check('A distinctive spoken suggestion is automatically marked as likely learner speech',async()=>{
  await page.locator('#conversation-tab').click();await type();const chosen=EXAMPLE.lesson.replies[1].words.map(w=>w.text).join('');await type(chosen);
  await page.locator('.transcript').last().getByText(/Likely you/).waitFor();await type();const data=(await requests()).at(-1);assert.equal(data.recent_turns.find(t=>t.text===chosen).speaker,'likely_user');assert.equal(data.user_goal,'');
 });
 await check('Model-inferred learner intent is remembered without requiring a goal',async()=>{
  await type('I want to catch my train.');await page.waitForFunction(()=>document.querySelector('#goal-summary').textContent.includes('Likely goal: Get to the train station.'));await type();const data=(await requests()).at(-1);assert.equal(data.user_goal,'');assert.equal(data.inferred_user_goal,'Get to the train station.');assert.equal(data.recent_turns.at(-1).speaker,'likely_user');
 });
 assert.deepEqual(errors,[]);fs.writeFileSync(path.join(ROOT,'validation/web-memory-browser-results.json'),JSON.stringify({passed:results.length,checks:results,google_mocked:true,geolocation_fixture:true,synthetic_browser_audio:true},null,2)+'\n');console.log('All '+results.length+' learner-memory browser checks passed.');
}catch(error){console.error(error);console.error(await page?.locator('.transcript .phrase-meta').allTextContents());console.error(await page?.locator('#lesson-panel').textContent());process.exitCode=1;}finally{await browser?.close();}})();
