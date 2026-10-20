# Chapter 12 — Error handling (Inferred profile)

> Visual Quar 0.0.4 beta · profile: `inferred` · documentation draft

## Scope

Error propagation, chaining, assertions and panic.

## Profile semantics

Local variables can be introduced by assignment when the selected profile permits inference. This does not mean that every declaration, function signature or advanced type can omit annotations.

Examples below are taken from the uploaded repository; coverage differs by source profile and backend.

## Source example

**Evidence:** `NOT DEMONSTRATED` for this profile and chapter in the uploaded `.vq` examples.

No syntax sample is asserted here: using a typed-profile example as if it were verified in this profile would be misleading.

Related typed-profile reference: `examples/0.0.4/typed/12 error handling/221 assertion success.vq`.

## Compatibility and verification

- The example is a repository artifact, not a claim that it was executed during manual generation.
- QRVM behavior and C backend support may differ.
- Use the project regression runner and the selected profile to confirm current behavior before treating a construct as stable.

## Historically documented features

- 12A: `try/catch`, `throw` e campo `error.message`.
- 12B: `throw ... from error` e catena in `error.cause`.
- 12C: `assert(bool)` e `error.trace` con nomi delle funzioni.
- 12D: `panic(string)` fatale, non intercettabile da `catch`, distinto da `exit`.
- `with` deve liberare le risorse durante l’unwinding; nessun recovery generale da panic.

These are historical documentation claims, not individually revalidated here.

## Open specification questions

- Which exact grammar forms and diagnostics are guaranteed for this profile?
- Which execution routes have been independently regression-tested?
- Are there profile-specific restrictions not yet reflected in the example corpus?
