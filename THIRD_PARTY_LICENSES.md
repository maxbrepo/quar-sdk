# Third-Party Licenses

This document is a **preliminary licensing inventory** for the Quar SDK ecosystem. It is not a completed dependency audit. The entries below describe technologies mentioned in the project documentation or development plans; they do **not** establish that each component is bundled with this repository or redistributed in release artifacts.

The project’s original source code is covered by the root `LICENSE` file unless otherwise indicated. Third-party software retains its own copyright and license terms.

## Known and potential external components

| Component | License family | Role / distribution status |
| --- | --- | --- |
| Python (CPython) | Python Software Foundation License | Reference implementation and bootstrap tooling; verify whether an interpreter is redistributed. |
| GTK | LGPL-2.1-or-later (GTK library; check exact installed version) | Quar Edit GUI dependency; verify dynamic linking and packaging. |
| PyGObject | LGPL-2.1-or-later (check exact package/version) | Python bindings for GTK; verify exact package and redistribution. |
| GCC | GPL-3.0-or-later for GCC compiler components, with separately licensed runtime libraries and relevant exceptions | External C toolchain; invoking GCC does not itself relicense generated programs. |
| LLVM / Clang | Apache-2.0 WITH LLVM-exception (modern LLVM releases; check version) | Possible external C compiler; verify actual use and packaging. |
| SDL3 | zlib | Used/planned in the separate Quar Game Framework (QGF) ecosystem; **not confirmed as a dependency of this SDK repository**. |

## Before public distribution

1. Inventory actual dependencies from manifests, imports, build scripts, vendored sources, binaries, and release archives.
2. Record exact component versions, copyright notices, license identifiers, and whether each component is invoked externally, dynamically linked, statically linked, embedded, or redistributed.
3. Include complete third-party license texts and notices where required by the relevant licenses and distribution method. This summary does not replace those obligations.
4. Review generated C/native outputs for embedded runtime code and any licensing exceptions required for unrestricted distribution of user programs.
5. Verify the rights and provenance of all third-party contributions, assets, and copied code before publication.

No claim of a complete legal compliance audit is made by this file.
