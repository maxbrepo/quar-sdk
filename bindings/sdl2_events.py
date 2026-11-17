"""Optional SDL2 event adapter; no SDL-specific behavior belongs in QRVM.

The caller must supply a contract measured against its SDL2 development headers.
This adapter never guesses the SDL_Event size or decodes union members.
"""
from __future__ import annotations

from dataclasses import dataclass

from qrvm.native_abi_contract import NativeABIContractError, NativeOutputABIContract


@dataclass(frozen=True)
class SDLEventSnapshot:
    """A copied SDL event discriminator with its verified opaque payload."""

    type: int
    raw: bytes


def decode_sdl_event(raw: bytes | None, contract: NativeOutputABIContract) -> SDLEventSnapshot | None:
    """Decode only the header-verified type field; return None for an empty queue."""
    if not isinstance(contract, NativeOutputABIContract):
        raise NativeABIContractError('An ABI contract measured from C headers is required')
    if raw is None:
        return None
    return SDLEventSnapshot(type=contract.read_u32(raw, 'type'), raw=raw)


@dataclass(frozen=True)
class SDLKeyboardSnapshot:
    """Copied SDL keyboard event data from header-verified C field offsets."""

    type: int
    scancode: int
    keycode: int
    raw: bytes


def decode_sdl_keyboard_event(
    raw: bytes | None, contract: NativeOutputABIContract
) -> SDLKeyboardSnapshot | None:
    """Decode KEYDOWN/KEYUP only; reject missing or invalid probed fields.

    The contract must provide offsets named 'type', 'key_scancode',
    and 'key_sym', measured from the same SDL_Event C definition.
    """
    event = decode_sdl_event(raw, contract)
    if event is None or event.type not in (0x300, 0x301):
        return None
    return SDLKeyboardSnapshot(
        type=event.type,
        scancode=contract.read_i32(event.raw, 'key_scancode'),
        keycode=contract.read_i32(event.raw, 'key_sym'),
        raw=event.raw,
    )

class SDLEventPoller:
    """External event polling facade using the generic QRVM output FFI.

    The caller supplies a trusted C symbol with signature int32_t poll(T *out)
    and an ABI contract measured from the same T definition.
    """

    def __init__(self, library_path: str, symbol: str, contract: NativeOutputABIContract) -> None:
        from qrvm.native_ffi import NativeLibrary
        from qrvm.vm import QRVM

        if not isinstance(contract, NativeOutputABIContract):
            raise NativeABIContractError('A measured ABI contract is required')
        if not isinstance(symbol, str) or not symbol.isascii() or not symbol.isidentifier():
            raise NativeABIContractError('A valid native polling symbol is required')
        self.contract = contract
        self.symbol = symbol
        self.vm = QRVM()
        self.vm.bind_native(
            {}, NativeLibrary(library_path),
            output_layouts={symbol: contract.opaque_storage('VerifiedEventStorage')},
            output_success_statuses={symbol: (1,)},
            output_empty_statuses={symbol: (0,)},
        )

    def poll(self) -> SDLEventSnapshot | None:
        """Poll once; return a copied event or None if the native queue is empty."""
        from qrvm.instructions import OpCode

        before = len(self.vm.stack)
        self.vm.execute([(OpCode.CALL, (self.symbol, 0))], {})
        if len(self.vm.stack) != before + 1:
            raise NativeABIContractError('Unexpected native poll stack result')
        return decode_sdl_event(self.vm.stack.pop(), self.contract)

    def poll_keyboard(self) -> SDLKeyboardSnapshot | None:
        """Poll once and decode a keyboard event; other events return None."""
        event = self.poll()
        return decode_sdl_keyboard_event(event.raw, self.contract) if event is not None else None
