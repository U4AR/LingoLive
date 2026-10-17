/* Real Chromium/cookies/AudioWorklet and local relay. Google responses are fixtures. */
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const ROOT=path.resolve(__dirname,'..'),ORIGIN='http://127.0.0.1:8098',KEY='test-browser-personal-google-key-12345',CODE='test-only-browser-access-code-32-characters';
const EXAMPLE=JSON.parse(fs.readFileSync(path.join(ROOT,'web/example.json')));let browser;const checks=[];
async function check(name,fn){await fn();checks.push({name,passed:true});console.log('PASS '+name);}
(async()=>{try{
 browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream']});
 const context=await browser.newContext({viewport:{width:390,height:844},permissions:['microphone']});const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const status=()=>page.request.get(ORIGIN+'/fixture/status').then(r=>r.json());
 const finish=()=>page.waitForFunction(()=>[...document.querySelectorAll('.transcript .phrase-meta')].every(n=>/Lesson saved|Not the learning language/.test(n.textContent)));
 const type=async()=>{const count=Number(await page.locator('#saved-count').textContent());await page.locator('#type-details').evaluate(n=>n.open=true);await page.locator('#phrase-input').fill(EXAMPLE.text);await page.getByRole('button',{name:'Teach me this phrase'}).click();await page.waitForFunction(n=>document.querySelector('#saved-count').textContent===String(n),count+1);await finish();};
 await page.goto(ORIGIN);await page.waitForFunction(()=>document.querySelector('#known-language').value==='en-US');await page.locator('#tutorial-skip').click();
 await check('Connect offers private code and a personal Google key with clear billing and retention',async()=>{
  await page.locator('#connection-open').click();await page.getByText('Your host can share the access code.',{exact:true}).waitFor();assert.equal(await page.locator('#method-code').isChecked(),true);
  await page.locator('#method-key').check();assert.equal(await page.locator('#key-fields').isVisible(),true);assert.equal(await page.locator('#code-fields').isVisible(),false);assert.match(await page.locator('#key-fields').textContent(),/Google bills your key/);
  await page.screenshot({path:path.join(ROOT,'validation/web-personal-key.png')});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 });
 await check('Switching methods and closing clears entered credentials',async()=>{
  await page.locator('#personal-api-key').fill(KEY);await page.locator('#method-code').check();assert.equal(await page.locator('#personal-api-key').inputValue(),'');
  await page.locator('#access-code').fill(CODE);await page.locator('#method-key').check();assert.equal(await page.locator('#access-code').inputValue(),'');
  await page.locator('#personal-api-key').fill(KEY);await page.locator('#connection-close').click();assert.equal(await page.locator('#personal-api-key').inputValue(),'');await page.locator('#connection-open').click();await page.locator('#method-key').check();
 });
 await check('Personal key creates only an opaque HttpOnly session and clears the key field',async()=>{
  await page.locator('#personal-api-key').fill(KEY);await page.locator('#connect-submit').click();await page.locator('#connection-dialog').waitFor({state:'hidden'});assert.equal(await page.locator('#personal-api-key').inputValue(),'');
  const session=await page.request.get(ORIGIN+'/v1/session').then(r=>r.json());assert.equal(session.mode,'api_key');const cookies=await context.cookies();assert.ok(cookies.some(c=>c.name==='lingolive_session'&&c.httpOnly));assert.ok(cookies.every(c=>!c.value.includes(KEY)));
 });
 await check('Lessons use the personal provider and never save keys with memory',async()=>{
  await type();const data=await status();assert.equal(data.requests.length,0);assert.equal(data.personal.at(-1).requests.length,1);assert.equal(await page.locator('.reply').count(),3);
  const stored=await page.evaluate(async()=>{
   const memory=await new Promise((resolve,reject)=>{const r=indexedDB.open('lingolive-learning');r.onsuccess=()=>{const q=r.result.transaction('phrases').objectStore('phrases').getAll();q.onsuccess=()=>resolve(q.result);q.onerror=reject;};r.onerror=reject;});
   return JSON.stringify({local:{...localStorage},session:{...sessionStorage},memory});
  });assert.ok(!stored.includes(KEY));assert.ok(!JSON.stringify(data).includes(KEY));
 });
 await check('Reload retains key-session access without storing or asking for the key again',async()=>{
  await page.reload();await page.getByText('Connected',{exact:true}).waitFor();await page.locator('#connection-open').click();await page.getByText('Connected using your Google API key.',{exact:true}).waitFor();assert.equal(await page.locator('#method-key').isChecked(),true);assert.equal(await page.locator('#personal-api-key').inputValue(),'');await page.locator('#connection-close').click();
 });
 await check('Browser microphone audio, transcription and lessons use only the personal provider',async()=>{
  await page.locator('#listen-button').click();await page.getByText('Listening · all languages',{exact:true}).waitFor();await page.waitForFunction(()=>document.querySelectorAll('.transcript').length>=2);await finish();await page.locator('#listen-button').click();await page.waitForFunction(()=>document.querySelectorAll('.transcript').length>=3);await finish();
  const data=await status();assert.equal(data.frames,0);assert.equal(data.requests.length,0);assert.ok(data.personal.at(-1).frames>=5);assert.ok(data.personal.at(-1).bytes>=16000);assert.equal(data.personal.at(-1).setups[0].setup.model,'models/gemini-3.5-transcribe-live');
 });
 await check('Switching to host code uses host quota while preserving saved lessons',async()=>{
  const saved=Number(await page.locator('#saved-count').textContent());await page.locator('#connection-open').click();await page.locator('#method-code').check();await page.locator('#access-code').fill(CODE);await page.locator('#connect-submit').click();await page.locator('#connection-dialog').waitFor({state:'hidden'});
  assert.equal((await page.request.get(ORIGIN+'/v1/session').then(r=>r.json())).mode,'access_code');await type();const data=await status();assert.equal(data.requests.length,1);assert.equal(await page.locator('#saved-count').textContent(),String(saved+1));
 });
 await check('Disconnect removes live access and retains local saved learning',async()=>{
  const count=await page.locator('#saved-count').textContent();await page.locator('#connection-open').click();await page.locator('#disconnect').click();assert.equal(await page.request.get(ORIGIN+'/v1/session').then(r=>r.status()),401);assert.equal(await page.locator('#saved-count').textContent(),count);
 });
 assert.deepEqual(errors,[]);fs.writeFileSync(path.join(ROOT,'validation/web-byok-browser-results.json'),JSON.stringify({passed:checks.length,checks,google_mocked:true,synthetic_browser_audio:true,errors},null,2)+'\n');
}catch(e){console.error(e);process.exitCode=1;}finally{await browser?.close();}})();
