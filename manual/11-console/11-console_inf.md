# Chapter 11 — Console and environment (Inferred profile)

> Visual Quar 0.0.4 beta · profile: `inferred` · documentation draft

## Scope

Console input/output, streams and environment operations.

## Profile semantics

Local variables can be introduced by assignment when the selected profile permits inference. This does not mean that every declaration, function signature or advanced type can omit annotations.

Examples below are taken from the uploaded repository; coverage differs by source profile and backend.

## Source example

**Evidence:** `NOT DEMONSTRATED` for this profile and chapter in the uploaded `.vq` examples.

No syntax sample is asserted here: using a typed-profile example as if it were verified in this profile would be misleading.

Related typed-profile reference: `examples/0.0.4/typed/11 console/194 stdout and print.vq`.

## Compatibility and verification

- The example is a repository artifact, not a claim that it was executed during manual generation.
- QRVM behavior and C backend support may differ.
- Use the project regression runner and the selected profile to confirm current behavior before treating a construct as stable.

## Historically documented features

- 11A: `print` e `input()` con prompt opzionale, conversioni successive `to_int` e `to_double`.
- 11B: `stdout`, `stderr` e `exit` con codice intero 0–255.
- 11C: `Console.arg_count`, `Console.arg`, `Console.env`, `Console.env_exists`.
- Input, argomenti ed environment possono essere forniti come fixture deterministiche nel runner.

These are historical documentation claims, not individually revalidated here.

## Open specification questions

- Which exact grammar forms and diagnostics are guaranteed for this profile?
- Which execution routes have been independently regression-tested?
- Are there profile-specific restrictions not yet reflected in the example corpus?
