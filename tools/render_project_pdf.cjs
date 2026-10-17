/* Render the local, editable project deck without external fonts or network requests. */
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const ROOT=path.resolve(__dirname,'..');
(async()=>{let browser,server;try{
 const html=fs.readFileSync(path.join(ROOT,'docs/how-it-works.html'),'utf8').replace('../validation/web-word-bubble.png','/preview.png');
 server=http.createServer((req,res)=>{
  if(req.url==='/'){res.setHeader('Content-Type','text/html; charset=utf-8');res.end(html);}
  else if(req.url==='/preview.png'){res.setHeader('Content-Type','image/png');res.end(fs.readFileSync(path.join(ROOT,'validation/web-word-bubble.png')));}
  else{res.statusCode=404;res.end();}
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const origin='http://127.0.0.1:'+server.address().port;
 browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 const page=await browser.newPage({viewport:{width:1280,height:720}});
 await page.route(/^https?:/,route=>route.request().url().startsWith(origin+'/')?route.continue():route.abort());
 await page.goto(origin);
 await page.evaluate(()=>document.fonts.ready);
 const checks=await page.evaluate(()=>({slides:document.querySelectorAll('.slide').length,images:[...document.images].every(i=>i.complete&&i.naturalWidth>0),overflow:[...document.querySelectorAll('.slide')].map((s,i)=>({page:i+1,height:s.scrollHeight,width:s.scrollWidth})).filter(s=>s.height>720||s.width>1280)}));
 if(checks.slides!==8||!checks.images||checks.overflow.length)throw new Error(JSON.stringify(checks));
 await page.pdf({path:path.join(ROOT,'docs/LingoLive-How-It-Works.pdf'),printBackground:true,preferCSSPageSize:true,displayHeaderFooter:false,tagged:true});
 const preview=process.env.PDF_PREVIEW_DIR;
 if(preview){fs.mkdirSync(preview,{recursive:true});for(const [i,node] of (await page.locator('.slide').all()).entries())await node.screenshot({path:path.join(preview,'page-'+String(i+1).padStart(2,'0')+'.png')});}
 console.log(JSON.stringify({file:'docs/LingoLive-How-It-Works.pdf',...checks,bytes:fs.statSync(path.join(ROOT,'docs/LingoLive-How-It-Works.pdf')).size}));
}finally{await browser?.close();server?.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
