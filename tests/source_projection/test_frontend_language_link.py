import unittest

from main import build_frontend
from tooling.source_projection import (
    SourceLanguage,
    SourceProfile,
    VocabularyStyle,
)


class FrontendLanguageLinkTests(unittest.TestCase):
    def test_canonical_source_still_builds(self):
        program, variables = build_frontend("i32 value = 5;")
        self.assertIsNotNone(program)
        self.assertIn("value", variables)

    def test_italian_extended_source_reaches_frontend(self):
        profile = SourceProfile(
            language=SourceLanguage.ITALIAN,
            vocabulary=VocabularyStyle.EXTENDED,
        )
        program, variables = build_frontend(
            "intero numero = 5;",
            profile,
        )
        self.assertIsNotNone(program)
        self.assertIn("numero", variables)

    def test_spanish_extended_source_reaches_frontend(self):
        profile = SourceProfile(
            language=SourceLanguage.SPANISH,
            vocabulary=VocabularyStyle.EXTENDED,
        )
        program, variables = build_frontend(
            "entero numero = 5;",
            profile,
        )
        self.assertIsNotNone(program)
        self.assertIn("numero", variables)


if __name__ == "__main__":
    unittest.main()
