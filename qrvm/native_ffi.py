"""Experimental typed C-ABI bridge for the QRVM bootstrap.

This is an internal adapter, not yet a Visual Quar language feature.
Only explicit scalar signatures are accepted. Native libraries are trusted code.
"""

from __future__ import annotations

import ctypes
from contextlib import contextmanager
from dataclasses import dataclass
from itertools import count
from pathlib import Path

from qrvm.native_struct_layout import NativeStructLayout
from qrvm.native_composite_layout import NativeCompositeLayout


class NativeFFIError(RuntimeError):
    """Report a rejected signature, argument, library, or symbol."""


_TYPES = {
    "i32": (ctypes.c_int32, -(2 ** 31), 2 ** 31 - 1),
    "u32": (ctypes.c_uint32, 0, 2 ** 32 - 1),
    "i64": (ctypes.c_int64, -(2 ** 63), 2 ** 63 - 1),
    "u64": (ctypes.c_uint64, 0, 2 ** 64 - 1),
    "f32": (ctypes.c_float, None, None),
    "f64": (ctypes.c_double, None, None),
    "opaque": (ctypes.c_void_p, None, None),
    "cstring": (ctypes.c_char_p, None, None),
    "bool": (ctypes.c_bool, None, None),
}


@dataclass(frozen=True)
class OpaqueNativePointer:
    """Non-dereferenceable address returned by a native library.

    The owning library must remain loaded for the lifetime of this handle.
    """

    address: int
    library_identity: int
    token: int = 0


@dataclass(frozen=True)
class NativeStructValue:
    """Explicit field values for a native structure passed by value."""

    layout: NativeStructLayout
    values: tuple[int | float, ...]


@dataclass(frozen=True)
class NativeSignature:
    """Describe one native symbol with explicit ABI-compatible scalar types."""

    symbol: str
    arguments: tuple[str | NativeStructLayout, ...]
    result: str | NativeStructLayout

    def __post_init__(self) -> None:
        if not self.symbol or not self.symbol.isidentifier() or not self.symbol.isascii():
            raise NativeFFIError("Native symbol must be a nonempty ASCII identifier")
        if not isinstance(self.arguments, tuple):
            raise NativeFFIError("Native argument types must be a tuple")
        if any(not isinstance(t, NativeStructLayout) and t not in _TYPES for t in self.arguments) or (not isinstance(self.result, NativeStructLayout) and self.result not in (*tuple(_TYPES), "void")):
            raise NativeFFIError("Unsupported native scalar type")


