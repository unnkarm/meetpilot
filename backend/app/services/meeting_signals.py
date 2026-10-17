"""Cheap, conservative explicit signals across English/Bengali/Hindi speech."""
import re

from app.services.pilot_language import normalized_text


def uncertain_statement(text: str) -> bool:
    content = normalized_text(text)
    return (content.rstrip().endswith("?") or bool(re.search(
        r"\b(?:could|might|maybe|perhaps|should|consider|propose|possibly|if)\b|"
        r"হয়তো|হয়তো|সম্ভবত|প্রস্তাব|যদি|शायद|प्रस्ताव|अगर|"
        r"(?:^|[।.!]\s*)(?:আমরা কি|আমরা কী|কি আমরা|কী আমরা|क्या हम|हमने क्या)|"
        r"\b(?:hoyto|hoyeto|shayad|agar)\b", content)))


def explicit_decision(text: str) -> bool:
    content = normalized_text(text)
    if uncertain_statement(content) or re.search(
        r"(?:not|haven't|haven’t|have not) (?:yet )?decided|"
        r"সিদ্ধান্ত (?:নিইনি|হয়নি|হয়নি|নেওয়া হয়নি|নেওয়া হয়নি)|"
        r"(?:फैसला|तय) (?:नहीं|नही)|অখনও সিদ্ধান্ত", content,
    ):
        return False
    return bool(re.search(
        r"\b(?:we decided to|we have decided to|we agreed to|okay,? let's|let's go with)\b|"
        r"সিদ্ধান্ত (?:নিয়েছি|নিয়েছি|নেওয়া হয়েছে|নেওয়া হয়েছে|নিলাম|হয়েছে|হয়েছে)|"
        r"ঠিক (?:করেছি|করা হয়েছে|করা হয়েছে|করলাম)|সম্মত হয়েছি|সম্মত হয়েছি|"
        r"(?:हमने|हम) .{0,160}?(?:फैसला किया|तय किया|सहमति)|"
        r"(?:फैसला|निर्णय) (?:कर लिया|लिया गया)|"
        r"\b(?:amra .{0,160}?(?:thik korechi|siddhanto niyechi)|humne .{0,160}?(?:faisla kiya|tay kiya))\b",
        content))


def first_person_commitment(text: str) -> bool:
    content = normalized_text(text)
    if uncertain_statement(content) or re.search(
        r"\bi (?:will not|won't|won’t)\b|(?:করব|করবো|দেব|নেব) না|नहीं .{0,40}(?:करूँगा|करूंगा)|(?:करूँगा|करूंगा) नहीं", content,
    ):
        return False
    return bool(re.match(r"(?:i will|i'll|i commit to)\s+.{5,}", content) or
                re.match(r"আমি\s+.{3,}(?:করব|করবো|দেব|দেবো|নেব|নেবো)", content) or
                re.match(r"मैं\s+.{3,}(?:करूँगा|करूंगा|करूँगी|करूंगी|दूँगा|दूंगा)", content))
