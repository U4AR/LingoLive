import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {PcmResampler,validateLesson,wordPieces,baseLanguage} from '../web/core.mjs';
const example=JSON.parse(readFileSync(new URL('../web/example.json',import.meta.url)));
validateLesson(example.lesson,example.text);
const bad=structuredClone(example.lesson);bad.words[0].text='altered';assert.throws(()=>validateLesson(bad,example.text));
const missing=structuredClone(example.lesson);missing.replies.pop();assert.throws(()=>validateLesson(missing,example.text));
const undefinedWord=structuredClone(example.lesson);undefinedWord.words[0].meaning='';assert.throws(()=>validateLesson(undefinedWord,example.text));
assert.equal(wordPieces(example.lesson.words,false).map(x=>x.prefix+x.text).join(''),example.text);
assert.match(wordPieces(example.lesson.words,true).map(x=>x.prefix+x.text).join(''),/kōhī wa ikaga/);
assert.equal(baseLanguage('cmn-Hans-CN'),baseLanguage('zh-CN'));assert.equal(baseLanguage('en-IN'),'en');
for(const rate of [16000,44100,48000]){
 const converter=new PcmResampler(rate);const output=[];const samples=Float32Array.from({length:rate},()=>.5);
 for(let i=0;i<samples.length;i+=128)converter.push(samples.subarray(i,i+128),frame=>output.push(...frame));
 converter.flush(frame=>output.push(...frame));assert.equal(output.length,16000,'exactly 1 second at '+rate);assert.ok(output.every(x=>Math.abs(x-16384)<=1),'PCM scaling within one quantization step at '+rate);
}
const converter=new PcmResampler(48000,2);const output=[];converter.push(new Float32Array([-1,-1,-1,1,1,1,0,0,0]),frame=>output.push(...frame));converter.flush(frame=>output.push(...frame));assert.deepEqual(output,[-32768,32767,0]);
console.log('Web core: source conservation, complete replies/definitions, transliteration, language aliases, and PCM at 16/44.1/48 kHz passed.');
