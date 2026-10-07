import unittest

from tooling.source_projection.easy_vocabulary import (
    EASY_VOCABULARY,
    EASY_VOCABULARY_CAPACITY,
    TranslationConfidence,
    translate_comment,
    translate_identifier,
)
from tooling.source_projection.profiles import SourceLanguage, SourceProfile, VocabularyStyle
from tooling.source_projection.transformer import project_source


class EasyVocabularyTests(unittest.TestCase):
    def test_capacity_and_seed(self):
        self.assertEqual(EASY_VOCABULARY_CAPACITY, 5000)
        self.assertGreaterEqual(len(EASY_VOCABULARY), 200)

    def test_snake_identifier(self):
        result = translate_identifier("user_count", SourceLanguage.ENGLISH, SourceLanguage.ITALIAN)
        self.assertEqual(result.text, "utente_conteggio")
        self.assertEqual(result.confidence, TranslationConfidence.COMPOSED)

    def test_camel_identifier(self):
        result = translate_identifier("filePath", SourceLanguage.ENGLISH, SourceLanguage.SPANISH)
        self.assertEqual(result.text, "archivoRuta")

    def test_unknown_identifier_is_preserved(self):
        result = translate_identifier("userMagic", SourceLanguage.ENGLISH, SourceLanguage.ITALIAN)
        self.assertIn("utente", result.text.lower())
        self.assertEqual(result.confidence, TranslationConfidence.PARTIAL)

    def test_comment_translation(self):
        result = translate_comment("Load user data and return result", SourceLanguage.ENGLISH, SourceLanguage.ITALIAN)
        self.assertEqual(result.text, "Carica utente dati e ritorna risultato")

    def test_projection_easy_modes(self):
        source = 'i32 user_count = 2; // Check user count\nprint("user_count");\n'
        en = SourceProfile(language=SourceLanguage.ENGLISH, vocabulary=VocabularyStyle.CANONICAL)
        it = SourceProfile(
            language=SourceLanguage.ITALIAN,
            vocabulary=VocabularyStyle.EXTENDED,
            naming_easy=True,
            comments_easy=True,
        )
        result = project_source(source, en, it).text
        self.assertIn("intero utente_conteggio", result)
        self.assertIn("// Controlla utente conteggio", result)
        self.assertIn('"user_count"', result)


if __name__ == "__main__":
    unittest.main()


def test_unicode_nfc_identifier_translation():
    from tooling.source_projection import normalize_unicode, translate_identifier
    decomposed = "modalita\u0300"
    assert normalize_unicode(decomposed) == "modalità"


def test_language_pack_metadata():
    from tooling.source_projection import get_language_pack
    assert get_language_pack("es").native_name == "Español"
    assert get_language_pack("it").normalization == "NFC"


def test_unicode_comment_translation():
    from tooling.source_projection import translate_comment, SourceLanguage
    result = translate_comment("Código usuario", SourceLanguage.SPANISH, SourceLanguage.ITALIAN)
    assert "Codice" in result.text
    assert "utente" in result.text
