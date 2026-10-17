import {baseLanguage} from './core.mjs';
const KEY='lingolive-tutorial-v1';

// The walkthrough is local and uses a prepared example: no AI requests or
// microphone/location permissions until the learner chooses those actions.
export function setupTutorial(onConnect,onReplay=()=>{}){
  const $=id=>document.getElementById(id),dialog=$('tutorial-dialog');let step=0;
  const titles=['Your languages','A little help, word by word','Listen. Understand. Reply.'];
  function render(){
    $('tutorial-progress').textContent=`${step+1} of 3`;
    $('tutorial-title').textContent=titles[step];
    ['languages','words','listen'].forEach((name,index)=>{$('tutorial-'+name).hidden=index!==step;});
    $('tutorial-back').hidden=step===0;$('tutorial-next').textContent=step===2?'Let’s start':'Next →';
    $('tutorial-error').hidden=true;$('tutorial-title').focus();
  }
  function show(){
    if(dialog.open)return;
    for(const [target,source]of [['tutorial-known','known-language'],['tutorial-learning','learning-language']]){
      $(target).replaceChildren(...[...$(source).options].map(option=>option.cloneNode(true)));$(target).value=$(source).value;
    }
    step=0;$('tutorial-meaning').hidden=true;$('tutorial-word').textContent='ありがとう';$('tutorial-pronunciation').setAttribute('aria-pressed','false');
    dialog.showModal();render();
  }
  function finish(){try{localStorage.setItem(KEY,'done');}catch{}dialog.close();$('listen-button').focus();}
  $('tutorial-skip').onclick=finish;
  dialog.addEventListener('cancel',()=>{try{localStorage.setItem(KEY,'done');}catch{}});
  $('tutorial-back').onclick=()=>{step=Math.max(0,step-1);render();};
  $('tutorial-next').onclick=()=>{
    if(step===0){
      if(baseLanguage($('tutorial-known').value)===baseLanguage($('tutorial-learning').value)){
        $('tutorial-error').textContent='Choose two different languages.';$('tutorial-error').hidden=false;return;
      }
      const changed=$('known-language').value!==$('tutorial-known').value||$('learning-language').value!==$('tutorial-learning').value;
      $('known-language').value=$('tutorial-known').value;$('learning-language').value=$('tutorial-learning').value;
      if(changed)$('learning-language').dispatchEvent(new Event('change'));
    }
    if(step===2){finish();onConnect();return;}
    step++;render();
  };
  $('tutorial-word').onclick=()=>{$('tutorial-meaning').hidden=!$('tutorial-meaning').hidden;};
  $('tutorial-pronunciation').onclick=()=>{
    const reading=$('tutorial-pronunciation').getAttribute('aria-pressed')!=='true';
    $('tutorial-pronunciation').setAttribute('aria-pressed',String(reading));$('tutorial-word').textContent=reading?'arigatō':'ありがとう';
  };
  $('tutorial-replay').onclick=async()=>{await onReplay();show();};
  let seen=false;try{seen=localStorage.getItem(KEY)==='done';}catch{}
  if(!seen)show();
}
