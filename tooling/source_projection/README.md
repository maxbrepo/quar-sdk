# Visual Quar Source Projection

Editor-independent source representation service for Visual Quar 0.0.3.

The service keeps one canonical Visual Quar representation and exposes explicit
source profiles for preview and export. It does not write files and it does not
depend on QEdit.

Current 0.0.3 scope:

- canonical Visual Quar vocabulary;
- English, Italian and Spanish source profiles;
- compact/canonical and extended vocabulary views;
- normalization through one canonical representation;
- preview/projection without source mutation;
- conversion result suitable for export to a new file or directory;
- string, char and comment contents preserved;
- legacy numeric aliases normalized to canonical fixed-width types.

Deliberately not implemented yet:

- automatic profile detection;
- automatic identifier translation (Naming Easy);
- automatic comment translation (Comments Easy);
- direct file writes;
- QEdit-specific UI or state.

Clients such as QEdit, Vim or Geany should own file handling and UI. They can
use this package only for deterministic source transformation.

## Easy vocabulary experiment

The 0.0.3 experiment includes an editor-independent Easy Vocabulary Engine for English, Italian and Spanish.

- Capacity target: 5,000 canonical concepts.
- Initial seed: 200+ programming-oriented concepts.
- Identifiers preserve snake_case, camelCase and PascalCase where possible.
- Unknown identifier parts remain unchanged.
- Comments use conservative word-level translation; unknown prose remains unchanged.
- String and character literals are never translated.
- `naming_easy` and `comments_easy` are independent profile switches.

The vocabulary engine is intentionally separate from QEdit. Any editor or tool can consume the same API.

## Unicode and language packs

Source Projection uses UTF-8 data and NFC Unicode normalization. English, Italian,
and Spanish are the initial built-in language packs. The engine API is independent
from QEdit so other editors can consume the same service.

The vocabulary capacity target is 5000 canonical concepts. Vocabulary growth is a
data task and does not require changes to the projection API.
