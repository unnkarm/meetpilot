import assert from 'node:assert/strict';
import { test } from 'node:test';
import { defaultScript, romanizeMeetingText } from '../src/utils/meetingLanguage';

test('Hindi and Bengali default to Roman letters; English remains original', () => {
  assert.equal(defaultScript('en'), 'original');
  assert.equal(defaultScript('hi'), 'romanized');
  assert.equal(defaultScript('bn'), 'romanized');
});
test('Benglish keeps existing English and technical terms intact', () => {
  assert.equal(romanizeMeetingText('আমরা শুক্রবার API deploy করব।'), 'amra shukrobar API deploy korbo.');
});
test('Hinglish keeps the utterance in Hindi using Roman letters', () => {
  assert.equal(romanizeMeetingText('मैं API अपडेट करूँगा।'), 'main API update karunga.');
});
test('URLs, inline code, English pipes, timestamps, and source strings survive', () => {
  const original = 'আমরা API | pgvector v2 [01:23] `আমরা` https://example.com/আমরা';
  assert.equal(romanizeMeetingText(original), 'amra API | pgvector v2 [01:23] `আমরা` https://example.com/আমরা');
  assert.equal(original, 'আমরা API | pgvector v2 [01:23] `আমরা` https://example.com/আমরা');
  assert.equal(romanizeMeetingText('Review PR #42 by Friday.'), 'Review PR #42 by Friday.');
});
