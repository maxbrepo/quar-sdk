"""SDL3-neutral ABI boundary tests; no SDL3 installation required."""
import ctypes
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from bindings.sdl3_events import SDL3EventPoller, decode_sdl3_event
from qrvm.native_abi_contract import NativeABIContractError, NativeOutputABIContract


class SDL3EventContractTests(unittest.TestCase):
    def test_header_verified_type(self):
        contract = NativeOutputABIContract(16, 8, (('type', 0),))
        raw = (0x300).to_bytes(4, __import__('sys').byteorder) + bytes(12)
        result = decode_sdl3_event(raw, contract)
        self.assertEqual(result.type, 0x300)
        self.assertEqual(result.raw, raw)

    def test_none_means_empty(self):
        self.assertIsNone(decode_sdl3_event(None, NativeOutputABIContract(16, 8, (('type', 0),))))

    def test_missing_verified_type_rejected(self):
        with self.assertRaises(NativeABIContractError):
            decode_sdl3_event(bytes(16), NativeOutputABIContract(16, 8, ()))

    def test_invalid_payload_rejected(self):
        with self.assertRaises(NativeABIContractError):
            decode_sdl3_event(bytes(12), NativeOutputABIContract(16, 8, (('type', 0),)))

    def test_invalid_contract_rejected(self):
        with self.assertRaises(NativeABIContractError):
            decode_sdl3_event(None, None)

    def test_poll_through_generic_ffi(self):
        compiler = shutil.which('cc')
        if not compiler:
            self.skipTest('C compiler unavailable')
        source = '''#include <stdint.h>
        typedef union { struct { uint32_t type; uint32_t padding[3]; } event; uint64_t align[2]; } FakeEvent;
        int32_t qgf_poll_fake_sdl3(FakeEvent *out) {
            out->event.type = 0x1234u;
            out->event.padding[0] = 0;
            out->event.padding[1] = 0;
            out->event.padding[2] = 0;
            return 1;
        }
        '''
        with tempfile.TemporaryDirectory() as tmp:
            c_path = Path(tmp) / 'fixture.c'
            lib_path = Path(tmp) / 'fixture.so'
            c_path.write_text(source, encoding='utf-8')
            subprocess.run([compiler, '-std=c11', '-shared', '-fPIC', str(c_path), '-o', str(lib_path)],
                           check=True, capture_output=True, text=True)
            poller = SDL3EventPoller(str(lib_path), 'qgf_poll_fake_sdl3',
                                     NativeOutputABIContract(16, 8, (('type', 0),)))
            result = poller.poll()
            self.assertEqual(result.type, 0x1234)
            self.assertEqual(len(result.raw), 16)


if __name__ == '__main__':
    unittest.main()
