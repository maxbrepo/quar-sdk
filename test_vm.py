from qrvm.instructions import OpCode
from qrvm.vm import QRVM


program = [
    (OpCode.PUSH_INT, 10),
    (OpCode.PUSH_INT, 2),
    (OpCode.MUL, None),
    (OpCode.PRINT, None),
    (OpCode.HALT, None),
]

vm = QRVM()
vm.run(program)