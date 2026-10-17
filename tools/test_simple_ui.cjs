/* Real Chromium UI check; no model calls or credentials. */
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const ROOT=path.resolve(__dirname,'..');let browser;const checks=[];
async function check(name,fn){await fn();checks.push({name,passed:true});console.log('PASS '+name);}
(async()=>{try{
 browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8094');await page.waitForFunction(()=>document.querySelector('#known-language').value==='en-US');await page.locator('#tutorial-skip').click();
 await check('Settings start hidden and preserve goals, learner memory and opt-in sensors',async()=>{
  assert.equal(await page.locator('#context-settings').isVisible(),false);await page.locator('#settings-open').click();
  for(const id of ['learner-profile','memory-notes','context-setting','use-location','use-audio-context','conversation-goal'])assert.equal(await page.locator('#'+id).isVisible(),true);
  assert.equal(await page.locator('#use-location').isChecked(),false);assert.equal(await page.locator('#use-audio-context').isChecked(),false);
  await page.locator('#settings-close').click();assert.equal(await page.locator('#context-settings').isVisible(),false);
 });
 await page.locator('#try-example').click();await page.locator('.source-words').waitFor();
 await check('Heard speech and three replies are visible with explanation collapsed',async()=>{
  assert.equal(await page.getByText('Heard',{exact:true}).isVisible(),true);assert.equal(await page.getByRole('heading',{name:'Try saying',exact:true}).isVisible(),true);assert.equal(await page.locator('.reply').count(),3);
  assert.equal(await page.locator('.explanation').isVisible(),false);assert.equal(await page.locator('.translation').isVisible(),true);
 });
 await check('A word opens an anchored non-modal meaning bubble and outside tap closes it',async()=>{
  const word=page.locator('.source-words .word').first();await word.click();const dialog=page.locator('#word-dialog');assert.equal(await dialog.isVisible(),true);assert.equal(await dialog.evaluate(n=>n.matches(':modal')),false);
  const box=await dialog.boundingBox(),anchor=await word.boundingBox();assert.ok(box.x>=0&&box.x+box.width<=390&&box.y>=0&&box.y+box.height<=844);assert.ok(Math.abs(box.y-anchor.y)<350);assert.equal(await page.locator('#word-meaning').textContent(),'coffee');
  await page.screenshot({path:path.join(ROOT,'validation/web-word-bubble.png'),fullPage:false});await page.locator('.translation').click();assert.equal(await dialog.isVisible(),false);
 });
 await check('Mobile lesson fits the screen and retains the fixed speaking button',async()=>{
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);const b=await page.locator('#listen-button').boundingBox();assert.ok(b.y>=0&&b.y+b.height<=844);await page.screenshot({path:path.join(ROOT,'validation/web-simple-mobile.png'),fullPage:true});
 });
 assert.deepEqual(errors,[]);fs.writeFileSync(path.join(ROOT,'validation/web-simple-ui-results.json'),JSON.stringify({passed:checks.length,checks,model_calls:0,errors},null,2)+'\n');
}catch(e){console.error(e);process.exitCode=1;}finally{await browser?.close();}})();
