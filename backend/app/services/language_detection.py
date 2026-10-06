"""Conservative text language detection; unknown is preferable to a false label."""

from dataclasses import dataclass
from functools import lru_cache

from app.core.app_config import APP_CONFIG


@dataclass(frozen=True)
class LanguageDetection:
    code: str | None = None
    name: str | None = None
    confidence: float | None = None
    is_multilingual: bool = False


@lru_cache(maxsize=1)
def _detector():
    from lingua import LanguageDetectorBuilder

    return LanguageDetectorBuilder.from_all_languages().build()


def detect_text_language(text: str) -> LanguageDetection:
    if not APP_CONFIG.language.enable_detection or len(text.strip()) < 20:
        return LanguageDetection()
    try:
        rankings = _detector().compute_language_confidence_values(text[:12000])
    except (ImportError, RuntimeError, ValueError):
        return LanguageDetection()
    if not rankings:
        return LanguageDetection()
    best = rankings[0]
    runner_up = rankings[1].value if len(rankings) > 1 else 0.0
    if best.value < APP_CONFIG.language.minimum_confidence or best.value - runner_up < 0.1:
        return LanguageDetection()
    return LanguageDetection(
        code=best.language.iso_code_639_1.name.lower(),
        name=best.language.name.title(),
        confidence=round(float(best.value), 3),
    )


def language_label(code: str | None) -> str | None:
    if not code:
        return None
    try:
        from lingua import IsoCode639_1, Language

        return Language.from_iso_code_639_1(IsoCode639_1.from_str(code.upper())).name.title()
    except (ImportError, KeyError, ValueError):
        return None
