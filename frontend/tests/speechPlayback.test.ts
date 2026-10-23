import assert from 'node:assert/strict';
import { test } from 'node:test';
import { nextSpeechPosition, pacingRate, speechIntervals } from '../src/utils/speechPlayback';

const turn = (start: number, end: number, text = 'We decided to review the database migration') => ({ id: `${start}-${end}`, speaker: 'Alice', start_time: start, end_time: end, text });

test('overlapping and nearby speech retains padding without double counting', () => {
  assert.deepEqual(speechIntervals([turn(10, 12), turn(11, 14), turn(15, 16), turn(30, 35)], 40), [[9.25, 16.75], [29.25, 35.75]]);
});
test('skipping only crosses long internal gaps and never speech or the untranscribed tail', () => {
  const intervals = speechIntervals([turn(10, 15), turn(30, 35)], 60);
  assert.equal(nextSpeechPosition(0, intervals), 9.25);
  assert.equal(nextSpeechPosition(12, intervals), null);
  assert.equal(nextSpeechPosition(20, intervals), 29.25);
  assert.equal(nextSpeechPosition(28, intervals), null);
  assert.equal(nextSpeechPosition(40, intervals), null);
});
test('invalid segments and ranges beyond actual recording cannot cause invalid seeks', () => {
  assert.deepEqual(speechIntervals([turn(-1, 2), turn(3, NaN), turn(9, 10, ''), turn(100, 120)], 20), []);
  assert.equal(nextSpeechPosition(NaN, []), null);
});
test('pacing adapts slowly spoken speech and returns to the selected base speed outside speech', () => {
  assert.equal(pacingRate(5, [turn(0, 10)], 1), 1.25);
  assert.equal(pacingRate(20, [turn(0, 10)], 1.5), 1.5);
  assert.equal(pacingRate(1, [turn(0, 2, 'Yes sir')], 1), 1);
  assert.equal(pacingRate(5, [turn(0, 10)], 2), 2);
});
