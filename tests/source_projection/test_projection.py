import unittest

from tooling.source_projection import (
    SourceLanguage,
    SourceProfile,
    VocabularyStyle,
    normalize_source,
    project_source,
)


class SourceProjectionTests(unittest.TestCase):
    def test_italian_extended_projection(self):
        source = 'i32 count = 2; if (count) { return count; }'
        profile = SourceProfile(
            SourceLanguage.ITALIAN,
            VocabularyStyle.EXTENDED,
        )
        result = project_source(
            source,
            SourceProfile(),
            profile,
        )
        self.assertEqual(
            result.text,
            'intero count = 2; se (count) { ritorna count; }',
        )

    def test_round_trip_through_canonical(self):
        source = 'intero valore = 3; se (vero) { ritorna valore; }'
        profile = SourceProfile(
            SourceLanguage.ITALIAN,
            VocabularyStyle.EXTENDED,
        )
        canonical, _ = normalize_source(source, profile)
        self.assertEqual(
            canonical,
            'i32 valore = 3; if (true) { return valore; }',
        )

    def test_strings_and_comments_are_preserved(self):
        source = 'string text = "se intero"; // se intero\ni32 value = 1;'
        profile = SourceProfile(
            SourceLanguage.ITALIAN,
            VocabularyStyle.EXTENDED,
        )
        result = project_source(source, SourceProfile(), profile)
        self.assertIn('"se intero"', result.text)
        self.assertIn('// se intero', result.text)
        self.assertIn('intero value = 1;', result.text)

    def test_legacy_alias_normalizes(self):
        canonical, _ = normalize_source('int value = 1;', SourceProfile())
        self.assertEqual(canonical, 'i32 value = 1;')


if __name__ == "__main__":
    unittest.main()
