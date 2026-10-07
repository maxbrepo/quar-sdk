from dataclasses import dataclass

from .easy_vocabulary import TranslationConfidence, translate_comment, translate_identifier


@dataclass(frozen=True)
class CoverageStats:
    exact: int = 0
    composed: int = 0
    partial: int = 0
    unknown: int = 0

    @property
    def total(self):
        return self.exact + self.composed + self.partial + self.unknown

    @property
    def covered(self):
        return self.exact + self.composed + self.partial

    @property
    def ratio(self):
        return 1.0 if self.total == 0 else self.covered / self.total


def measure_identifiers(identifiers, source_language, target_language):
    counts = {confidence: 0 for confidence in TranslationConfidence}
    for identifier in identifiers:
        result = translate_identifier(identifier, source_language, target_language)
        counts[result.confidence] += 1
    return CoverageStats(
        exact=counts[TranslationConfidence.EXACT],
        composed=counts[TranslationConfidence.COMPOSED],
        partial=counts[TranslationConfidence.PARTIAL],
        unknown=counts[TranslationConfidence.UNKNOWN],
    )
