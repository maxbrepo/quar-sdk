# Chapter 13 — Modules and imports (Typed profile)

> Visual Quar 0.0.4 beta · profile: `typed` · documentation draft

## Scope

Module loading, imports, aliases and qualified calls.

## Profile semantics

The typed profile favors explicit declarations and predictable type checking. Familiar aliases such as `int` coexist with more specialized numeric types; the exact supported widths and constraints must be checked against the compiler.

Imports are demonstrated in typed module examples; module availability and dependency resolution are distinct concerns.

## Source example

**Evidence:** `EXAMPLE PRESENT`

Exact source: `examples/0.0.4/typed/13 modules/238 module internal call/main.vq`

```vq
import math;
print(math.twice(21));
```

## Compatibility and verification

- The example is a repository artifact, not a claim that it was executed during manual generation.
- QRVM behavior and C backend support may differ.
- Use the project regression runner and the selected profile to confirm current behavior before treating a construct as stable.

## Open specification questions

- Which exact grammar forms and diagnostics are guaranteed for this profile?
- Which execution routes have been independently regression-tested?
- Are there profile-specific restrictions not yet reflected in the example corpus?
