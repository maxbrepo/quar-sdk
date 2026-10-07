from dataclasses import asdict, dataclass
from enum import Enum


class SourceLanguage(str, Enum):
    ENGLISH = "en"
    ITALIAN = "it"
    SPANISH = "es"
    PORTUGUESE = "pt"
    JAPANESE = "ja"
    CHINESE_SIMPLIFIED = "zh-hans"
    CHINESE_TRADITIONAL = "zh-hant"
    KOREAN = "ko"
    HINDI = "hi"
    FRENCH = "fr"
    ARABIC = "ar"
    RUSSIAN = "ru"
    GERMAN = "de"
    TURKISH = "tr"
    INDONESIAN = "id"
    VIETNAMESE = "vi"
    POLISH = "pl"
    BENGALI = "bn"
    THAI = "th"
    PERSIAN = "fa"
    URDU = "ur"
    UKRAINIAN = "uk"
    DUTCH = "nl"
    GREEK = "el"
    CZECH = "cs"
    ROMANIAN = "ro"

class VocabularyStyle(str, Enum):
    CANONICAL = "canonical"
    EXTENDED = "extended"


class TypingMode(str, Enum):
    EXPLICIT = "explicit"
    INFERRED = "inferred"
    MIXED = "mixed"


@dataclass(frozen=True)
class SourceProfile:
    language: SourceLanguage = SourceLanguage.ENGLISH
    vocabulary: VocabularyStyle = VocabularyStyle.CANONICAL
    language_version: str = "0.0.3"
    typing: TypingMode = TypingMode.EXPLICIT
    compatibility_level: str = "0.0.3"
    naming_easy: bool = False
    comments_easy: bool = False

    def to_dict(self):
        data = asdict(self)
        data["language"] = self.language.value
        data["vocabulary"] = self.vocabulary.value
        data["typing"] = self.typing.value
        return data

    @classmethod
    def from_dict(cls, data):
        return cls(
            language=SourceLanguage(data.get("language", "en")),
            vocabulary=VocabularyStyle(data.get("vocabulary", "canonical")),
            language_version=data.get("language_version", "0.0.3"),
            typing=TypingMode(data.get("typing", "explicit")),
            compatibility_level=data.get("compatibility_level", "0.0.3"),
            naming_easy=bool(data.get("naming_easy", False)),
            comments_easy=bool(data.get("comments_easy", False)),
        )


CANONICAL_PROFILE = SourceProfile()
