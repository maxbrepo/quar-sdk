"""Build and load the real SDL3 event-polling adapter when SDL3 is installed."""
from __future__ import annotations

from pathlib import Path
import shlex
import subprocess

from bindings.sdl3_abi_probe import measure_sdl3_abi
from bindings.sdl3_events import SDL3EventPoller
from qrvm.native_abi_contract import NativeABIContractError


def compile_sdl3_poll_shim(output: Path, source: Path | None = None) -> Path:
    """Compile the C adapter against SDL3; return its shared-library path."""
    if source is None:
        source = Path(__file__).resolve().parents[1] / 'fixtures' / 'sdl3_poll_shim.c'
    output = Path(output)
    if not source.is_file():
        raise NativeABIContractError('SDL3 polling adapter source is missing')
    flags = subprocess.run(['pkg-config', '--cflags', '--libs', 'sdl3'],
                           check=True, capture_output=True, text=True).stdout
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['cc', '-std=c11', '-shared', '-fPIC', str(source), '-o', str(output),
                    *shlex.split(flags)], check=True, capture_output=True, text=True)
    return output


def create_sdl3_poller(library_path: Path) -> tuple[SDL3EventPoller, dict[str, int]]:
    """Measure the ABI and create a poller using the matching SDL3 installation."""
    contract, event_ids = measure_sdl3_abi()
    return SDL3EventPoller(str(library_path), 'vq_sdl3_poll_event', contract), event_ids

class SDL3EventSession:
    """Own the SDL event subsystem while exposing the existing QRVM poller.

    This wrapper requires a trusted shim built against the same SDL3 library
    as the header-based ABI probe. It does not own the application's window.
    """

    def __init__(self, library_path: Path) -> None:
        import ctypes
        self._library_path = Path(library_path)
        self._native = ctypes.CDLL(str(self._library_path.resolve(strict=True)))
        self._native.vq_sdl3_init_events.argtypes = []
        self._native.vq_sdl3_init_events.restype = ctypes.c_int32
        self._native.vq_sdl3_quit_events.argtypes = []
        self._native.vq_sdl3_quit_events.restype = None
        self._native.vq_sdl3_last_error.argtypes = []
        self._native.vq_sdl3_last_error.restype = ctypes.c_char_p
        self._active = False
        self._poller = None
        self.event_ids: dict[str, int] = {}

    def __enter__(self) -> 'SDL3EventSession':
        if self._active:
            raise NativeABIContractError('SDL3 event session is already active')
        if self._native.vq_sdl3_init_events() != 1:
            detail = self._native.vq_sdl3_last_error()
            message = detail.decode('utf-8', errors='replace') if detail else 'unknown error'
            raise NativeABIContractError('SDL3 event initialization failed: ' + message)
        self._active = True
        try:
            self._poller, self.event_ids = create_sdl3_poller(self._library_path)
        except BaseException:
            self.close()
            raise
        return self

    def poll(self):
        """Return the next immutable event snapshot or None for an empty queue."""
        if not self._active or self._poller is None:
            raise NativeABIContractError('SDL3 event session is not active')
        return self._poller.poll()

    def poll_typed(self):
        """Decode known SDL3 events; preserve unknown events as raw snapshots."""
        from bindings.sdl3_events import (
            decode_sdl3_keyboard_event, decode_sdl3_mouse_motion_event,
        )
        event = self.poll()
        if event is None:
            return None
        contract = self._poller.contract
        ids = self.event_ids
        if event.type in (ids.get('keydown'), ids.get('keyup')):
            if 'keydown' not in ids or 'keyup' not in ids:
                raise NativeABIContractError('Incomplete SDL3 keyboard event IDs')
            return decode_sdl3_keyboard_event(event.raw, contract, ids['keydown'], ids['keyup'])
        if 'motion' in ids and event.type == ids['motion']:
            return decode_sdl3_mouse_motion_event(event.raw, contract, ids['motion'])
        return event

    def poll_batch(self, max_events: int = 64) -> list:
        """Drain at most max_events; a bounded batch prevents event starvation."""
        if type(max_events) is not int or not 1 <= max_events <= 4096:
            raise ValueError('max_events must be an integer between 1 and 4096')
        if not self._active or self._poller is None:
            raise NativeABIContractError('SDL3 event session is not active')
        result = []
        for _ in range(max_events):
            event = self.poll_typed()
            if event is None:
                break
            result.append(event)
        return result

    def is_quit_event(self, event) -> bool:
        """Recognize SDL_EVENT_QUIT using the header-measured identifier."""
        from bindings.sdl3_events import SDL3EventSnapshot
        if 'quit' not in self.event_ids:
            raise NativeABIContractError('SDL3 quit identifier is not available in ABI contract')
        return isinstance(event, SDL3EventSnapshot) and event.type == self.event_ids['quit']

    def close(self) -> None:
        """Release this session's SDL event-subsystem initialization once."""
        if self._active:
            self._active = False
            self._poller = None
            self._native.vq_sdl3_quit_events()

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def dispatch_events(self, on_event, max_events: int = 64) -> tuple[int, bool]:
        """Dispatch a bounded event batch; stop immediately on SDL_EVENT_QUIT.

        Returns (dispatched_count, quit_requested). The caller owns the main
        loop and rendering; callbacks receive immutable event snapshots.
        Callback exceptions propagate without silently consuming more events.
        """
        if not callable(on_event):
            raise TypeError('on_event must be callable')
        if type(max_events) is not int or not 1 <= max_events <= 4096:
            raise ValueError('max_events must be an integer between 1 and 4096')
        if not self._active or self._poller is None:
            raise NativeABIContractError('SDL3 event session is not active')
        dispatched = 0
        for _ in range(max_events):
            event = self.poll_typed()
            if event is None:
                break
            quit_requested = self.is_quit_event(event)
            on_event(event)
            dispatched += 1
            if quit_requested:
                return dispatched, True
        return dispatched, False

    def dispatch_frame(self, on_event, max_events: int = 64) -> tuple[int, bool]:
        """Process one bounded frame of events for an application-owned loop.

        The caller remains responsible for window ownership, rendering and
        frame timing. A quit event stops dispatch immediately. This is a
        small alias with an explicit frame-level contract for QGF adapters.
        """
        return self.dispatch_events(on_event, max_events)
