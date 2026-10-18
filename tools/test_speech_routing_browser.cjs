/* Real browser/microphone/relay flow; Google outputs are explicit test fixtures. */
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs');
const BASE='http://127.0.0.1:8099',example=require('../web/example.json'),checks=[];
async function check(name,fn){await fn();checks.push({name,passed:true});console.log('PASS '+name);}
(async()=>{let browser;try{
 browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream']});
 const context=await browser.newContext({viewport:{width:390,height:844},permissions:['microphone']}),page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const count=()=>page.request.get(BASE+'/fixture/status').then(r=>r.json()).then(x=>x.requests.length);
 const send=text=>page.request.post(BASE+'/fixture/final',{data:{text}});
 await page.goto(BASE);await page.locator('#tutorial-skip').click();await page.locator('#connection-open').click();await page.locator('#access-code').fill('test-only-browser-access-code-32-characters');await page.locator('#connect-submit').click();await page.locator('#connection-dialog').waitFor({state:'hidden'});
 await page.locator('#listen-button').click();await page.locator('#lesson-panel .reply').nth(2).waitFor();const initial=await count(),long=example.lesson.replies[1].words.map(w=>w.text).join(''),short=example.lesson.replies[0].words.map(w=>w.text).join('');
 await check('A spoken option is saved as learner speech with no new model call or reply loop',async()=>{
  await send(long);await page.waitForFunction(()=>[...document.querySelectorAll('.transcript')].some(n=>n.textContent.includes('Your words · waiting')));assert.equal(await count(),initial);assert.equal(await page.locator('#lesson-panel .reply').count(),3);assert.equal(await page.locator('#lesson-panel .heard-text').textContent(),example.text);
 });
 await check('Repeating a displayed pronunciation also avoids a new request',async()=>{
  await send(example.lesson.replies[1].words.filter(w=>w.is_word).map(w=>w.reading).join(' '));await page.waitForFunction(()=>document.querySelectorAll('.transcript').length===3);assert.equal(await count(),initial);
 });
 await check('A short ambiguous reply asks who spoke before spending a model request',async()=>{
  await send(short);await page.locator('#lesson-panel .heard-label').filter({hasText:'Who said this?'}).waitFor();assert.equal(await count(),initial);await page.getByRole('button',{name:'I said this',exact:true}).click();assert.equal(await count(),initial);await page.getByText('Waiting for the other person. Your words stay in the conversation context.',{exact:true}).waitFor();
 });
 await check('The next other-person utterance gets replies and includes the learner turn as context',async()=>{
  await send(example.text);await page.locator('#lesson-panel .reply').nth(2).waitFor();assert.equal(await count(),initial+1);const status=await page.request.get(BASE+'/fixture/status').then(r=>r.json()),turns=status.requests.at(-1).recent_turns;assert.ok(turns.some(t=>t.text===long&&t.speaker==='likely_user'));assert.ok(turns.some(t=>t.text===short&&t.speaker==='user'));
 });
 await check('A suppressed turn can be corrected to the other speaker with one action',async()=>{
  await send(long);await page.waitForFunction(()=>document.querySelectorAll('.transcript').length===6);await page.locator('#transcripts').evaluate(n=>n.closest('details').open=true);await page.locator('.transcript').last().click();await page.getByRole('button',{name:'Other person said this',exact:true}).click();await page.waitForFunction(async expected=>(await (await fetch('/fixture/status')).json()).requests.length===expected,initial+2);assert.equal(await count(),initial+2);
 });
 await check('Explicit Help me say this still translates learner intent',async()=>{
  await page.locator('#type-details').evaluate(n=>n.open=true);await page.locator('#phrase-input').fill('Please stop for tea first.');await page.locator('#phrase-is-mine').check();await page.locator('#phrase-form button').click();await page.getByRole('heading',{name:'Say it in Japanese',exact:true}).waitFor();assert.equal(await count(),initial+3);
 });
 await check('Speaker features and raw PCM never enter local saved records or lesson payloads',async()=>{
  const result=await page.evaluate(async()=>{const {Memory}=await import('/assets/memory.js');const store=await new Memory('lingolive-learning').open();return store.all();});assert.ok(result.some(r=>r.status==='spoken'));assert.ok(result.every(r=>!['voice','vector','pitch','pcm'].some(k=>k in r)));const status=await page.request.get(BASE+'/fixture/status').then(r=>r.json());assert.ok(status.requests.every(r=>!['voice','vector','pitch','pcm'].some(k=>k in r)));
 });
 assert.deepEqual(errors,[]);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));fs.writeFileSync('validation/web-speech-routing-browser-results.json',JSON.stringify({passed:checks.length,checks,google_mocked:true,microphone:'Chromium synthetic PCM through real AudioWorklet and relay',physical_speaker_identification_tested:false,page_errors:errors},null,2)+'\n');
 }catch(e){console.error(e);process.exitCode=1;}finally{await browser?.close();}})();
