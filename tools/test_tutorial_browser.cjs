/* First-visit interaction, persistence and no paid/permission requests. */
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const ROOT=path.resolve(__dirname,'..'),ORIGIN='http://127.0.0.1:8094';let browser;const checks=[];
async function check(name,fn){await fn();checks.push({name,passed:true});console.log('PASS '+name);}
(async()=>{try{
 browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true}),page=await context.newPage(),errors=[],writes=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.method()==='POST'||r.url().startsWith('ws:'))writes.push(r.url());});
 await page.addInitScript(()=>{window.permissionRequests=0;navigator.mediaDevices.getUserMedia=()=>{window.permissionRequests++;throw Error('Unexpected microphone request');};navigator.geolocation.getCurrentPosition=()=>{window.permissionRequests++;};});
 await page.goto(ORIGIN);await page.locator('#tutorial-dialog').waitFor();
 await check('First visit opens an accessible tutorial with real language choices',async()=>{
  assert.equal(await page.locator('#tutorial-dialog').evaluate(n=>n.matches(':modal')),true);assert.equal(await page.locator('#tutorial-known option').count(),83);assert.equal(await page.locator('#tutorial-known').inputValue(),'en-US');assert.equal(await page.locator('#tutorial-learning').inputValue(),'ja-JP');await page.screenshot({path:path.join(ROOT,'validation/web-tutorial.png')});
 });
 await check('Language selection validates the pair and saves it into the app',async()=>{
  await page.locator('#tutorial-learning').selectOption('en-US');await page.locator('#tutorial-next').click();assert.equal(await page.locator('#tutorial-error').isVisible(),true);await page.locator('#tutorial-learning').selectOption('hi-IN');await page.locator('#tutorial-next').click();assert.equal(await page.locator('#tutorial-progress').textContent(),'2 of 3');assert.equal(await page.locator('#learning-language').inputValue(),'hi-IN');await page.waitForFunction(()=>JSON.parse(localStorage.getItem('lingolive-profile')).learning_code==='hi-IN');
 });
 await check('Word and transliteration tutorial is interactive with no model requests',async()=>{
  assert.equal(await page.locator('#tutorial-listen').isVisible(),true);await page.locator('#tutorial-next').click();await page.locator('#tutorial-word').click();assert.equal(await page.locator('#tutorial-meaning').isVisible(),true);await page.locator('#tutorial-pronunciation').click();assert.equal(await page.locator('#tutorial-word').textContent(),'dhanyavaadagalu');await page.locator('#tutorial-back').click();await page.locator('#tutorial-back').click();assert.equal(await page.locator('#tutorial-known').inputValue(),'en-US');await page.locator('#tutorial-next').click();await page.locator('#tutorial-next').click();assert.equal(await page.locator('#tutorial-progress').textContent(),'3 of 3');assert.equal(writes.length,0);assert.equal(await page.evaluate(()=>window.permissionRequests),0);
 });
 await check('Completion opens Connect without starting the microphone and is remembered on reload',async()=>{
  await page.locator('#tutorial-next').click();await page.locator('#connection-dialog').waitFor();assert.equal(writes.length,0);assert.equal(await page.evaluate(()=>window.permissionRequests),0);await page.locator('#connection-close').click();await page.reload();await page.locator('#connection-label').waitFor();await page.waitForFunction(()=>document.querySelector('#known-language').value==='en-US');assert.equal(await page.locator('#tutorial-dialog').isVisible(),false);assert.equal(await page.locator('#learning-language').inputValue(),'hi-IN');
 });
 await check('Tutorial can be replayed from settings and dismissed with Escape',async()=>{
  await page.locator('#settings-open').click();await page.locator('#tutorial-replay').click();await page.locator('#tutorial-dialog').waitFor();await page.keyboard.press('Escape');assert.equal(await page.locator('#tutorial-dialog').isVisible(),false);await page.locator('#settings-close').click();
 });
 await check('History starts collapsed and the main speaking button stays visible on mobile',async()=>{
  assert.equal(await page.locator('#recent-phrases').evaluate(n=>n.open),false);assert.equal(await page.locator('#transcripts').isVisible(),false);await page.locator('#recent-phrases summary').click();assert.equal(await page.locator('#transcripts').isVisible(),true);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));const dock=await page.locator('#listen-button').boundingBox();assert.ok(dock.y>=0&&dock.y+dock.height<=844);
 });
 await check('Skip on a fresh browser also persists and makes no paid call',async()=>{
  const fresh=await browser.newContext(),p=await fresh.newPage();await p.goto(ORIGIN);await p.locator('#tutorial-skip').click();assert.equal(await p.evaluate(()=>localStorage.getItem('lingolive-tutorial-v1')),'done');await p.reload();await p.waitForFunction(()=>document.querySelector('#known-language').value==='en-US');assert.equal(await p.locator('#tutorial-dialog').isVisible(),false);await fresh.close();
 });
 assert.deepEqual(errors,[]);assert.equal(writes.length,0);fs.writeFileSync(path.join(ROOT,'validation/web-tutorial-results.json'),JSON.stringify({passed:checks.length,checks,model_calls:0,errors},null,2)+'\n');
}catch(e){console.error(e);process.exitCode=1;}finally{await browser?.close();}})();
