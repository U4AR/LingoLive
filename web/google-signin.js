/* Google credentials remain in memory and are sent only to the same-origin relay. */
let sdk;
function loadGoogle() {
  if(window.google?.accounts?.id)return Promise.resolve();
  if(!sdk)sdk=new Promise((resolve,reject)=>{
    const script=document.createElement('script');script.src='https://accounts.google.com/gsi/client';script.async=true;script.defer=true;
    const timer=setTimeout(()=>{script.remove();sdk=null;reject(new Error('Google sign-in did not load. Check your connection and try again.'));},12000);
    script.onload=()=>{clearTimeout(timer);resolve();};script.onerror=()=>{clearTimeout(timer);script.remove();sdk=null;reject(new Error('Google sign-in is unavailable. Please try again.'));};document.head.append(script);
  });
  return sdk;
}
export async function renderGoogleSignIn(config,target,callback) {
  if(config.google_provider==='firebase'){
    const {prepare,googlePopup}=await import('./firebase-auth.js');
    await prepare(config.firebase);target.replaceChildren();
    const button=document.createElement('button');button.type='button';button.className='small-button';button.textContent='Sign in with Google';
    button.onclick=async()=>{button.disabled=true;try{callback(await googlePopup(config.firebase));}catch{callback('');}finally{button.disabled=false;}};
    target.append(button);return;
  }

  await loadGoogle();
  if(!window.google?.accounts?.id)throw new Error('Google sign-in is unavailable. Please try again.');
  window.google.accounts.id.initialize({client_id:config.google_client_id,nonce:config.nonce,auto_select:false,ux_mode:'popup',callback:response=>callback(response.credential||'')});
  target.replaceChildren();
  window.google.accounts.id.renderButton(target,{type:'standard',theme:'outline',size:'large',text:'signin_with',shape:'pill',width:Math.max(200,Math.min(320,target.clientWidth||280))});
}
export function forgetGoogleSelection(){window.google?.accounts?.id?.disableAutoSelect();}
