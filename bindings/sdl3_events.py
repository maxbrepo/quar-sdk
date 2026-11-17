"""SDL3 event snapshots using compiler-measured ABI contracts.

SDL3 event constants and layouts are intentionally not inherited from SDL2.
The caller supplies a contract obtained from the actual SDL3 headers.
"""
from __future__ import annotations

from dataclasses import dataclass

from qrvm.native_abi_contract import NativeABIContractError, NativeOutputABIContract


@dataclass(frozen=True)
class SDL3EventSnapshot:
    type: int
    raw: bytes


def decode_sdl3_event(raw: bytes | None, contract: NativeOutputABIContract) -> SDL3EventSnapshot | None:
    """Read the verified SDL_Event.type field; preserve the entire event copy."""
    if not isinstance(contract, NativeOutputABIContract):
        raise NativeABIContractError('An SDL3 header-measured ABI contract is required')
    if raw is None:
        return None
    return SDL3EventSnapshot(type=contract.read_u32(raw, 'type'), raw=raw)


class SDL3EventPoller:
    """Poll via a trusted C shim: int32_t symbol(SDL_Event *out).

    Status 1 denotes an event; status 0 denotes an empty queue.
    The shim and contract must be compiled against matching SDL3 headers.
    """

    def __init__(self, library_path: str, symbol: str, contract: NativeOutputABIContract) -> None:
        from qrvm.native_ffi import NativeLibrary
        from qrvm.vm import QRVM

        if not isinstance(contract, NativeOutputABIContract):
            raise NativeABIContractError('An SDL3 header-measured ABI contract is required')
        if not isinstance(symbol, str) or not symbol.isascii() or not symbol.isidentifier():
            raise NativeABIContractError('Invalid native polling symbol')
        self.contract = contract
        self.symbol = symbol
        self.vm = QRVM()
        self.vm.bind_native({}, NativeLibrary(library_path),
                            output_layouts={symbol: contract.opaque_storage('SDL3EventStorage')},
                            output_success_statuses={symbol: (1,)},
                            output_empty_statuses={symbol: (0,)})

    def poll(self) -> SDL3EventSnapshot | None:
        from qrvm.instructions import OpCode

        before = len(self.vm.stack)
        self.vm.execute([(OpCode.CALL, (self.symbol, 0))], {})
        if len(self.vm.stack) != before + 1:
            raise NativeABIContractError('Unexpected native poll stack result')
        return decode_sdl3_event(self.vm.stack.pop(), self.contract)


@dataclass(frozen=True)
class SDL3KeyboardSnapshot:
    """Keyboard fields copied from an SDL3-header-verified event layout."""
    type: int
    scancode: int
    keycode: int
    raw: bytes


@dataclass(frozen=True)
class SDL3MouseMotionSnapshot:
    """Mouse motion float fields read at verified offsets."""
    type: int
    x: float
    y: float
    raw: bytes


def decode_sdl3_keyboard_event(
    raw: bytes | None, contract: NativeOutputABIContract,
    keydown: int, keyup: int,
) -> SDL3KeyboardSnapshot | None:
    """Use SDL3 event IDs from headers; never reuse SDL2 constants."""
    event = decode_sdl3_event(raw, contract)
    if event is None or event.type not in (keydown, keyup):
        return None
    return SDL3KeyboardSnapshot(
        event.type, contract.read_u32(event.raw, 'key_scancode'),
        contract.read_u32(event.raw, 'key_key'), event.raw,
    )


def decode_sdl3_mouse_motion_event(
    raw: bytes | None, contract: NativeOutputABIContract, motion_type: int,
) -> SDL3MouseMotionSnapshot | None:
    """Decode SDL3 float coordinates using probed C field offsets."""
    import struct
    import sys
    event = decode_sdl3_event(raw, contract)
    if event is None or event.type != motion_type:
        return None
    fields = dict(contract.offsets)
    coordinates = []
    for name in ('motion_x', 'motion_y'):
        if name not in fields:
            raise NativeABIContractError('Missing header-verified field: ' + name)
        offset = fields[name]
        if offset % 4 or offset + 4 > contract.size:
            raise NativeABIContractError('Invalid float field offset: ' + name)
        coordinates.append(struct.unpack_from('=f', event.raw, offset)[0])
    return SDL3MouseMotionSnapshot(event.type, *coordinates, event.raw)
