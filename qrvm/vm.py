from typing import Any

from .instructions import OpCode


Instruction = tuple[OpCode, Any | None]


class QRVM:
    def __init__(self) -> None:
        self.stack: list[int | float | bool] = []
        self.variables: dict[str, object] = {}
        self.functions: dict[str, dict] = {}

    def run(self, program) -> None:
        self.stack.clear()
        self.variables.clear()

        if isinstance(program, dict):
            instructions = program["instructions"]
            self.functions = program["functions"]
        else:
            instructions = program
            self.functions = {}

        self.execute(instructions, self.variables)
        # Execute complete QRVM program

    def execute(
        self,
        program: list[Instruction],
        variables: dict[str, object],
    ):
        ip = 0

        while ip < len(program):
            opcode, operand = program[ip]
            ip += 1

            if opcode == OpCode.PUSH_INT:
                if not isinstance(operand, int):
                    raise RuntimeError(
                        "PUSH_INT requires an integer operand."
                    )
                self.stack.append(operand)

            elif opcode == OpCode.PUSH_CHAR:
                if not isinstance(operand, str) or len(operand) > 1:
                    raise RuntimeError(
                        "PUSH_CHAR requires zero or one character."
                    )
                self.stack.append(operand)

            elif opcode == OpCode.PUSH_STRING:
                if not isinstance(operand, str):
                    raise RuntimeError(
                        "PUSH_STRING requires a string."
                    )
                self.stack.append(operand)

            elif opcode == OpCode.PUSH_DOUBLE:
                if not isinstance(operand, float):
                    raise RuntimeError(
                        "PUSH_DOUBLE requires a double operand."
                    )
                self.stack.append(operand)

            elif opcode == OpCode.PUSH_BOOL:
                if not isinstance(operand, bool):
                    raise RuntimeError(
                        "PUSH_BOOL requires a boolean operand."
                    )
                self.stack.append(operand)

            elif opcode == OpCode.LOAD:
                if not isinstance(operand, str):
                    raise RuntimeError(
                        "LOAD requires a variable name."
                    )
                if operand not in variables:
                    raise RuntimeError(
                        f"Unknown variable '{operand}'."
                    )
                self.stack.append(
                    variables[operand]
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
                variables[operand] = self.stack.pop()

            elif opcode == OpCode.ARRAY_NEW:
                if not isinstance(operand, tuple):
                    raise RuntimeError(
                        "ARRAY_NEW requires array metadata."
                    )
                if len(operand) == 5:
                    name, size, default, initial_count, second_size = operand
                    dynamic = False
                elif len(operand) == 6:
                    name, size, default, initial_count, second_size, dynamic = operand
                else:
                    raise RuntimeError(
                        "ARRAY_NEW received invalid metadata."
                    )
                if initial_count:
                    values = [
                        self.stack.pop()
                        for _ in range(initial_count)
                    ][::-1]
                else:
                    values = [
                        default for _ in range(size)
                    ]
                variables[name] = {
                    "__array__": values,
                    "__second_size__": second_size,
                    "__dynamic__": dynamic,
                }

            elif opcode == OpCode.ARRAY_LOAD:
                name, has_second = operand
                if name not in variables:
                    raise RuntimeError(
                        f"Unknown sequence '{name}'."
                    )
                value = variables[name]

                if isinstance(value, str):
                    if has_second:
                        raise RuntimeError(
                            "String accepts one index."
                        )
                    index = self.stack.pop()
                    if index < 0 or index >= len(value):
                        raise RuntimeError(
                            f"String index out of bounds: {index}."
                        )
                    self.stack.append(value[index])
                    continue

                if not isinstance(value, dict) or "__array__" not in value:
                    raise RuntimeError(
                        f"'{name}' is not an array."
                    )
                array = value["__array__"]

                if has_second:
                    second = self.stack.pop()
                    first = self.stack.pop()
                    width = value["__second_size__"]
                    if width is None:
                        raise RuntimeError(
                            "Second index requires multidimensional array."
                        )
                    rows = len(array) // width
                    if (
                        not isinstance(first, int)
                        or isinstance(first, bool)
                        or not isinstance(second, int)
                        or isinstance(second, bool)
                        or first < 0
                        or first >= rows
                        or second < 0
                        or second >= width
                    ):
                        raise RuntimeError(
                            f"Array index out of bounds: [{first}][{second}]."
                        )
                    index = first * width + second
                else:
                    index = self.stack.pop()

                if not isinstance(index, int) or isinstance(index, bool):
                    raise RuntimeError(
                        "Array index must be int."
                    )
                if index < 0 or index >= len(array):
                    raise RuntimeError(
                        f"Array index out of bounds: {index}."
                    )
                self.stack.append(array[index])

            elif opcode == OpCode.ARRAY_STORE:
                name, has_second = operand
                if name not in variables:
                    raise RuntimeError(
                        f"Unknown array '{name}'."
                    )
                value = variables[name]
                if not isinstance(value, dict) or "__array__" not in value:
                    raise RuntimeError(
                        f"'{name}' is not an array."
                    )
                array = value["__array__"]
                stored = self.stack.pop()

                if has_second:
                    second = self.stack.pop()
                    first = self.stack.pop()
                    width = value["__second_size__"]
                    if width is None:
                        raise RuntimeError(
                            "Second index requires multidimensional array."
                        )
                    rows = len(array) // width
                    if (
                        not isinstance(first, int)
                        or isinstance(first, bool)
                        or not isinstance(second, int)
                        or isinstance(second, bool)
                        or first < 0
                        or first >= rows
                        or second < 0
                        or second >= width
                    ):
                        raise RuntimeError(
                            f"Array index out of bounds: [{first}][{second}]."
                        )
                    index = first * width + second
                else:
                    index = self.stack.pop()

                if index < 0 or index >= len(array):
                    raise RuntimeError(
                        f"Array index out of bounds: {index}."
                    )
                array[index] = stored

            elif opcode == OpCode.LENGTH:
                if operand not in variables:
                    raise RuntimeError(
                        f"Unknown value '{operand}'."
                    )
                value = variables[operand]
                if isinstance(value, str):
                    self.stack.append(len(value))
                elif isinstance(value, dict) and "__array__" in value:
                    self.stack.append(len(value["__array__"]))
                else:
                    raise RuntimeError(
                        "Length requires array or string."
                    )

            elif opcode == OpCode.STRING_OP:
                name, argument_count = operand
                if len(self.stack) < argument_count:
                    raise RuntimeError(f"String operation '{name}' has insufficient arguments.")
                arguments = [self.stack.pop() for _ in range(argument_count)][::-1]
                try:
                    if name == "substring":
                        text, start, length = arguments
                        if not isinstance(text, str) or not isinstance(start, int) or not isinstance(length, int):
                            raise RuntimeError("substring requires string, int, int.")
                        if start < 0 or length < 0 or start + length > len(text):
                            raise RuntimeError("Substring range out of bounds.")
                        result = text[start:start + length]
                    elif name == "find":
                        text, needle = arguments
                        result = text.find(needle)
                    elif name == "replace":
                        text, old, new = arguments
                        result = text.replace(old, new)
                    elif name == "trim":
                        result = arguments[0].strip()
                    elif name == "to_string":
                        value = arguments[0]
                        if isinstance(value, bool):
                            result = "true" if value else "false"
                        else:
                            result = str(value)
                    elif name == "to_int":
                        result = int(arguments[0], 10)
                    elif name == "to_double":
                        result = float(arguments[0])
                    else:
                        raise RuntimeError(f"Unknown string operation '{name}'.")
                except RuntimeError:
                    raise
                except (ValueError, TypeError) as error:
                    raise RuntimeError(f"String conversion failed in '{name}'.") from error
                self.stack.append(result)

            elif opcode == OpCode.OBJECT_NEW:
                name, type_name, field_names = operand
                if len(self.stack) < len(field_names):
                    raise RuntimeError(
                        "OBJECT_NEW has insufficient values."
                    )
                values = [
                    self.stack.pop()
                    for _ in range(len(field_names))
                ][::-1]
                variables[name] = {
                    "__type__": type_name,
                    "__fields__": dict(zip(field_names, values)),
                }

            elif opcode == OpCode.MEMBER_LOAD:
                object_name, member_name = operand
                if object_name not in variables:
                    raise RuntimeError(
                        f"Unknown object '{object_name}'."
                    )
                obj = variables[object_name]
                if not isinstance(obj, dict) or "__fields__" not in obj:
                    raise RuntimeError(
                        f"'{object_name}' is not an object."
                    )
                if member_name not in obj["__fields__"]:
                    raise RuntimeError(
                        f"Unknown field '{member_name}'."
                    )
                self.stack.append(obj["__fields__"][member_name])

            elif opcode == OpCode.MEMBER_STORE:
                object_name, member_name = operand
                if not self.stack:
                    raise RuntimeError(
                        "MEMBER_STORE requires a value."
                    )
                if object_name not in variables:
                    raise RuntimeError(
                        f"Unknown object '{object_name}'."
                    )
                obj = variables[object_name]
                if not isinstance(obj, dict) or "__fields__" not in obj:
                    raise RuntimeError(
                        f"'{object_name}' is not an object."
                    )
                if member_name not in obj["__fields__"]:
                    raise RuntimeError(
                        f"Unknown field '{member_name}'."
                    )
                obj["__fields__"][member_name] = self.stack.pop()

            elif opcode == OpCode.TUPLE_NEW:
                count = operand
                values = [self.stack.pop() for _ in range(count)][::-1]
                self.stack.append(tuple(values))

            elif opcode == OpCode.TUPLE_UNPACK:
                value = self.stack.pop()
                if not isinstance(value, tuple) or len(value) != len(operand):
                    raise RuntimeError("Tuple destructuring failed.")
                for name, item in zip(operand, value): variables[name] = item

            elif opcode == OpCode.VARIANT_NEW:
                enum_name, variant_name, count = operand
                values = [self.stack.pop() for _ in range(count)][::-1]
                self.stack.append({"__enum__": enum_name, "__variant__": variant_name, "__payload__": values})

            elif opcode == OpCode.MATCH_VARIANT:
                variant_name, bindings, fail_target = operand
                value = self.stack.pop()
                if isinstance(value, str) and "." in value:
                    current_variant = value.rsplit(".", 1)[1]
                    payload = []
                elif isinstance(value, dict):
                    current_variant = value.get("__variant__")
                    payload = value.get("__payload__", [])
                else:
                    current_variant = None
                    payload = []
                if current_variant != variant_name:
                    ip = fail_target
                    continue
                for name, item in zip(bindings, payload): variables[name] = item

            elif opcode == OpCode.POP:
                if not self.stack:
                    raise RuntimeError(
                        "POP requires a stack value."
                    )
                self.stack.pop()

            elif opcode == OpCode.ADD:
                right = self.stack.pop()
                left = self.stack.pop()
                self.stack.append(left + right)

            elif opcode == OpCode.SUB:
                right = self.stack.pop()
                left = self.stack.pop()
                self.stack.append(left - right)

            elif opcode == OpCode.MUL:
                right = self.stack.pop()
                left = self.stack.pop()
                self.stack.append(left * right)

            elif opcode == OpCode.DIV:
                right = self.stack.pop()
                left = self.stack.pop()
                if right == 0:
                    raise RuntimeError("Division by zero")
                if (
                    isinstance(left, int)
                    and not isinstance(left, bool)
                    and isinstance(right, int)
                    and not isinstance(right, bool)
                ):
                    self.stack.append(int(left / right))
                else:
                    self.stack.append(left / right)

            elif opcode == OpCode.MOD:
                right = self.stack.pop()
                left = self.stack.pop()
                if right == 0:
                    raise RuntimeError("Modulo by zero")
                self.stack.append(left % right)

            elif opcode == OpCode.BIT_AND:
                right = self.stack.pop()
                left = self.stack.pop()
                self.stack.append(left & right)

            elif opcode == OpCode.BIT_OR:
                right = self.stack.pop()
                left = self.stack.pop()
                self.stack.append(left | right)

            elif opcode == OpCode.BIT_XOR:
                right = self.stack.pop()
                left = self.stack.pop()
                self.stack.append(left ^ right)

            elif opcode == OpCode.SHIFT_LEFT:
                right = self.stack.pop()
                left = self.stack.pop()
                if right < 0:
                    raise RuntimeError("Negative shift count")
                self.stack.append(left << right)

            elif opcode == OpCode.SHIFT_RIGHT:
                right = self.stack.pop()
                left = self.stack.pop()
                if right < 0:
                    raise RuntimeError("Negative shift count")
                self.stack.append(left >> right)

            elif opcode == OpCode.BIT_NOT:
                value = self.stack.pop()
                self.stack.append(~value)

            elif opcode == OpCode.EQUAL:
                right = self.stack.pop()
                left = self.stack.pop()
                self.stack.append(left == right)

            elif opcode == OpCode.NOT_EQUAL:
                right = self.stack.pop()
                left = self.stack.pop()
                self.stack.append(left != right)

            elif opcode == OpCode.LESS:
                right = self.stack.pop()
                left = self.stack.pop()
                self.stack.append(left < right)

            elif opcode == OpCode.LESS_EQUAL:
                right = self.stack.pop()
                left = self.stack.pop()
                self.stack.append(left <= right)

            elif opcode == OpCode.GREATER:
                right = self.stack.pop()
                left = self.stack.pop()
                self.stack.append(left > right)

            elif opcode == OpCode.GREATER_EQUAL:
                right = self.stack.pop()
                left = self.stack.pop()
                self.stack.append(left >= right)

            elif opcode == OpCode.LOGICAL_AND:
                right = self.stack.pop()
                left = self.stack.pop()
                if not isinstance(left, bool) or not isinstance(right, bool):
                    raise RuntimeError(
                        "LOGICAL_AND requires boolean operands."
                    )
                self.stack.append(left and right)

            elif opcode == OpCode.LOGICAL_OR:
                right = self.stack.pop()
                left = self.stack.pop()
                if not isinstance(left, bool) or not isinstance(right, bool):
                    raise RuntimeError(
                        "LOGICAL_OR requires boolean operands."
                    )
                self.stack.append(left or right)

            elif opcode == OpCode.LOGICAL_NOT:
                value = self.stack.pop()
                if not isinstance(value, bool):
                    raise RuntimeError(
                        "LOGICAL_NOT requires a boolean operand."
                    )
                self.stack.append(not value)

            elif opcode == OpCode.NEGATE:
                value = self.stack.pop()
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise RuntimeError(
                        "NEGATE requires a numeric operand."
                    )
                self.stack.append(-value)

            elif opcode == OpCode.JUMP_IF_FALSE:
                condition = self.stack.pop()
                if not isinstance(condition, (bool, int, float, str)):
                    raise RuntimeError(
                        "JUMP_IF_FALSE requires a truthy value."
                    )
                if not bool(condition):
                    ip = operand
                    continue

            elif opcode == OpCode.JUMP:
                ip = operand
                continue

            elif opcode == OpCode.PRINT:
                if not self.stack:
                    raise RuntimeError(
                        "PRINT requires a stack value."
                    )
                print(self.stack.pop())

            elif opcode == OpCode.CALL:
                if not isinstance(operand, tuple):
                    raise RuntimeError(
                        "CALL requires function metadata."
                    )

                name, argument_count = operand

                if name not in self.functions:
                    raise RuntimeError(
                        f"Unknown function '{name}'."
                    )

                function = self.functions[name]
                parameters = function["parameters"]

                if len(parameters) != argument_count:
                    raise RuntimeError(
                        f"Function '{name}' argument count mismatch."
                    )

                arguments = [
                    self.stack.pop()
                    for _ in range(argument_count)
                ]
                arguments.reverse()

                local_variables = dict(
                    zip(parameters, arguments)
                )

                result = self.execute(
                    function["instructions"],
                    local_variables,
                )

                if function.get("return_type") == "void":
                    continue

                if result is None:
                    raise RuntimeError(
                        f"Function '{name}' did not return a value."
                    )

                self.stack.append(result)

            elif opcode == OpCode.RETURN:
                has_value = bool(operand)
                if not has_value:
                    return None
                if not self.stack:
                    raise RuntimeError(
                        "RETURN requires a stack value."
                    )
                return self.stack.pop()

            elif opcode == OpCode.HALT:
                return None

            else:
                raise RuntimeError(
                    f"Unknown opcode: {opcode}"
                )

        return None
        # Finish current execution frame
