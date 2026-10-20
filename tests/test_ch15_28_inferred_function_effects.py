"""Chapter 15.28: conservative AST-based function effect inference."""
import unittest
from frontend.quar.ast_nodes import (
    Assignment, FunctionDefinition, FunctionParameter, FunctionCall,
    VariableDeclaration, ReturnStatement, Integer, Variable, IfStatement,
    WhileStatement, MemberAssignment,
)
from qrvm.function_effects import FunctionEffects, infer_function_effects, call_invalidations


def fn(name, *body, parameters=()):
    return FunctionDefinition('void', name, list(parameters), list(body))


class InferredFunctionEffectsTests(unittest.TestCase):
    def infer(self, *functions):
        return infer_function_effects(functions, {'x', 'y'})

    def test_simple_pure_function(self):
        self.assertEqual(self.infer(fn('read', ReturnStatement(Integer(3))))['read'], FunctionEffects())

    def test_global_assignment(self):
        self.assertEqual(self.infer(fn('write', Assignment('x', Integer(1))))['write'], FunctionEffects({'x'}))

    def test_local_shadow_does_not_modify_global(self):
        self.assertEqual(self.infer(fn('local', VariableDeclaration('int', 'x', Integer(1)), Assignment('x', Integer(2))))['local'], FunctionEffects())

    def test_parameter_shadow_does_not_modify_global(self):
        param = FunctionParameter('int', 'x')
        self.assertEqual(self.infer(fn('param', Assignment('x', Integer(3)), parameters=(param,)))['param'], FunctionEffects())

    def test_known_call_propagates(self):
        result = self.infer(fn('write', Assignment('x', Integer(1))), fn('caller', FunctionCall('write', [])))
        self.assertEqual(result['caller'], FunctionEffects({'x'}))

    def test_unknown_external_call_is_not_claimed_pure(self):
        self.assertNotIn('caller', self.infer(fn('caller', FunctionCall('external', []))))

    def test_unknown_transitive_call_is_not_claimed_pure(self):
        result = self.infer(fn('a', FunctionCall('external', [])), fn('b', FunctionCall('a', [])))
        self.assertNotIn('a', result)
        self.assertNotIn('b', result)

    def test_branch_effects_union(self):
        result = self.infer(fn('branch', IfStatement(Variable('flag'), [Assignment('x', Integer(1))], [Assignment('y', Integer(2))])))
        self.assertEqual(result['branch'], FunctionEffects({'x', 'y'}))

    def test_loop_effects(self):
        result = self.infer(fn('looping', WhileStatement(Variable('flag'), [Assignment('x', Integer(1))])))
        self.assertEqual(result['looping'], FunctionEffects({'x'}))

    def test_unsupported_mutation_is_unknown(self):
        self.assertNotIn('mutate', self.infer(fn('mutate', MemberAssignment('obj', 'field', Integer(1)))))

    def test_call_argument_effects_propagate(self):
        result = self.infer(fn('write', Assignment('x', Integer(1))), fn('read', ReturnStatement(Integer(2))),
                            fn('outer', FunctionCall('read', [FunctionCall('write', [])])))
        self.assertEqual(result['outer'], FunctionEffects({'x'}))

    def test_inferred_summaries_integrate_with_call_invalidations(self):
        summaries = self.infer(fn('write', Assignment('x', Integer(1))))
        self.assertEqual(call_invalidations(FunctionCall('write', []), {'x', 'y'}, summaries), frozenset({'x'}))


if __name__ == '__main__':
    unittest.main()
