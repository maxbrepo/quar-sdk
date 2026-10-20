"""Chapter 15.21: invalidate optional flow proofs across opaque calls."""
import unittest
from frontend.quar.ast_nodes import (VariableDeclaration, Assignment, Variable,
    Integer, Boolean, FunctionCall, FunctionDefinition, IfStatement)
from qrvm.compiler import QRVMCompiler


def call(name, *args):
    return FunctionCall(name, list(args))


class OptionalCallInvalidationTests(unittest.TestCase):
    def test_call_invalidates_known_absence(self):
        program = [VariableDeclaration('int?', 'x', None),
                   FunctionDefinition('void', 'touch', [], []),
                   call('touch'), IfStatement(call('unwrap', Variable('x')), [], [])]
        # Without invalidation the compiler would reject the unwrap.
        QRVMCompiler().compile(program)

    def test_runtime_guard_remains_for_absent_value(self):
        QRVMCompiler().compile([VariableDeclaration('int?', 'x', None),
                                IfStatement(call('unwrap', Variable('x')), [], [])])

    def test_branch_call_invalidates_absence(self):
        program = [VariableDeclaration('int?', 'x', None),
                   FunctionDefinition('void', 'touch', [], []),
                   IfStatement(Boolean(True), [call('touch'), IfStatement(call('unwrap', Variable('x')), [], [])], [])]
        QRVMCompiler().compile(program)

    def test_conditional_call_does_not_restore_stale_absence(self):
        program = [VariableDeclaration('int?', 'x', None),
                   FunctionDefinition('bool', 'probe', [], []),
                   IfStatement(call('probe'), [IfStatement(call('unwrap', Variable('x')), [], [])], [])]
        QRVMCompiler().compile(program)

    def test_assignment_after_call_keeps_runtime_guard(self):
        program = [VariableDeclaration('int?', 'x', None),
                   FunctionDefinition('void', 'touch', [], []),
                   call('touch'), Assignment('x', None), IfStatement(call('unwrap', Variable('x')), [], [])]
        QRVMCompiler().compile(program)

    def test_call_does_not_erase_optional_type(self):
        program = [VariableDeclaration('int?', 'x', Integer(4)),
                   FunctionDefinition('void', 'touch', [], []),
                   call('touch'), IfStatement(call('present', Variable('x')), [], [])]
        QRVMCompiler().compile(program)


if __name__ == '__main__':
    unittest.main()
