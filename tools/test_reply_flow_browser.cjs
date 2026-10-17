/* Real Chromium and local relay; Google responses are explicit fixtures. */
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const ROOT=path.resolve(__dirname,'..'),BASE='http://127.0.0.1:8099';
const EXAMPLE=JSON.parse(fs.readFileSync(path.join(ROOT,'web/example.json'))),KANNADA=JSON.parse(fs.readFileSync(path.join(ROOT,'web/example-kn.json')));
let browser;const checks=[];async function check(name,fn){await fn();checks.push({name,passed:true});console.log('PASS '+name);}
(async()=>{try{
 browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true,permissions:['clipboard-read','clipboard-write']}),page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const calls=()=>page.request.get(BASE+'/fixture/status').then(r=>r.json()).then(r=>r.requests.length);
 await page.goto(BASE);await page.locator('#tutorial-skip').click();await page.locator('#connection-open').click();await page.locator('#access-code').fill('test-only-browser-access-code-32-characters');await page.locator('#connect-submit').click();await page.locator('#connection-dialog').waitFor({state:'hidden'});
 const startingCalls=await calls();
 await page.locator('#type-details').evaluate(n=>n.open=true);await page.locator('#phrase-input').fill(EXAMPLE.text);await page.locator('#phrase-form button').click();await page.locator('#lesson-panel .reply').nth(2).waitFor();
 await check('Live conversation prioritizes three replies and has no word-meaning controls or teaching explanation',async()=>{
  assert.equal(await page.locator('#lesson-panel .source-words').textContent(),EXAMPLE.text);assert.equal(await page.locator('#lesson-panel .translation').textContent(),EXAMPLE.lesson.translation);
  assert.equal(await page.getByRole('heading',{name:'You could say',exact:true}).isVisible(),true);assert.equal(await page.locator('#lesson-panel .reply').count(),3);assert.equal(await page.locator('#lesson-panel .word').count(),0);assert.equal(await page.locator('#lesson-panel .phrase-explanation').count(),0);assert.equal(await calls(),startingCalls+1);
  await page.screenshot({path:path.join(ROOT,'validation/web-replies-live.png'),fullPage:true});
 });
 await check('Reply pronunciation leaves heard text unchanged; copying preserves original wording without another model call',async()=>{
  await page.getByRole('button',{name:'Pronunciation',exact:true}).click();assert.equal(await page.locator('#lesson-panel .source-words').textContent(),EXAMPLE.text);assert.match(await page.locator('#lesson-panel .reply-words').first().textContent(),/hai/);
  await page.getByRole('button',{name:/Copy reply:/}).first().click();assert.equal(await page.evaluate(()=>navigator.clipboard.readText()),EXAMPLE.lesson.replies[0].words.map(w=>w.text).join(''));assert.equal(await calls(),startingCalls+1);
 });
 await check('Learn later opens a saved review with word meanings, independent pronunciation and no paid request',async()=>{
  await page.getByRole('button',{name:'Learn later in Saved',exact:true}).click();assert.equal(await page.locator('#saved-tab').getAttribute('aria-current'),'page');assert.equal(await page.locator('#listen-dock').isVisible(),false);assert.equal(await page.locator('#lesson-panel').isVisible(),false);
  assert.equal(await page.locator('#review-panel .source-words').textContent(),EXAMPLE.text);await page.locator('#review-panel .source-words .word').first().click();assert.equal(await page.locator('#word-meaning').textContent(),'coffee');await page.locator('#word-close').click();
  await page.getByRole('button',{name:'Pronunciation',exact:true}).click();assert.match(await page.locator('#review-panel .source-words').textContent(),/kōhī/);await page.locator('#review-panel .reply .word').first().click();assert.ok((await page.locator('#word-meaning').textContent()).length);await page.locator('#word-close').click();assert.equal(await calls(),startingCalls+1);
  await page.screenshot({path:path.join(ROOT,'validation/web-replies-review.png'),fullPage:true});
 });
 await check('Returning to Conversation restores replies without retaining study controls or losing its reading choice',async()=>{
  await page.locator('#conversation-tab').click();assert.equal(await page.locator('#review-panel .word').count(),0);assert.equal(await page.locator('#lesson-panel .word').count(),0);assert.match(await page.locator('#lesson-panel .reply-words').first().textContent(),/hai/);assert.equal(await page.locator('#listen-dock').isVisible(),true);assert.equal(await calls(),startingCalls+1);await page.locator('#settings-open').click();await page.locator('#saved-tab').click();await page.locator('.open-saved').click();await page.locator('#settings-open').click();assert.equal(await page.locator('#context-settings').isVisible(),true);await page.locator('#settings-close').click();
 });
 await check('Saved reviews survive reload/offline and deletion removes the learning record',async()=>{
  await page.evaluate(()=>navigator.serviceWorker.ready);await page.waitForFunction(()=>!!navigator.serviceWorker.controller);await context.setOffline(true);await page.reload();await page.waitForFunction(()=>document.querySelector('#known-language').value==='en-US');await page.locator('#saved-tab').click();await page.locator('.open-saved').click();await page.locator('#review-panel .source-words .word').first().click();assert.equal(await page.locator('#word-meaning').textContent(),'coffee');await page.locator('#word-close').click();await page.getByRole('button',{name:'← Back to saved',exact:true}).click();await page.locator('.saved-card button[aria-label^="Remove saved"]').click();await page.waitForFunction(()=>document.querySelector('#saved-count').textContent==='0');assert.equal(await page.locator('#review-panel').isVisible(),false);await context.setOffline(false);
 });
 await check('The Kannada prepared review stays in Saved and never creates a conversation or a paid request',async()=>{
  await page.locator('#conversation-tab').click();await page.locator('#try-example').click();await page.locator('#review-panel').waitFor();assert.equal(await page.locator('#saved-tab').getAttribute('aria-current'),'page');assert.equal(await page.locator('#review-panel .source-words').textContent(),KANNADA.text);assert.match(await page.locator('.example-banner').textContent(),/Prepared Kannada/);assert.equal(await page.locator('#saved-count').textContent(),'0');assert.equal(await calls(),startingCalls+1);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 });
 assert.deepEqual(errors,[]);fs.writeFileSync(path.join(ROOT,'validation/web-reply-flow-results.json'),JSON.stringify({passed:checks.length,checks,google_mocked:true,physical_microphone:false,errors},null,2)+'\n');
}catch(e){console.error(e);process.exitCode=1;}finally{await browser?.close();}})();
