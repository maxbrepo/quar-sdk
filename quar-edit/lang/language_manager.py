from collections.abc import Callable

from lang import eng, ita, spa, por, jpn, zho_hans, zho_hant, kor, hin, fra, ara, rus, deu, tur, ind, vie, pol, ben, tha, fas, urd, ukr, nld, ell, ces, ron

LanguageCallback = Callable[[], None]

class LanguageManager:
    """Manage Quar Edit interface languages and localized strings."""

    def __init__(self) -> None:
        self._languages: dict[str, dict[str, str]] = {
            "eng": eng.STRINGS,
            "ita": ita.STRINGS,
            "spa": spa.STRINGS,
            "por": por.STRINGS,
            "jpn": jpn.STRINGS,
            "zho_hans": zho_hans.STRINGS,
            "zho_hant": zho_hant.STRINGS,
            "kor": kor.STRINGS,
            "hin": hin.STRINGS,
            "fra": fra.STRINGS,
            "ara": ara.STRINGS,
            "rus": rus.STRINGS,
            "deu": deu.STRINGS,
            "tur": tur.STRINGS,
            "ind": ind.STRINGS,
            "vie": vie.STRINGS,
            "pol": pol.STRINGS,
            "ben": ben.STRINGS,
            "tha": tha.STRINGS,
            "fas": fas.STRINGS,
            "urd": urd.STRINGS,
            "ukr": ukr.STRINGS,
            "nld": nld.STRINGS,
            "ell": ell.STRINGS,
            "ces": ces.STRINGS,
            "ron": ron.STRINGS,
        }
        self._current_language = "eng"
        self._callbacks: list[LanguageCallback] = []

    def get_string(self, key: str) -> str:
        """Return a localized string with English as the fallback."""
        current_strings = self._languages[self._current_language]
        if key in current_strings:
            return current_strings[key]
        return eng.STRINGS.get(key, key)

    def set_language(self, language_code: str) -> bool:
        """Change language and return True when a change occurred."""
        if language_code not in self._languages or language_code == self._current_language:
            return False
        self._current_language = language_code
        for callback in self._callbacks.copy():
            callback()
        return True

    def get_language(self) -> str:
        return self._current_language

    def has_language(self, language_code: str) -> bool:
        return language_code in self._languages

    def get_available_languages(self) -> tuple[str, ...]:
        return tuple(self._languages.keys())

    def register_callback(self, callback: LanguageCallback) -> None:
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(self, callback: LanguageCallback) -> None:
        if callback in self._callbacks:
            self._callbacks.remove(callback)

language_manager = LanguageManager()

def get_string(key: str) -> str:
    return language_manager.get_string(key)
