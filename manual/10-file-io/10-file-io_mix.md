# Chapter 10 — File input/output (Mixed profile)

> Visual Quar 0.0.4 beta · profile: `mixed` · documentation draft

## Scope

File handling, bytes and resource operations.

## Profile semantics

The mixed profile permits a combination of explicit typed declarations and inferred local bindings where implemented.

Examples below are taken from the uploaded repository; coverage differs by source profile and backend.

## Source example

**Evidence:** `NOT DEMONSTRATED` for this profile and chapter in the uploaded `.vq` examples.

No syntax sample is asserted here: using a typed-profile example as if it were verified in this profile would be misleading.

Related typed-profile reference: `examples/0.0.4/typed/10 file io/171 text round trip.vq`.

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