class NativeLibrary:
    """Load a trusted library and call symbols using explicit signatures."""

    def __init__(self, path: str | Path) -> None:
        # Explicit paths are resolved strictly; bare library names are resolved
        # by the platform dynamic loader (e.g. libSDL3.so.0 on Linux).
        raw = str(path)
        if not raw or "\x00" in raw:
            raise NativeFFIError("Native library name must be nonempty and contain no NUL")
        candidate = Path(raw).expanduser()
        if candidate.is_absolute() or raw.startswith("~") or "/" in raw or "\\" in raw:
            try:
                location = candidate.resolve(strict=True)
            except (OSError, RuntimeError) as exc:
                raise NativeFFIError(f"Native library path not found: {raw}") from exc
            if not location.is_file():
                raise NativeFFIError("Native library path is not a file")
            loader_name = str(location)
        elif raw in (".", ".."):
            raise NativeFFIError("Native library name is not valid")
        else:
            loader_name = raw
        try:
            self._library = ctypes.CDLL(loader_name)
        except OSError as exc:
            raise NativeFFIError(f"Unable to load native library '{raw}': {exc}") from exc
        self._cache: dict[NativeSignature, object] = {}
        self._declared_symbols: dict[str, NativeSignature] = {}
        self._output_symbols: dict[str, NativeStructLayout | NativeCompositeLayout] = {}
        self._identity = id(self)
        self._next_token = count(1)
        self._revoked_tokens: set[int] = set()
        self._issued_handles: dict[int, int] = {}
        self._managed_call_scopes: list[tuple[dict[str, NativeSignature], list[tuple[OpaqueNativePointer, NativeSignature]]]] = []

    def call(self, signature: NativeSignature, *arguments: object) -> object:
        """Validate scalars, call a C symbol, and return its scalar result or None."""
        if not isinstance(signature, NativeSignature):
            raise NativeFFIError("An explicit NativeSignature is required")
        if len(arguments) != len(signature.arguments):
            raise NativeFFIError("Native argument count does not match signature")
        converted = []
        for value, kind in zip(arguments, signature.arguments):
            if isinstance(kind, NativeStructLayout):
                if not isinstance(value, NativeStructValue) or value.layout != kind or len(value.values) != len(kind.fields):
                    raise NativeFFIError("Native struct value does not match declared layout")
                structure = kind.ctypes_type()
                validated = []
                for item, (_, field_kind) in zip(value.values, kind.fields):
                    _, minimum, maximum = _TYPES[field_kind]
                    if field_kind.startswith("f"):
                        if type(item) not in (int, float):
                            raise NativeFFIError("Invalid native struct floating field")
                    elif type(item) is not int or not minimum <= item <= maximum:
                        raise NativeFFIError("Invalid native struct integer field")
                    validated.append(item)
                converted.append(structure(*validated))
                continue
            if kind == "bool":
                if type(value) is not bool:
                    raise NativeFFIError("Native bool argument must be bool")
                converted.append(value)
                continue
            if kind == "cstring":
                if type(value) is not str or "\x00" in value:
                    raise NativeFFIError("C string must be text without embedded NUL")
                converted.append(value.encode("utf-8"))
                continue
            if kind == "opaque":
                if not isinstance(value, OpaqueNativePointer) or value.library_identity != self._identity:
                    raise NativeFFIError("Opaque pointer must originate from this library")
                if value.token in self._revoked_tokens:
                    raise NativeFFIError("Opaque pointer has been released")
                if self._issued_handles.get(value.token) != value.address:
                    raise NativeFFIError("Opaque pointer is not a registered native handle")
                converted.append(value.address)
                continue
            _, minimum, maximum = _TYPES[kind]
            if kind.startswith("f"):
                if type(value) not in (int, float):
                    raise NativeFFIError(f"Argument is not a valid {kind} value")
            elif type(value) is not int or not minimum <= value <= maximum:
                raise NativeFFIError(f"Argument is not a valid {kind} value")
            converted.append(value)
        if signature.symbol in self._output_symbols:
            raise NativeFFIError("Symbol is already bound as an output function")
        previous = self._declared_symbols.get(signature.symbol)
        if previous is not None and previous != signature:
            raise NativeFFIError("Conflicting native signatures for the same symbol")
        function = self._cache.get(signature)
        if function is None:
            try:
                function = getattr(self._library, signature.symbol)
            except AttributeError as exc:
                raise NativeFFIError(f"Native symbol not found: {signature.symbol}") from exc
            function.argtypes = tuple(t.ctypes_type() if isinstance(t, NativeStructLayout) else _TYPES[t][0] for t in signature.arguments)
            function.restype = (signature.result.ctypes_type() if isinstance(signature.result, NativeStructLayout)
                                else None if signature.result == "void" else _TYPES[signature.result][0])
            self._cache[signature] = function
            self._declared_symbols[signature.symbol] = signature
        result = function(*converted)
        if isinstance(signature.result, NativeStructLayout):
            return NativeStructValue(signature.result, tuple(getattr(result, name) for name, _ in signature.result.fields))
        if signature.result == "cstring":
            if result is None:
                raise NativeFFIError("Native function returned a null C string")
            try:
                return result.decode("utf-8", errors="strict")
            except UnicodeDecodeError as exc:
                raise NativeFFIError("Native function returned invalid UTF-8") from exc
        if signature.result == "opaque":
            if result is None:
                raise NativeFFIError("Native function returned a null opaque pointer")
            token = next(self._next_token)
            self._issued_handles[token] = int(result)
            handle = OpaqueNativePointer(int(result), self._identity, token)
            # Only an explicitly selected creator participates in opt-in cleanup.
            if self._managed_call_scopes:
                creators, acquired = self._managed_call_scopes[-1]
                destructor = creators.get(signature.symbol)
                if destructor is not None:
                    acquired.append((handle, destructor))
            return handle
        return None if signature.result == "void" else result

    def release_handle(self, handle: OpaqueNativePointer, release_signature: NativeSignature) -> None:
        """Call a declared C destructor and invalidate this handle's token.

        The caller must supply the correct destructor for the resource. This
        cannot detect native-side frees, aliases returned as new handles, or
        use-after-free performed directly by C code.
        """
        if not isinstance(handle, OpaqueNativePointer) or handle.library_identity != self._identity:
            raise NativeFFIError("Opaque pointer must originate from this library")
        if handle.token in self._revoked_tokens:
            raise NativeFFIError("Opaque pointer has already been released")
        if self._issued_handles.get(handle.token) != handle.address:
            raise NativeFFIError("Opaque pointer is not a registered native handle")
        if release_signature.arguments != ("opaque",) or release_signature.result != "void":
            raise NativeFFIError("Native destructor must have signature (opaque) -> void")
        self.call(release_signature, handle)
        # All issued tokens for this address are aliases of the same native
        # resource. Invalidate them together after a successful destructor.
        # The native library must not recycle the address while it is live.
        for token, address in self._issued_handles.items():
            if address == handle.address:
                self._revoked_tokens.add(token)

    @contextmanager
    def managed_calls(self, creators: dict[str, NativeSignature]):
        """Clean up selected native creators invoked by QRVM or Python.

        Only explicitly mapped creators are tracked. Cleanup is in reverse
        creation order; previously released handles are skipped. This is an
        opt-in Python bridge scope, not Visual Quar automatic ownership.
        """
        if not isinstance(creators, dict) or not creators:
            raise NativeFFIError("Managed native creators must be a nonempty mapping")
        for name, destructor in creators.items():
            if not isinstance(name, str) or not name.isascii() or not name.isidentifier():
                raise NativeFFIError("Invalid managed native creator name")
            if (not isinstance(destructor, NativeSignature)
                    or destructor.arguments != ("opaque",) or destructor.result != "void"):
                raise NativeFFIError("Managed native destructor must have signature (opaque) -> void")
        # A nested scope owns its own acquisitions. A handle belongs to the
        # innermost active scope, preventing duplicate cleanup registrations.
        acquired: list[tuple[OpaqueNativePointer, NativeSignature]] = []
        self._managed_call_scopes.append((dict(creators), acquired))
        body_error = None
        try:
            yield
        except BaseException as error:
            body_error = error
            raise
        finally:
            self._managed_call_scopes.pop()
            cleanup_errors: list[Exception] = []
            for handle, destructor in reversed(acquired):
                if handle.token in self._revoked_tokens:
                    continue
                try:
                    self.release_handle(handle, destructor)
                except Exception as error:
                    cleanup_errors.append(error)
            if cleanup_errors:
                if body_error is not None:
                    for error in cleanup_errors:
                        body_error.add_note(f"Native managed-call cleanup failed: {error}")
                    # Preserve the original failure; expose the first cleanup
                    # failure as its cause, while notes retain all failures.
                    raise body_error from cleanup_errors[0]
                if len(cleanup_errors) > 1:
                    raise ExceptionGroup("Multiple native cleanup failures", cleanup_errors)
                raise cleanup_errors[0]

    @contextmanager
    def managed_handle(self, create_signature: NativeSignature,
                       release_signature: NativeSignature, *arguments: object):
        """Scope one newly created opaque resource with deterministic cleanup.

        The native destructor is invoked when the scope exits, including when
        the body raises. This is an opt-in Python adapter, not Visual Quar
        ownership or automatic lifetime tracking. Native code is trusted.
        """
        if create_signature.result != "opaque":
            raise NativeFFIError("Managed creator must return opaque")
        if release_signature.arguments != ("opaque",) or release_signature.result != "void":
            raise NativeFFIError("Native destructor must have signature (opaque) -> void")
        handle = self.call(create_signature, *arguments)
        try:
            yield handle
        except BaseException as body_error:
            # A cleanup failure must not hide the original scope failure.
            # Preserve both errors through explicit exception chaining.
            if handle.token not in self._revoked_tokens:
                try:
                    self.release_handle(handle, release_signature)
                except Exception as cleanup_error:
                    body_error.add_note(
                        f"Native resource cleanup also failed: {cleanup_error}"
                    )
                    raise body_error from cleanup_error
            raise
        else:
            # Explicit or alias-based release already revoked this token.
            if handle.token not in self._revoked_tokens:
                self.release_handle(handle, release_signature)

    def call_struct_out(self, symbol: str, layout: NativeStructLayout) -> tuple[int, NativeStructValue]:
        """Call int symbol(struct *out) with an adapter-owned, zeroed buffer.

        The C function is trusted and must not retain the pointer. A nonzero
        status is treated as failure; no partially written value is exposed.
        """
        if not isinstance(symbol, str) or not symbol.isascii() or not symbol.isidentifier():
            raise NativeFFIError("Native symbol must be an ASCII identifier")
        if not isinstance(layout, NativeStructLayout):
            raise NativeFFIError("An explicit native struct layout is required")
        if symbol in self._declared_symbols or (symbol in self._output_symbols and self._output_symbols[symbol] != layout):
            raise NativeFFIError("Symbol is already bound with a different ABI signature")
        try:
            function = getattr(self._library, symbol)
        except AttributeError as exc:
            raise NativeFFIError(f"Native symbol not found: {symbol}") from exc
        structure = layout.ctypes_type()
        function.argtypes = (ctypes.POINTER(structure),)
        self._output_symbols[symbol] = layout
        function.restype = ctypes.c_int32
        output = structure()
        status = int(function(ctypes.byref(output)))
        if status != 0:
            raise NativeFFIError(f"Native output function failed with status {status}")
        return status, NativeStructValue(layout, tuple(getattr(output, name) for name, _ in layout.fields))

    def call_composite_out(self, symbol: str, layout: NativeCompositeLayout, *, success_statuses: tuple[int, ...] = (0,), empty_statuses: tuple[int, ...] = ()) -> tuple[int, bytes | None]:
        """Call int32_t symbol(composite *out), returning immutable raw ABI bytes.

        No union member is selected or interpreted. The trusted native function
        must write only within the supplied object and must not retain its pointer.
        Empty statuses return None without exposing the uninitialized output.
        Other statuses raise an error; the default success status is zero.
        """
        if not isinstance(symbol, str) or not symbol.isascii() or not symbol.isidentifier():
            raise NativeFFIError("Native symbol must be an ASCII identifier")
        if not isinstance(layout, NativeCompositeLayout):
            raise NativeFFIError("An explicit native composite layout is required")
        if symbol in self._declared_symbols or (symbol in self._output_symbols and self._output_symbols[symbol] != layout):
            raise NativeFFIError("Symbol is already bound with a different ABI signature")
        if (not isinstance(success_statuses, tuple) or not success_statuses
                or any(type(code) is not int or not -(2**31) <= code < 2**31 for code in success_statuses)
                or len(set(success_statuses)) != len(success_statuses)):
            raise NativeFFIError("Invalid native output success statuses")
        if (not isinstance(empty_statuses, tuple)
                or any(type(code) is not int or not -(2**31) <= code < 2**31 for code in empty_statuses)
                or len(set(empty_statuses)) != len(empty_statuses)
                or set(empty_statuses) & set(success_statuses)):
            raise NativeFFIError("Invalid or overlapping native empty statuses")
        structure = layout.ctypes_type()
        if ctypes.sizeof(structure) > 1024 * 1024:
            raise NativeFFIError("Native composite output exceeds the size limit")
        try:
            function = getattr(self._library, symbol)
        except AttributeError as exc:
            raise NativeFFIError(f"Native symbol not found: {symbol}") from exc
        function.argtypes = (ctypes.POINTER(structure),)
        function.restype = ctypes.c_int32
        self._output_symbols[symbol] = layout
        output = structure()  # ctypes zero-initializes the entire object.
        status = int(function(ctypes.byref(output)))
        if status in empty_statuses:
            return status, None
        if status not in success_statuses:
            raise NativeFFIError(f"Native output function failed with status {status}")
        return status, ctypes.string_at(ctypes.addressof(output), ctypes.sizeof(output))
