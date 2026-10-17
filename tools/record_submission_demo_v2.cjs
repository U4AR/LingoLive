/* Approved v2: real deployed APIs, disclosed synthetic microphone/GPS only.
 * No trace, HAR, credential screenshots or stored cookie/browser profile.
 */
const {chromium}=require('playwright'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const OUT=path.resolve(process.argv[2]||'/tmp/lingolive-video-v2'),BASE='https://lingolive-358650584819.us-central1.run.app';
const pause=ms=>new Promise(r=>setTimeout(r,ms)),now=()=>performance.now();
let browser,ctx,page,origin,startVideo;const jobs=[],report={app_version:'1.9',url:BASE,google_mocked:false,api_responses_replaced:false,physical_microphone:false,synthetic_microphone:true,synthetic_ambience:true,geolocation_and_elapsed_time_simulated:true,maximum_lesson_requests:10,scenes:[],lessons:[],inputs:[],page_errors:[],success:false};
const requests=[],received=[];
async function shot(id,fn){const row={id,start:((now()-origin)/1000)};report.scenes.push(row);await fn(row);row.end=(now()-origin)/1000;row.seconds=row.end-row.start;await page.screenshot({path:path.join(OUT,'shots',id+'.png')});console.log('Captured '+id+' '+row.seconds.toFixed(2)+'s');return row;}
async function top(){await page.evaluate(()=>scrollTo({top:0,behavior:'instant'}));await pause(200);}
async function settled(){await page.waitForFunction(()=>![...document.querySelectorAll('.transcript .phrase-meta')].some(n=>/Waiting|Understanding/.test(n.textContent)),null,{timeout:45000});await pause(350);}
async function choose(id,lesson,pattern){
 assert.equal(lesson.replies.length,3);const i=lesson.replies.findIndex(r=>pattern.test(r.translation));assert.ok(i>=0,'No faithful selected reply for '+id);
 const reply=lesson.replies[i],card=page.locator('#lesson-panel .reply').nth(i);await card.scrollIntoViewIfNeeded();await pause(500);
 report.selected=report.selected||{};report.selected[id]={index:i,text:reply.words.map(w=>w.text).join(''),translation:reply.translation,words:reply.words};
 // The actual card remains on screen; no scripted result is substituted.
}
async function speech(id,file,pattern,row,fallbackText=null){
 const before=received.length;row.listen_click=(now()-origin)/1000;await top();
 const pending=page.waitForResponse(r=>r.url()===BASE+'/v1/teach'&&r.request().method()==='POST',{timeout:60000});pending.catch(()=>{});
 await page.locator('#listen-button').click();await page.getByText('Listening · all languages',{exact:true}).waitFor({timeout:20000});
 row.input_start=(now()-origin)/1000;const duration=await page.evaluate(name=>window.demoSpeech(name),file);row.input_end=(now()-origin)/1000;
 report.inputs.push({id,audio_file:'audio/'+file,seconds:duration,source:'Google TTS plus disclosed synthetic ambience through getUserMedia MediaStream / real AudioWorklet / real Google transcription'});
 await pause(450);await page.locator('#listen-button').click();row.stop_click=(now()-origin)/1000;
 const response=await pending;assert.equal(response.status(),200,'Real lesson failed: '+id);let lesson=await response.json();await settled();row.response_ready=(now()-origin)/1000;row.original_asr_text=response.request().postDataJSON().text;
 if(fallbackText&&(!lesson.contains_learning_language||!lesson.replies.some(r=>pattern.test(r.translation)))){
  row.correction_start=(now()-origin)/1000;row.correction_reason='Automatic recognition did not preserve the expected Kannada question';await pause(1200);lesson=await type(fallbackText);row.correction_end=(now()-origin)/1000;row.corrected_text=fallbackText;row.source_from='visible_typed_correction';
 }
 await pause(900);await choose(id,lesson,pattern);await page.getByRole('button',{name:'Pronunciation',exact:true}).click();await pause(1100);await page.getByRole('button',{name:'Original',exact:true}).click();await pause(600);
 assert.ok(received.length>before);row.lesson_text=row.corrected_text||response.request().postDataJSON().text;row.source_contains_learning_language=lesson.contains_learning_language;row.reply_mode=lesson.reply_mode;
 return lesson;
}
async function type(text,mine=false){
 await page.locator('#type-details').evaluate(n=>n.open=true);await page.locator('#phrase-input').fill(text);if(mine)await page.locator('#phrase-is-mine').check();
 const pending=page.waitForResponse(r=>r.url()===BASE+'/v1/teach'&&r.request().method()==='POST',{timeout:60000});pending.catch(()=>{});await page.locator('#phrase-form button[type=submit]').click();const r=await pending;assert.equal(r.status(),200,'Typed live lesson failed');const d=await r.json();await settled();return d;
}
(async()=>{try{
 const input=await new Promise(resolve=>{let s='';process.stdin.setEncoding('utf8');process.stdin.on('data',v=>s+=v);process.stdin.on('end',()=>resolve(JSON.parse(s)));});
 fs.mkdirSync(path.join(OUT,'raw'),{recursive:true});fs.mkdirSync(path.join(OUT,'shots'),{recursive:true});
 const proxy=process.env.HTTPS_PROXY||process.env.HTTP_PROXY;
 browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,...(proxy?{proxy:{server:proxy,bypass:'127.0.0.1,localhost'}}:{}),args:['--no-sandbox','--disable-dev-shm-usage','--autoplay-policy=no-user-gesture-required']});
 ctx=await browser.newContext({viewport:{width:460,height:900},recordVideo:{dir:path.join(OUT,'raw'),size:{width:460,height:900}}});
 const signed=await ctx.request.post(BASE+'/v1/session',{data:{token:input.access_code},headers:{Origin:BASE}});assert.equal(signed.status(),200);input.access_code='';
 await ctx.route(BASE+'/__demo/audio/*',route=>{const name=new URL(route.request().url()).pathname.split('/').at(-1);assert.match(name,/^[a-z-]+\.wav$/);return route.fulfill({path:path.join(OUT,'audio',name),contentType:'audio/wav'});});
 await ctx.addInitScript(()=>{
  // Only sensor/input simulation: no app logic, response or storage substitution.
  let offset=0,next=0;const realNow=Date.now;Date.now=()=>realNow()+offset;
  const watchers=new Map();let coords={latitude:12.972,longitude:77.595,accuracy:10,speed:0};const pos=()=>({coords,timestamp:Date.now()});
  Object.defineProperty(navigator,'geolocation',{value:{watchPosition:ok=>{watchers.set(++next,ok);return next;},clearWatch:id=>watchers.delete(id),getCurrentPosition:ok=>ok(pos())}});
  window.demoMove=(lat=12.972,lon=77.595,advance=0)=>{offset+=advance;coords={latitude:lat,longitude:lon,accuracy:10,speed:0};for(const ok of watchers.values())ok(pos());};
  let ac,destination;
  navigator.mediaDevices.getUserMedia=async()=>{ac=new AudioContext({sampleRate:48000});await ac.resume();destination=ac.createMediaStreamDestination();return destination.stream;};
  window.demoSpeech=async name=>{if(!ac||!destination)throw Error('Microphone is not active');const r=await fetch('/__demo/audio/'+name),buffer=await ac.decodeAudioData(await r.arrayBuffer()),node=ac.createBufferSource();node.buffer=buffer;node.connect(destination);const seconds=buffer.duration;await new Promise(resolve=>{node.onended=resolve;node.start();});return seconds;};
 });
 origin=now();page=await ctx.newPage();page.on('pageerror',e=>report.page_errors.push(e.name));
 page.on('request',r=>{if(r.url()===BASE+'/v1/teach'&&r.method()==='POST'){requests.push({at:(now()-origin)/1000,payload:r.postDataJSON()});if(requests.length>10){report.budget_exceeded=true;page.close().catch(()=>{});}}});
 page.on('response',r=>{if(r.url()===BASE+'/v1/teach'&&r.request().method()==='POST')jobs.push((async()=>{const d=await r.json();received.push(d);report.lessons.push({status:r.status(),text:r.request().postDataJSON().text,at:(now()-origin)/1000,request:r.request().postDataJSON(),response:d});})());});
 await page.goto(BASE);assert.equal((await ctx.request.get(BASE+'/health')).status(),200);await page.locator('#tutorial-skip').click();await page.locator('#learning-language').selectOption('kn-IN');await top();
 await shot('solution',async()=>{await pause(3500);});
 await shot('plan',async()=>{
  const before=requests.length;await page.locator('#plan-open').click();await page.locator('#plan-intent').fill('');await page.locator('#plan-intent').pressSequentially('Take a cab to Bengaluru railway station. I might stop for tea on the way.',{delay:30});await page.locator('#plan-form details').evaluate(n=>n.open=true);await page.locator('#plan-steps').pressSequentially('Get a cab\nTea stop?\nReach the station',{delay:35});await page.locator('#plan-form button[type=submit]').click();await page.locator('#plan-progress').scrollIntoViewIfNeeded();await pause(1600);assert.equal(requests.length,before);report.plan_saved_without_ai=true;await page.locator('#settings-close').click();await top();
 });
 await shot('cab',async row=>{const d=await speech('cab','driver-question-mic.wav',/station|railway/i,row);assert.equal(d.contains_learning_language,true);assert.match(row.lesson_text,/ಎಲ್ಲಿಗೆ|ಹೋಗ/);});
 await shot('express',async row=>{const d=await speech('express','learner-english-mic.wav',/tea/i,row);assert.equal(d.contains_learning_language,false);assert.equal(d.reply_mode,'express');assert.match(row.lesson_text.toLowerCase(),/tea/);});
 await shot('cafe',async row=>{await page.locator('#plan-open').click();await page.getByRole('button',{name:'Done, next step',exact:true}).click();await page.locator('#settings-close').click();await top();const d=await speech('cafe','cafe-question-mic.wav',/parcel|take.?away|take.?out|to go/i,row,'ಇಲ್ಲೇ ಕುಡಿಯುತ್ತೀರಾ ಅಥವಾ ಪಾರ್ಸೆಲ್ ಬೇಕಾ?');assert.equal(d.contains_learning_language,true);});
 // A future destination remains a plan, not a current location. Finish/pause it
 // explicitly before the separately labelled later-return demonstration.
 await page.locator('#plan-open').click();await page.locator('#pause-plan').click();await page.locator('#settings-close').click();
 await shot('place-setup',async()=>{
  await page.locator('#settings-open').click();await page.locator('#place-settings').evaluate(n=>n.open=true);await page.locator('#use-place-memory').check();
  await page.evaluate(()=>window.demoMove());await page.evaluate(()=>window.demoMove(12.972,77.595,60001));await page.locator('#place-state').scrollIntoViewIfNeeded();assert.match(await page.locator('#place-state').textContent(),/Ready/);await pause(800);await page.locator('#settings-close').click();
  const d=await type('I order ginger tea to take away here.',true);assert.ok(d.place_candidates?.length===1,'Real source did not propose a grounded place note');await page.locator('#settings-open').click();await page.locator('[data-place]').waitFor();await page.getByRole('button',{name:'Confirm place note',exact:true}).click();await page.locator('[data-place]').scrollIntoViewIfNeeded();await pause(1200);report.place_note=d.place_candidates[0];
 });
 await page.evaluate(()=>window.demoMove(13,77.7,1000));await page.locator('#new-conversation').click();await page.locator('#settings-close').click();await type('ಏನು ಬೇಕು?');assert.deepEqual(requests.at(-1).payload.place_context,[]);report.no_place_context_away=true;
 await page.evaluate(()=>window.demoMove());await page.evaluate(()=>window.demoMove(12.972,77.595,60001));await page.locator('#settings-open').click();await page.locator('#new-conversation').click();await page.locator('#place-state').scrollIntoViewIfNeeded();assert.match(await page.locator('#place-state').textContent(),/Back near/);await pause(700);await page.locator('#settings-close').click();await top();
 await shot('place-return',async row=>{await speech('place','shop-question-mic.wav',/ginger/i,row,'ಏನು ಬೇಕು?');const req=requests.at(-1).payload;assert.ok(req.place_context.length>0);assert.match(JSON.stringify(req.place_context),/ginger/i);assert.deepEqual(req.recent_turns,[]);assert.equal(req.user_goal,'');assert.doesNotMatch(JSON.stringify(req.place_context),/latitude|longitude/);report.return_place_context=req.place_context;});
 await shot('learn',async()=>{const before=requests.length;await top();await page.getByRole('button',{name:'Learn later in Saved',exact:true}).click();await page.locator('#review-panel .reply .word').first().click();await pause(3500);await page.locator('#word-close').click();await page.getByRole('button',{name:'Pronunciation',exact:true}).click();await pause(2800);await page.locator('#review-panel .reply').first().scrollIntoViewIfNeeded();await pause(2500);assert.equal(requests.length,before);report.saved_review_without_ai=true;});
 await Promise.all(jobs);assert.ok(requests.length<=10);assert.deepEqual(report.page_errors,[]);assert.ok(report.lessons.every(r=>r.status===200));
 report.lesson_requests=requests.length;report.google_generation_calls=requests.length*2;report.recorded_wall_seconds=(now()-origin)/1000;const video=page.video();await ctx.close();ctx=null;await video.saveAs(path.join(OUT,'raw/app.webm'));report.raw_video='raw/app.webm';report.success=true;
 await browser.close();browser=null;
}catch(e){report.error_type=e.name;report.error=e.message;console.error('Capture failed: '+e.message);process.exitCode=1;}finally{await Promise.allSettled(jobs);if(ctx)await ctx.close();await browser?.close();fs.writeFileSync(path.join(OUT,'recording.json'),JSON.stringify(report,null,2)+'\n');}})();
