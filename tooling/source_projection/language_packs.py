from dataclasses import dataclass

from .profiles import SourceLanguage
from .languages import LANGUAGES


@dataclass(frozen=True)
class LanguagePackInfo:
    code: str
    name: str
    native_name: str
    encoding: str = "UTF-8"
    normalization: str = "NFC"


LANGUAGE_PACKS = {
    code: LanguagePackInfo(code, module.NAME, module.NATIVE_NAME)
    for code, module in LANGUAGES.items()
}


def get_language_pack(language):
    code = language.value if isinstance(language, SourceLanguage) else str(language)
    return LANGUAGE_PACKS[code]
