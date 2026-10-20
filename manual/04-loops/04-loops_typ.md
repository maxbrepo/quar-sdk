# Chapter 04 — Loops and iteration (Typed profile)

> Visual Quar 0.0.4 beta · profile: `typed` · documentation draft

## Scope

Loops, break, continue and counter-based iteration.

## Profile semantics

The typed profile favors explicit declarations and predictable type checking. Familiar aliases such as `int` coexist with more specialized numeric types; the exact supported widths and constraints must be checked against the compiler.

Examples below are taken from the uploaded repository; coverage differs by source profile and backend.

## Source example

**Evidence:** `EXAMPLE PRESENT`

Exact source: `examples/0.0.3/typed/04 loops/086 automatic ascending for.vq`

```vq
i32 i = 0;
for (i = 1; i <= 5) {
    print(i);
}
```

## Compatibility and verification

- The example is a repository artifact, not a claim that it was executed during manual generation.
- QRVM behavior and C backend support may differ.
- Use the project regression runner and the selected profile to confirm current behavior before treating a construct as stable.

## Historically documented features

- `while`, `do while` e `loop` esplicito.
- `for` ascendente e discendente, con direzione automatica o esplicita.
- `break` e `continue`.
- Diagnostici per direzione incoerente e alcuni cicli infiniti.
- Truthiness numerica nei cicli.

These are historical documentation claims, not individually revalidated here.

## Open specification questions

- Which exact grammar forms and diagnostics are guaranteed for this profile?
- Which execution routes have been independently regression-tested?
- Are there profile-specific restrictions not yet reflected in the example corpus?
