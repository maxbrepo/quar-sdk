"""Measure SDL3 event layout and identifiers using the installed C headers."""
from __future__ import annotations

import json
from pathlib import Path
import shlex
import subprocess
import tempfile

from qrvm.native_abi_contract import NativeABIContractError, NativeOutputABIContract


REQUIRED_FIELDS = ('type', 'key_scancode', 'key_key', 'motion_x', 'motion_y')
REQUIRED_EVENTS = ('keydown', 'keyup', 'motion')
OPTIONAL_EVENTS = ('quit',)


def parse_sdl3_probe(output: str) -> tuple[NativeOutputABIContract, dict[str, int]]:
    """Validate compiler-produced JSON; return a contract and SDL3 event IDs."""
    try:
        data = json.loads(output)
        if type(data) is not dict or set(data) != {'size', 'alignment', 'offsets', 'event_ids'}:
            raise ValueError('Unexpected probe keys')
        offsets = data['offsets']
        event_ids = data['event_ids']
        if type(offsets) is not dict or set(offsets) != set(REQUIRED_FIELDS):
            raise ValueError('Missing or unexpected field offsets')
        if type(event_ids) is not dict or not set(REQUIRED_EVENTS).issubset(event_ids) or not set(event_ids).issubset(set(REQUIRED_EVENTS) | set(OPTIONAL_EVENTS)):
            raise ValueError('Missing or unexpected event identifiers')
        if any(type(value) is not int or not 0 <= value <= 0xffffffff for value in event_ids.values()):
            raise ValueError('Invalid SDL3 event identifier')
        if len(set(event_ids.values())) != len(event_ids):
            raise ValueError('Duplicate SDL3 event identifier')
        contract = NativeOutputABIContract(data['size'], data['alignment'],
                                           tuple((name, offsets[name]) for name in REQUIRED_FIELDS))
        for name, offset in contract.offsets:
            if offset % 4 or offset + 4 > contract.size:
                raise ValueError('Invalid 32-bit event field offset: ' + name)
        return contract, event_ids
    except (ValueError, TypeError, KeyError) as exc:
        raise NativeABIContractError('Invalid SDL3 ABI probe result: ' + str(exc)) from exc


def measure_sdl3_abi(source: Path | None = None) -> tuple[NativeOutputABIContract, dict[str, int]]:
    """Compile and execute the probe. Requires SDL3 development headers and pkg-config."""
    if source is None:
        source = Path(__file__).resolve().parents[1] / 'fixtures' / 'sdl3_event_abi_probe.c'
    flags = subprocess.run(['pkg-config', '--cflags', 'sdl3'], check=True,
                           capture_output=True, text=True).stdout
    with tempfile.TemporaryDirectory(prefix='vq_sdl3_abi_') as directory:
        binary = Path(directory) / 'sdl3_event_probe'
        subprocess.run(['cc', '-std=c11', *shlex.split(flags), str(source), '-o', str(binary)],
                       check=True, capture_output=True, text=True)
        result = subprocess.run([str(binary)], check=True, capture_output=True, text=True)
    return parse_sdl3_probe(result.stdout)
