/* Local-only chapter backgrounds; no Google calls, external fonts or assets. */
const {chromium}=require('playwright'),fs=require('node:fs'),path=require('node:path');
const ROOT=path.resolve(__dirname,'..'),OUT=path.resolve(process.argv[2]||'/tmp/lingolive-submission');
const escape=s=>s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
(async()=>{let browser;try{browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});const page=await browser.newPage({viewport:{width:1280,height:720}});const scenes=JSON.parse(fs.readFileSync(path.join(ROOT,'docs/submission/demo-scenes.json')));fs.mkdirSync(path.join(OUT,'scenes'),{recursive:true});
for(const [index,s]of scenes.entries()){
 await page.setContent(`<style>*{box-sizing:border-box}body{margin:0;width:1280px;height:720px;background:#edf1e7;font-family:Arial,sans-serif;color:#193b30}aside{position:absolute;left:0;top:0;width:250px;height:650px;background:#193b30;color:#f5f5ef;padding:32px 25px}b{font-size:22px}small{display:block;font-size:12px;letter-spacing:1px;color:#b9d798;margin-top:16px}h1{font-weight:500;font-size:31px;line-height:1.18;margin:62px 0 30px;overflow-wrap:break-word}p{font-size:16px;line-height:1.6;color:#d1dfca}.foot{position:absolute;bottom:22px;font-size:11px;color:#b9d798}.video{position:absolute;left:260px;top:30px;width:1000px;height:620px;background:#f5f5ef;border-radius:10px}</style><aside><b>LingoLive</b><small>AI BUILDER CUP · EDUCATION</small><h1>${escape(s.title)}</h1><p>${escape(s.note)}</p><div class="foot">${String(index+1).padStart(2,'0')} / ${scenes.length} · Ashish T. Vasant<br>Recorded prototype · English narration</div></aside><div class="video"></div>`);
 await page.screenshot({path:path.join(OUT,'scenes',s.id+'-background.png')});
}
console.log('Rendered '+scenes.length+' chapter backgrounds');
}finally{await browser?.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
