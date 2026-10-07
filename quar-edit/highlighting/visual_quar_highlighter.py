from __future__ import annotations

from dataclasses import dataclass
import re

from tooling.source_projection.vocabularies import (
    CANONICAL_BUILTINS,
    CANONICAL_WORDS,
    LEGACY_ALIASES,
    display_builtin,
    display_word,
)


@dataclass(frozen=True)
class HighlightSpan:
    start: int
    end: int
    category: str


TYPE_WORDS = {
    "i8", "i16", "i32", "i64", "i128",
    "u8", "u16", "u32", "u64", "u128",
    "f32", "f64", "bool", "char", "string", "void", "tuple",
}
LITERAL_WORDS = {"true", "false"}


def _display_sets(profile):
    types = {display_word(word, profile) for word in TYPE_WORDS}
    # Legacy type spellings such as int, float, double and short are
    # accepted by the Visual Quar frontend and must therefore be
    # highlighted as types when they appear in the actual source.
    types.update(
        alias
        for alias, canonical in LEGACY_ALIASES.items()
        if canonical in TYPE_WORDS
    )
    literals = {display_word(word, profile) for word in LITERAL_WORDS}
    keywords = {
        display_word(word, profile)
        for word in CANONICAL_WORDS
        if word not in TYPE_WORDS and word not in LITERAL_WORDS
    }
    builtins = {display_builtin(word, profile) for word in CANONICAL_BUILTINS}
    return keywords, types, builtins, literals


def classify_visual_quar(text: str, profile) -> list[HighlightSpan]:
    """Classify code tokens while excluding strings, chars and comments."""
    keywords, types, builtins, literals = _display_sets(profile)
    spans: list[HighlightSpan] = []
    i = 0
    state = "code"

    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if state == "code":
            if ch == '"':
                state = "string"
                i += 1
                continue
            if ch == "'":
                state = "char"
                i += 1
                continue
            if ch == "/" and nxt == "/":
                state = "line_comment"
                i += 2
                continue
            if ch == "/" and nxt == "*":
                state = "block_comment"
                i += 2
                continue
            if ch.isalpha() or ch == "_":
                start = i
                i += 1
                while i < len(text) and (text[i].isalnum() or text[i] == "_"):
                    i += 1
                word = text[start:i]
                category = None
                if word in types:
                    category = "type"
                elif word in literals:
                    category = "literal"
                elif word in keywords:
                    category = "keyword"
                elif word in builtins:
                    category = "builtin"
                if category:
                    spans.append(HighlightSpan(start, i, category))
                continue

        elif state in ("string", "char"):
            if ch == "\\":
                i += 2
                continue
            if (state == "string" and ch == '"') or (state == "char" and ch == "'"):
                state = "code"
            i += 1
            continue

        elif state == "line_comment":
            if ch == "\n":
                state = "code"
            i += 1
            continue

        elif state == "block_comment":
            if ch == "*" and nxt == "/":
                state = "code"
                i += 2
                continue
            i += 1
            continue

        i += 1

    return spans


PALETTES = {
    "classic": {
        "keyword": "#a64ca6",
        "type": "#2f7fbf",
        "builtin": "#d26a2e",
        "literal": "#2c9a63",
    },
    "high-contrast": {
        "keyword": "#ff00ff",
        "type": "#00a8ff",
        "builtin": "#ff7a00",
        "literal": "#00c853",
    },
}


def clear_visual_quar_highlighting(buffer) -> None:
    """Remove only Visual Quar highlighting tags from the buffer."""
    start = buffer.get_start_iter()
    end = buffer.get_end_iter()
    table = buffer.get_tag_table()
    for category in ("keyword", "type", "builtin", "literal"):
        tag = table.lookup(f"vq-{category}")
        if tag is not None:
            buffer.remove_tag(tag, start, end)


def apply_visual_quar_highlighting(buffer, profile, palette_name: str = "classic") -> None:
    """Apply color-only Visual Quar highlighting without changing layout metrics."""
    palette = PALETTES.get(palette_name, PALETTES["classic"])
    start = buffer.get_start_iter()
    end = buffer.get_end_iter()
    table = buffer.get_tag_table()
    tags = {}
    for category, color in palette.items():
        name = f"vq-{category}"
        tag = table.lookup(name)
        if tag is None:
            tag = buffer.create_tag(name)
        tag.set_property("foreground", color)
        tags[category] = tag
        buffer.remove_tag(tag, start, end)
    source = buffer.get_text(start, end, True)
    for span in classify_visual_quar(source, profile):
        buffer.apply_tag(
            tags[span.category],
            buffer.get_iter_at_offset(span.start),
            buffer.get_iter_at_offset(span.end),
        )
