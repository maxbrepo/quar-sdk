from dataclasses import dataclass

from .easy_vocabulary import translate_comment, translate_identifier
from .profiles import CANONICAL_PROFILE, SourceProfile
from .vocabularies import CANONICAL_BUILTINS, CANONICAL_WORDS, display_builtin, display_word, input_map


@dataclass(frozen=True)
class ProjectionResult:
    text: str
    source_profile: SourceProfile
    target_profile: SourceProfile
    replacements: int


def _transform_source(source, word_replacements, source_profile, target_profile):
    output = []
    index = 0
    changed = 0
    state = "code"
    comment_buffer = []

    def flush_comment():
        nonlocal changed
        text = "".join(comment_buffer)
        comment_buffer.clear()
        if target_profile.comments_easy:
            result = translate_comment(text, source_profile.language, target_profile.language)
            changed += result.translated_parts
            output.append(result.text)
        else:
            output.append(text)

    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""

        if state == "code":
            if char == '"':
                state = "string"
                output.append(char)
                index += 1
                continue
            if char == "'":
                state = "char"
                output.append(char)
                index += 1
                continue
            if char == "/" and next_char == "/":
                state = "line_comment"
                output.extend((char, next_char))
                index += 2
                continue
            if char == "/" and next_char == "*":
                state = "block_comment"
                output.extend((char, next_char))
                index += 2
                continue
            if char.isalpha() or char == "_":
                start = index
                index += 1
                while index < len(source) and (source[index].isalnum() or source[index] == "_"):
                    index += 1
                word = source[start:index]
                replacement = word_replacements.get(word)
                if replacement is None and target_profile.naming_easy:
                    result = translate_identifier(word, source_profile.language, target_profile.language)
                    replacement = result.text
                if replacement is None:
                    replacement = word
                changed += int(replacement != word)
                output.append(replacement)
                continue

        elif state in ("string", "char"):
            output.append(char)
            index += 1
            if char == "\\" and index < len(source):
                output.append(source[index])
                index += 1
                continue
            if state == "string" and char == '"':
                state = "code"
            elif state == "char" and char == "'":
                state = "code"
            continue

        elif state == "line_comment":
            if char == "\n":
                flush_comment()
                output.append(char)
                state = "code"
            else:
                comment_buffer.append(char)
            index += 1
            continue

        elif state == "block_comment":
            if char == "*" and next_char == "/":
                flush_comment()
                output.extend((char, next_char))
                index += 2
                state = "code"
            else:
                comment_buffer.append(char)
                index += 1
            continue

        output.append(char)
        index += 1

    if comment_buffer:
        flush_comment()
    return "".join(output), changed


def normalize_source(source, source_profile=CANONICAL_PROFILE):
    """Normalize one explicit source profile to canonical Visual Quar."""
    canonical_profile = SourceProfile(
        language=SourceProfile().language,
        vocabulary=SourceProfile().vocabulary,
        language_version=source_profile.language_version,
        typing=source_profile.typing,
        compatibility_level=source_profile.compatibility_level,
        naming_easy=source_profile.naming_easy,
        comments_easy=source_profile.comments_easy,
    )
    return _transform_source(source, input_map(source_profile), source_profile, canonical_profile)


def project_source(source, source_profile, target_profile):
    """Project source through canonical Visual Quar without file writes."""
    canonical, first_count = normalize_source(source, source_profile)
    replacements = {word: display_word(word, target_profile) for word in CANONICAL_WORDS}
    replacements.update(
        {word: display_builtin(word, target_profile) for word in CANONICAL_BUILTINS}
    )
    canonical_profile = SourceProfile(
        language=SourceProfile().language,
        vocabulary=SourceProfile().vocabulary,
        language_version=source_profile.language_version,
        typing=source_profile.typing,
        compatibility_level=source_profile.compatibility_level,
        naming_easy=source_profile.naming_easy,
        comments_easy=source_profile.comments_easy,
    )
    projected, second_count = _transform_source(
        canonical, replacements, canonical_profile, target_profile
    )
    return ProjectionResult(projected, source_profile, target_profile, first_count + second_count)


def convert_source(source, source_profile, target_profile):
    """Return converted source text for explicit export by a client."""
    return project_source(source, source_profile, target_profile)
