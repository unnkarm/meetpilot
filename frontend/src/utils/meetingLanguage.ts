import Sanscript from '@indic-transliteration/sanscript';

export type DisplayScript = 'original' | 'romanized';
export const MEETING_LANGUAGES = [
  ['en', 'English'], ['hi', 'Hindi · Hinglish display'], ['bn', 'Bengali · Benglish display'],
  ['auto', 'Mixed / auto · English, Bengali, Hindi + others'], ['ta', 'Tamil'], ['te', 'Telugu'],
  ['mr', 'Marathi'], ['gu', 'Gujarati'], ['pa', 'Punjabi'], ['ur', 'Urdu'],
] as const;
export const defaultScript = (language: string): DisplayScript => ['hi', 'bn'].includes(language) ? 'romanized' : 'original';

// Informal Roman spelling has no single standard. These common conversational
// forms complement deterministic script transliteration; English is untouched.
const bengaliWords: Record<string, string> = {
  'আমি': 'ami', 'আমরা': 'amra', 'আমাদের': 'amader', 'আপনি': 'apni', 'আপনার': 'apnar',
  'তুমি': 'tumi', 'সে': 'she', 'এই': 'ei', 'ওই': 'oi', 'এটা': 'eta', 'এটি': 'eti',
  'হ্যাঁ': 'hya', 'না': 'na', 'কি': 'ki', 'কী': 'ki', 'করব': 'korbo', 'করবে': 'korbe',
  'করতে': 'korte', 'করছি': 'korchi', 'করা': 'kora', 'করে': 'kore', 'করি': 'kori',
  'হবে': 'hobe', 'হয়েছে': 'hoyeche', 'হয়েছে': 'hoyeche', 'আছে': 'ache', 'নেই': 'nei',
  'হয়': 'hoy', 'হয়': 'hoy', 'এবং': 'ebong', 'কিন্তু': 'kintu', 'আজ': 'aj', 'কাল': 'kal',
  'মধ্যে': 'moddhe', 'শুক্রবার': 'shukrobar', 'বৃহস্পতিবার': 'brihoshpotibar',
  'সোমবার': 'sombar', 'মঙ্গলবার': 'mongolbar', 'বুধবার': 'budhbar',
  'শনিবার': 'shonibar', 'রবিবার': 'robibar', 'সিদ্ধান্ত': 'siddhanto',
  'নিয়েছি': 'niyechi', 'নিয়েছি': 'niyechi', 'ব্যবহার': 'byabohar', 'সময়': 'shomoy',
  'আপডেট': 'update', 'ডিপ্লয়': 'deploy', 'ডিপ্লয়': 'deploy', 'বাজেট': 'budget',
};
const hindiWords: Record<string, string> = {
  'मैं': 'main', 'हम': 'hum', 'हमने': 'humne', 'हमें': 'humein', 'हैं': 'hain', 'है': 'hai',
  'हाँ': 'haan', 'नहीं': 'nahi', 'हूँ': 'hoon', 'करना': 'karna', 'करूँगा': 'karunga',
  'करूंगा': 'karunga', 'करेंगे': 'karenge', 'इसका': 'iska', 'उसका': 'uska',
  'अपडेट': 'update', 'डिप्लॉय': 'deploy', 'बजट': 'budget',
};
const cache = new Map<string, string>();

function romanWord(word: string, bengali: boolean): string {
  const dictionary = bengali ? bengaliWords : hindiWords;
  if (dictionary[word]) return dictionary[word];
  // Do not translate, run an LLM, or rewrite the saved evidence.
  let roman = Sanscript.t(word, bengali ? 'bengali' : 'devanagari', 'iast')
    .replace(/ś|ṣ/g, 'sh').replace(/ṛ|ṝ/g, 'ri').replace(/ṅ|ñ|ṇ|ṃ/g, 'n')
    .replace(/c/g, 'ch').replace(/ḥ/g, 'h').replace(/~/g, 'n')
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  if (bengali) roman = roman.replace(/v/g, 'b');
  // Final inherent vowels are usually silent in contemporary Hindi/Bengali;
  // explicit vowel signs must remain (e.g. करे -> kare, করা -> kara).
  if (/[क-हक़-य़ক-হড়ঢ়য়]$/u.test(word) && roman.length > 2) roman = roman.replace(/a$/, '');
  return roman.replace(/\|/g, '.');
}

export function romanizeMeetingText(text: string): string {
  if (cache.has(text)) return cache.get(text)!;
  const result = text.replace(/https?:\/\/\S+|`[^`]*`|[\u0900-\u097f\u200c\u200d]+|[\u0980-\u09ff\u200c\u200d]+/gu,
    word => word.startsWith('http') || word.startsWith('`') ? word :
      romanWord(word.replace(/[\u200c\u200d]/g, ''), /[\u0980-\u09ff]/u.test(word)));
  if (cache.size >= 1000) cache.clear();
  cache.set(text, result);
  return result;
}
