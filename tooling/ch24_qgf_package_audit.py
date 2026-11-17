"""Static release audit for the optional Chapter 24 QGF/SDL package.

This tool reads ZIP members without executing packaged Python. It checks the
presence of required files, the public symbols consumed by tests, and SHA-256
checksums of payload files. It is not an SDL ABI compatibility test.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import sys
import zipfile


REQUIRED_FILES = (
    'bindings/__init__.py',
    'bindings/sdl2_events.py',
    'qrvm/native_abi_contract.py',
    'fixtures/qgf_ffi_abi_contract.c',
    'fixtures/qgf_ffi_keyboard_event.c',
    'tests/test_ch24_34_sdl_external_binding.py',
    'tests/test_ch24_35_sdl_header_runtime_contract.py',
    'tests/test_ch24_36_typed_keyboard_events.py',
    'tests/test_ch24_38_external_event_poller.py',
    'tests/test_ch24_39_source_typed_event.py',
    'tests/test_ch24_40_qgf_package_audit.py',
    'tooling/ch24_qgf_package_audit.py',
    'examples/0.0.5/typed/24_interoperability/24_14_sdl_visible_window.vq.native.json',
)

REQUIRED_EXPORTS = {
    'bindings/sdl2_events.py': (
        'SDLEventSnapshot', 'SDLKeyboardSnapshot', 'SDLEventPoller',
        'decode_sdl_event', 'decode_sdl_keyboard_event',
    ),
    'qrvm/native_abi_contract.py': (
        'NativeABIContractError', 'NativeOutputABIContract',
    ),
}


class ReleaseAuditError(ValueError):
    """An archive cannot be considered self-contained at the patch level."""


def audit_archive(path: str | Path) -> tuple[int, str]:
    """Inspect an incremental ZIP without executing its contents.

    Returns the number of validated payload files and their SHA-256 digest.
    Raises ReleaseAuditError with the relevant missing file or symbol.
    """
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ReleaseAuditError('Duplicate ZIP member names')
        if any(name.startswith('/') or '..' in Path(name).parts for name in names):
            raise ReleaseAuditError('Unsafe ZIP path')
        for required in REQUIRED_FILES:
            if required not in names:
                raise ReleaseAuditError('Missing package dependency: ' + required)
        for filename, symbols in REQUIRED_EXPORTS.items():
            module = ast.parse(archive.read(filename), filename=filename)
            exports = {
                node.name for node in module.body
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            }
            for symbol in symbols:
                if symbol not in exports:
                    raise ReleaseAuditError(f'Missing exported symbol: {filename}:{symbol}')
        manifest_name = 'SHA256SUMS_24_40.txt'
        if manifest_name not in names:
            raise ReleaseAuditError('Missing SHA-256 manifest')
        lines = archive.read(manifest_name).decode('utf-8').splitlines()
        expected = {}
        for line in lines:
            digest, separator, filename = line.partition('  ')
            if not separator or filename in expected or len(digest) != 64:
                raise ReleaseAuditError('Invalid or duplicate manifest entry')
            expected[filename] = digest
        payload = {name for name in names if not name.endswith('/') and name != manifest_name}
        if set(expected) != payload:
            raise ReleaseAuditError('Manifest payload mismatch')
        for filename, digest in expected.items():
            if hashlib.sha256(archive.read(filename)).hexdigest() != digest:
                raise ReleaseAuditError('SHA-256 mismatch: ' + filename)
        combined = hashlib.sha256(archive.read(manifest_name)).hexdigest()
        return len(payload), combined


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python -m tooling.ch24_qgf_package_audit PACKAGE.zip')
    try:
        count, checksum = audit_archive(sys.argv[1])
    except (ReleaseAuditError, OSError, zipfile.BadZipFile) as error:
        print(f'FAIL: {error}')
        raise SystemExit(1) from error
    print(f'PASS: {count} payload files, SHA-256 verified; manifest={checksum}')
