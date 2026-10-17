/* Local Google UI fixture: mock SDK, real RSA validation and real browser cookies. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');const path=require('node:path');
const ROOT=path.resolve(__dirname,'..'),ORIGIN='http://127.0.0.1:8095';
const CODE='test-only-browser-access-code-32-characters';
const results=[];let browser;
async function check(name,fn){await fn();results.push({name,passed:true});console.log('PASS '+name);}
const sdk=`window.google={accounts:{id:{initialize(config){this.config=config},renderButton(target){const button=document.createElement('button');button.type='button';button.textContent='Sign in with Google';button.onclick=async()=>{const params=new URLSearchParams({nonce:this.config.nonce,email:window.fixtureEmail||'ashish.t.vasant@gmail.com'});const value=await fetch('/fixture/google-credential?'+params).then(r=>r.json());this.config.callback(value)};target.append(button)},disableAutoSelect(){}}}};`;
(async()=>{try{
 browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 const context=await browser.newContext({viewport:{width:390,height:844}});
 await context.route('https://accounts.google.com/gsi/client',route=>route.fulfill({contentType:'application/javascript',body:sdk}));
 const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(ORIGIN);await page.waitForFunction(()=>document.querySelector('#known-language').value==='en-US');
 await check('Google is required before connecting with the private code',async()=>{
  await page.locator('#connection-open').click();await page.getByRole('button',{name:'Sign in with Google',exact:true}).waitFor();
  assert.equal(await page.locator('#connect-submit').isDisabled(),true);
  await page.locator('#access-code').fill(CODE);
  assert.equal(await page.locator('#connect-submit').isDisabled(),true);
 });
 await check('Uninvited Google account is rejected without an AI call',async()=>{
  await page.evaluate(()=>window.fixtureEmail='uninvited@example.com');await page.getByRole('button',{name:'Sign in with Google',exact:true}).click();
  await page.locator('#connect-submit').click();await page.getByText('This Google account has not been invited. Ask the host for access.',{exact:true}).waitFor();
  assert.equal(await page.locator('#connection-label').textContent(),'Connect');
  const status=await page.request.get(ORIGIN+'/fixture/status').then(r=>r.json());assert.equal(status.requests,0);
 });
 await check('Invited Google account and private code create a secure session and lesson',async()=>{
  await page.evaluate(()=>window.fixtureEmail='ashish.t.vasant@gmail.com');await page.getByRole('button',{name:'Sign in with Google',exact:true}).click();
  await page.locator('#connect-submit').click();await page.locator('#connection-dialog').waitFor({state:'hidden'});
  assert.equal(await page.locator('#connection-label').textContent(),'Connected');
  const cookie=(await context.cookies()).find(c=>c.name==='lingolive_session');assert.ok(cookie.httpOnly);assert.equal(cookie.value.split('.').length,4);
  await page.locator('#type-details').evaluate(n=>n.open=true);await page.locator('#phrase-input').fill('コーヒーはいかがですか？');await page.getByRole('button',{name:'Teach me this phrase'}).click();
  await page.locator('#lesson-panel .translation').waitFor();assert.equal(await page.locator('#saved-count').textContent(),'1');
 });
 await check('Reload preserves sign-in and stores no Google credential or access code',async()=>{
  await page.reload();await page.getByText('Connected',{exact:true}).waitFor();
  const storage=await page.evaluate(()=>JSON.stringify([localStorage,sessionStorage]));assert.ok(!storage.includes(CODE));assert.ok(!storage.includes('fixture-google-user'));
  assert.equal(await page.locator('#saved-count').textContent(),'1');
  const cacheUrls=await page.evaluate(async()=>{const all=[];for(const name of await caches.keys()){for(const request of await (await caches.open(name)).keys())all.push(request.url)}return all;});
  assert.ok(!cacheUrls.some(url=>url.includes('/v1/')||url.startsWith('https://accounts.google.com')));
 });
 await check('Sign-out requires Google selection again and retains local lessons',async()=>{
  await page.locator('#connection-open').click();await page.getByRole('button',{name:'Sign in with Google',exact:true}).waitFor();
  assert.equal(await page.locator('#connect-submit').isDisabled(),true);await page.locator('#disconnect').click();
  await page.locator('#connection-dialog').waitFor({state:'hidden'});assert.equal(await page.locator('#connection-label').textContent(),'Connect');
  assert.equal(await page.locator('#saved-count').textContent(),'1');assert.equal((await page.request.get(ORIGIN+'/v1/session')).status(),401);
 });
 assert.deepEqual(errors,[]);const report={passed:results.length,checks:results,real_google_login:false,local_rsa_token_verification:true};
 fs.writeFileSync(path.join(ROOT,'validation/web-google-signin-browser-results.json'),JSON.stringify(report,null,2)+'\n');console.log('All '+results.length+' Google sign-in browser fixture checks passed.');
}catch(error){console.error(error);process.exitCode=1;}finally{await browser?.close();}})();
