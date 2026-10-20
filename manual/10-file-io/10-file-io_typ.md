# Chapter 10 — File input/output (Typed profile)

> Visual Quar 0.0.4 beta · profile: `typed` · documentation draft

## Scope

File handling, bytes and resource operations.

## Profile semantics

The typed profile favors explicit declarations and predictable type checking. Familiar aliases such as `int` coexist with more specialized numeric types; the exact supported widths and constraints must be checked against the compiler.

Examples below are taken from the uploaded repository; coverage differs by source profile and backend.

## Source example

**Evidence:** `EXAMPLE PRESENT`

Exact source: `examples/0.0.4/typed/10 file io/171 text round trip.vq`

```vq
File.write_text("note.txt", "hello"); print(File.read_text("note.txt"));
```

## Compatibility and verification

- The example is a repository artifact, not a claim that it was executed during manual generation.
- QRVM behavior and C backend support may differ.
- Use the project regression runner and the selected profile to confirm current behavior before treating a construct as stable.

## Historically documented features

- Lettura, scrittura e append di testo UTF-8 e bytes binari.
- `bytes` distinto da `string`, conversioni hex esplicite, indicizzazione, confronto e lunghezza.
- Directory listing e operazioni sui percorsi.
- `with File.open(..., mode)` con chiusura automatica su uscita normale, errore e return, inclusi blocchi annidati.
- Scritture atomiche opt-in con file temporaneo, flush, fsync e replace, con limiti espliciti.
- Classificazione degli errori I/O: not_found e invalid_data.

These are historical documentation claims, not individually revalidated here.

## Open specification questions

- Which exact grammar forms and diagnostics are guaranteed for this profile?
- Which execution routes have been independently regression-tested?
- Are there profile-specific restrictions not yet reflected in the example corpus?
