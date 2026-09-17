from typing import Any

from .instructions import OpCode


Instruction = tuple[OpCode, Any | None]


class QRVM:
    def __init__(self) -> None:
        self.stack: list[int] = []
        self.variables: dict[str, int] = {}

        self.ip: int = 0
        self.running: bool = False

    def run(self, program: list[Instruction]) -> None:
        self.stack.clear()
        self.variables.clear()

        self.ip = 0
        self.running = True

        while self.running:
            opcode, operand = program[self.ip]
            self.ip += 1

            if opcode == OpCode.PUSH_INT:
                if not isinstance(operand, int):
                    raise RuntimeError(
                        "PUSH_INT requires an integer operand."
                    )

                self.stack.append(operand)

            elif opcode == OpCode.LOAD:
                if not isinstance(operand, str):
                    raise RuntimeError(
                        "LOAD requires a variable name."
                    )

                if operand not in self.variables:
                    raise RuntimeError(
                        f"Unknown variable '{operand}'."
                    )

                self.stack.append(
                    self.variables[operand]
                )

            elif opcode == OpCode.STORE:
                if not isinstance(operand, str):
                    raise RuntimeError(
                        "STORE requires a variable name."
                    )

                if not self.stack:
                    raise RuntimeError(
                        "STORE requires a stack value."
                    )

                self.variables[operand] = self.stack.pop()

            elif opcode == OpCode.POP:
                if not self.stack:
                    raise RuntimeError(
                        "POP requires a stack value."
                    )

                self.stack.pop()

            elif opcode == OpCode.ADD:
                right = self.stack.pop()
                left = self.stack.pop()

                self.stack.append(
                    left + right
                )

            elif opcode == OpCode.SUB:
                right = self.stack.pop()
                left = self.stack.pop()

                self.stack.append(
                    left - right
                )

            elif opcode == OpCode.MUL:
                right = self.stack.pop()
                left = self.stack.pop()

                self.stack.append(
                    left * right
                )

            elif opcode == OpCode.DIV:
                right = self.stack.pop()
                left = self.stack.pop()

                self.stack.append(
                    left // right
                )

            elif opcode == OpCode.PRINT:
                if not self.stack:
                    raise RuntimeError(
                        "PRINT requires a stack value."
                    )

                value = self.stack.pop()
                print(value)

            elif opcode == OpCode.HALT:
                self.running = False

            else:
                raise RuntimeError(
                    f"Unknown opcode: {opcode}"
                )

        # Finish execution at HALT