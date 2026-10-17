"""Fast English/Bengali/Hindi dialogue hints; originals remain the evidence."""
import re
import unicodedata

from app.core.app_config import APP_CONFIG
from app.services.language_detection import detect_text_language, language_label

LABELS = {"en": "English", "bn": "Bengali", "hi": "Hindi"}


def normalized_text(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def native_script(char: str) -> str | None:
    # Danda punctuation is shared by Indic languages. It must not switch a
    # Bengali sentence to a Hindi voice or mark it as a Hindi speech turn.
    if unicodedata.category(char)[0] not in {"L", "M"}:
        return None
    return "bn" if "\u0980" <= char <= "\u09ff" else "hi" if "\u0900" <= char <= "\u097f" else None


def script_languages(text: str) -> set[str]:
    languages = {code for char in text if (code := native_script(char))}
    if re.search(r"[A-Za-z]{2,}", text):
        languages.add("en")
    return languages


def reply_language(question: str, hint: str | None = None) -> str:
    """Follow the request, including short questions that text detectors abstain on."""
    if APP_CONFIG.language.qa_language_mode != "question":
        return "en"
    text = normalized_text(question)
    # Explicit language requests win over the language of the surrounding query.
    for code, pattern in (
        ("bn", r"(?:in bengali|in bangla|বাংলায়|বাংলায়|বাংলাতে|banglay|bangla te)"),
        ("hi", r"(?:in hindi|हिंदी में|हिन्दी में|hindi mein|hindi me\b)"),
        ("en", r"(?:in english|ইংরেজিতে|इंग्लिश में|अंग्रेज़ी में|english mein)"),
    ):
        if re.search(pattern, text):
            return code
    counts = {code: sum(native_script(char) == code for char in text) for code in ("bn", "hi")}
    if max(counts.values()):
        # Prefer the last question's native script over English technical nouns.
        code = max(counts, key=counts.get)
        if code == "hi" and len(text) >= 20:
            # Hindi and Marathi share Devanagari. Preserve the existing
            # Marathi detection for longer requests instead of relabelling it.
            detected = detect_text_language(question)
            if detected.code == "mr":
                return "mr"
        return code
    if re.search(r"\b(?:ki hoyeche|ki siddhanto|ki niye|ki ki|meeting er|meeting ta|amra|amader|bolo|bolun|ektu|bujhiye|shongkhep|siddhanto|alochona)\b", text):
        return "bn"
    if re.search(r"\b(?:kya|kyun|kaise|batao|bataiye|samjhao|humne|hamne|humein|faisla|dhanyavad|meeting ka|meeting ki|meeting mein)\b", text):
        return "hi"
    detected = detect_text_language(question)
    return detected.code or (hint if hint and hint != "auto" else "en")


def reply_instruction(question: str, hint: str | None = None) -> str:
    code = reply_language(question, hint)
    label = LABELS.get(code) or language_label(code) or code
    script = " Use Bengali script for speech synthesis." if code == "bn" else (
        " Use Devanagari script for speech synthesis." if code == "hi" else "")
    return (f"Answer in {label}, matching the user's request.{script} "
            "Read English, Bengali and Hindi code-switching together. Preserve names, numbers, "
            "negations, deadlines and English technical terms. Never infer a decision from a suggestion.")


def is_followup(text: str) -> bool:
    return bool(re.search(
        r"(?:আরও বল|আরো বল|একটু ছোট|ছোট করে|সংক্ষেপে বল|বুঝিয়ে বল|বুঝিয়ে বল|দ্বিতীয়|দ্বিতীয়|প্রথম পয়েন্ট|"
        r"और बताओ|थोड़ा छोटा|संक्षेप में|समझाओ|दूसर[ेाी] पॉइंट|पहला पॉइंट|"
        r"\b(?:aro bolo|ektu choto|bujhiye bolo|aur batao|thoda chhota|samjhao)\b)", normalized_text(text)))


def is_addressed_followup(text: str) -> bool:
    return is_followup(text) or bool(re.match(
        r"(?:আর |আরও |তাহলে |और |तो )?(?:কি|কী|কেন|কখন|কার|কিভাবে|কীভাবে|কোন|আমাদের কি|আমরা কি|বল|দাও|"
        r"क्या|क्यों|कब|कौन|कैसे|बताओ|बताइए|समझाओ|हमने क्या|हम क्या|"
        r"ki\b|keno\b|kibhabe\b|bolo\b|bolun\b|amra ki\b|kya\b|kyun\b|kaise\b|batao\b|humne kya\b)",
        normalized_text(text)))


def native_intent(query: str) -> str | None:
    """Explicit native requests only; a language switch never authorizes a tool."""
    text = normalized_text(query)
    task = r"(?:টাস্ক|কাজ|टास्क|कार्य|काम|task)"
    creation = re.search(r"(?:তৈরি (?:করো|করুন|করে দাও|কর)(?![\u0980-\u09ff])|যোগ (?:করো|করুন)|বানাও(?![\u0980-\u09ff])|"
                         r"(?:बनाओ|बनाइए|बना दो|जोड़ो)(?![\u0900-\u097f])|\btoiri koro\b|\bbanao\b)", text)
    reported = re.search(r"(?:বলেছে|বলেছিল|বলল|बोला|कहा|হয়তো|হয়তো|अगर|शायद|\bmaybe\b)", text)
    if re.search(task, text) and creation and not reported:
        return "action_request"
    if re.search(task, text) and re.search(r"(?:মুছে|পরিবর্তন|ডিলিট|हटाओ|बदलो|डिलीट)", text):
        return "clarification"
    if re.search(r"(?:আমার কাজ|আমার টাস্ক|আমাকে দেওয়া কাজ|আমাকে দেওয়া কাজ|मेरे काम|मेरे टास्क|मुझे सौंपे|\bamar (?:kaj|task)|\bmere (?:kaam|tasks?))", text):
        return "task_query"
    historical = re.search(r"(?:গত\s*সপ্তাহ|গত\s*মাস|আগের মিটিং|পূর্বের মিটিং|গতকালের|पिछले हफ्ते|पिछले सप्ताह|पिछली मीटिंग|पिछली बैठक|पिछले महीने|\bgoto (?:shoptaho|soptaho)|\bpichl[ei] (?:hafte|meeting))", text)
    docs = re.search(r"(?:ডকুমেন্ট|নথি|ফাইল|দস্তাবেজ|दस्तावेज|डॉक्यूमेंट|फ़ाइल|फाइल)", text)
    if historical:
        return "historical_meeting_question"
    if docs:
        return "knowledge_question"
    recent = re.search(r"(?:এইমাত্র|এই মাত্র|এখনই|अभी|\bekhoni\b|\babhi\b)", text)
    summary = re.search(r"(?:সারাংশ|সংক্ষেপ|মূল পয়েন্ট|মূল পয়েন্ট|কী কী আলোচনা|কি কি আলোচনা|কী আলোচনা|কি আলোচনা|"
                        r"কী সিদ্ধান্ত|কি সিদ্ধান্ত|কী ঠিক|কি ঠিক|কি কি কথা|কী কী কথা|সারসংক্ষেপ|सारांश|संक्षेप|मुख्य बातें|मुख्य पॉइंट|क्या चर्चा|क्या फैसला|क्या तय|"
                        r"\b(?:shongkhep|saransh|ki (?:ki )?(?:alochona|siddhanto|decide|decision)|kya (?:charcha|faisla|decide|decision)))", text)
    if summary:
        focused = re.search(r"(?:নিয়ে|নিয়ে|বিষয়ে|বিষয়ে|সম্পর্কে|के बारे|about|regarding)", text)
        return "meeting_context_question" if recent or focused else "summarize"
    if is_followup(text):
        return "meeting_context_question"
    if re.fullmatch(r"(?:ধন্যবাদ|ধন্যবাদ তোমাকে|শুনতে পাচ্ছ|তুমি আছো|धन्यवाद|शुक्रिया|सुन रहे हो|dhonnobad|dhanyavad)[।.!? ]*", text):
        return "general_conversation"
    return None


_MESSAGES = {
    "no_evidence": {
        "bn": "[Uncertain: উত্তর দেওয়ার মতো যথেষ্ট প্রমাণ এই আলোচনায় পাইনি।]",
        "hi": "[Uncertain: जवाब देने के लिए इस चर्चा में पर्याप्त प्रमाण नहीं मिला।]",
    },
    "model_unavailable": {
        "bn": "[Uncertain: স্থানীয় AI নির্ভরযোগ্য উত্তর দিতে পারেনি। একটু পরে আবার বলুন।]",
        "hi": "[Uncertain: स्थानीय AI भरोसेमंद जवाब नहीं दे पाया। थोड़ी देर में फिर पूछें।]",
    },
    "unverified_voice": {
        "bn": "[Uncertain: মিটিংয়ের কণ্ঠস্বর দিয়ে আপনার workspace পরিচয় যাচাই করা যায় না। কাজ তৈরি করতে নিজের microphone বা task form ব্যবহার করুন।]",
        "hi": "[Uncertain: मीटिंग की आवाज़ से आपकी workspace पहचान सत्यापित नहीं होती। काम बनाने के लिए अपना microphone या task form इस्तेमाल करें।]",
    },
    "clarification": {
        "bn": "কোন কাজটি কীভাবে বদলাতে চান বলুন। এখনও কোনো পরিবর্তন করিনি।",
        "hi": "कौन सा काम कैसे बदलना है बताइए। अभी कोई बदलाव नहीं किया है।",
    },
    "thanks": {"bn": "আপনাকে স্বাগতম।", "hi": "आपका स्वागत है।"},
    "greeting": {"bn": "আমি শুনছি। কী জানতে চান?", "hi": "मैं सुन रहा हूँ। क्या जानना चाहते हैं?"},
    "no_tasks": {"bn": "আপনার অনুমতিতে দেখা যায় এমন কোনো কাজ পাইনি।", "hi": "आपकी अनुमति में दिखने वाला कोई काम नहीं मिला।"},
    "created_task": {"bn": "কাজ তৈরি করেছি: {task}।", "hi": "काम बना दिया: {task}।"},
    "your_tasks": {"bn": "আপনার সাম্প্রতিক কাজ: ", "hi": "आपके हाल के काम: "},
    "recent_tasks": {"bn": "সাম্প্রতিক কাজ: ", "hi": "हाल के काम: "},
    "task_failed": {
        "bn": "[Uncertain: কাজের অনুরোধ বা আপনার অনুমতি যাচাই করতে পারিনি। task form ব্যবহার করুন।]",
        "hi": "[Uncertain: काम का अनुरोध या आपकी अनुमति सत्यापित नहीं कर पाया। task form इस्तेमाल करें।]",
    },
}


def localized_message(key: str, question: str, english: str) -> str:
    return _MESSAGES.get(key, {}).get(reply_language(question), english)
