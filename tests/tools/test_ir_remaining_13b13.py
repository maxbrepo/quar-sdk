"""Coverage tests for enum, variants, named arguments and scoped files."""
import unittest
from frontend.quar.ast_nodes import (
    EnumDefinition, EnumVariant, VariantConstructor, NamedArgument,
    WithFileStatement, String, Integer, VariableDeclaration, FunctionCall,
)
from frontend.quar.ir.builder import lower_expression, lower_statement
from frontend.quar.ir.model import (
    IREnumDefinition, IRVariantNew, IRNamedArgument, IRWithFile,
)
from qrvm.ir_bridge import to_ast, compile_ir_statements
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM


class RemainingIRTests(unittest.TestCase):
    def test_enum_and_variant_execution(self):
        program = [
            EnumDefinition('Option', [EnumVariant('Some', ['int']), EnumVariant('None', [])]),
            VariableDeclaration('Option', 'value', VariantConstructor('Option', 'Some', [Integer(12)])),
        ]
        lowered = tuple(lower_statement(node) for node in program)
        self.assertIsInstance(lowered[0], IREnumDefinition)
        self.assertIsInstance(lowered[1].value, IRVariantNew)
        direct = QRVMCompiler().compile(program)
        via_ir = compile_ir_statements(lowered)
        self.assertEqual(direct['instructions'], via_ir['instructions'])
        original_vm, ir_vm = QRVM(), QRVM()
        original_vm.run(direct)
        ir_vm.run(via_ir)
        self.assertEqual(original_vm.variables, ir_vm.variables)

    def test_named_argument_roundtrip(self):
        original = NamedArgument('limit', Integer(5))
        lowered = lower_expression(original)
        self.assertIsInstance(lowered, IRNamedArgument)
        self.assertEqual(to_ast(lowered), original)
        call = FunctionCall('example', [original])
        self.assertEqual(to_ast(lower_expression(call)), call)

    def test_with_file_roundtrip(self):
        original = WithFileStatement(String('example.txt'), String('r'), 'handle', [])
        lowered = lower_statement(original)
        self.assertIsInstance(lowered, IRWithFile)
        self.assertEqual(to_ast(lowered), original)
        self.assertEqual(
            QRVMCompiler().compile([original])['instructions'],
            compile_ir_statements([lowered])['instructions'],
        )


if __name__ == '__main__':
    unittest.main()
