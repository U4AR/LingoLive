export const baseLanguage = code => ({cmn:'zh',zho:'zh',iw:'he',in:'id',tl:'fil',no:'nb'}[code.toLowerCase().split('-')[0]] || code.toLowerCase().split('-')[0]);
export function validateLesson(lesson, source) {
  if (!lesson || typeof lesson.contains_learning_language !== 'boolean') throw new Error('The lesson was incomplete. Your original phrase is saved; try again.');
  if(lesson.context_summary!==undefined&&(typeof lesson.context_summary!=='string'||lesson.context_summary.length>600))throw new Error('The conversation context was incomplete. Please retry.');
  const wordsOK = words => Array.isArray(words) && words.every(w => typeof w.text === 'string' && w.text && typeof w.reading === 'string' && typeof w.meaning === 'string' && typeof w.note === 'string' && typeof w.is_word === 'boolean' && (w.is_word ? w.meaning.trim() && w.reading.trim() : !/[\p{L}\p{N}]/u.test(w.text)));
  if (![lesson.translation, lesson.explanation, lesson.tip, lesson.detected_language].every(x => typeof x === 'string') || !wordsOK(lesson.words) || !Array.isArray(lesson.replies)) throw new Error('The lesson was incomplete. Try this phrase again.');
  if (lesson.contains_learning_language && (lesson.words.map(w => w.text).join('') !== source || !lesson.words.some(w => w.is_word) || lesson.replies.length !== 3 || !lesson.replies.every(r => typeof r.label === 'string' && typeof r.translation === 'string' && wordsOK(r.words) && r.words.some(w => w.is_word)))) throw new Error('The lesson changed or missed words. Your phrase is saved; try again.');
  if(lesson.reply_mode==='express'&&(lesson.replies.length!==3||!lesson.contains_learning_language&&lesson.words.length||!lesson.replies.every(r=>typeof r.label==='string'&&typeof r.translation==='string'&&wordsOK(r.words)&&r.words.some(w=>w.is_word))))throw new Error('The phrases for saying this were incomplete. Please retry.');
  return lesson;
}
export function wordPieces(words, pronunciation) {
  let previousWord = false;
  return words.map(w => {
    const text = pronunciation && w.is_word ? w.reading.trim() : w.text;
    const prefix = pronunciation && previousWord && w.is_word && /^[\p{L}\p{N}]/u.test(text) ? ' ' : '';
    previousWord = w.is_word;
    return {word:w, text, prefix};
  });
}
export class PcmResampler {
  constructor(inputRate, frameSize=1600) {
    this.ratio=inputRate/16000; this.frameSize=frameSize; this.sum=0; this.weight=0; this.frame=new Int16Array(frameSize); this.at=0;
  }
  push(input, emit) {
    for (const sample of input) {
      let left=1;
      while (left>1e-8) {
        const take=Math.min(left,this.ratio-this.weight);
        this.sum+=sample*take; this.weight+=take; left-=take;
        if (this.weight>=this.ratio-1e-8) {
          const value=Math.max(-1,Math.min(1,this.sum/this.ratio));
          this.frame[this.at++]=Math.round(value*(value<0?32768:32767)); this.sum=0; this.weight=0;
          if(this.at===this.frameSize) { emit(this.frame); this.frame=new Int16Array(this.frameSize); this.at=0; }
        }
      }
    }
  }
  flush(emit) { if(this.at) { emit(this.frame.slice(0,this.at)); this.at=0; } }
}
