"""Chapter 15.27: explicit effects with conservative unknown-call fallback."""
import unittest
from frontend.quar.ast_nodes import Assignment, BinaryOperation, FunctionCall, IfStatement, Integer, Variable
from qrvm.control_flow import ControlFlowBuilder
from qrvm.function_effects import FunctionEffects, call_invalidations
from qrvm.optional_dataflow import OptionalDataflowAnalyzer
from qrvm.optional_flow import FlowState, Presence


class FunctionEffectsTests(unittest.TestCase):
    def exit_state(self, statements, effects=None):
        graph = ControlFlowBuilder().build(statements)
        result = OptionalDataflowAnalyzer().analyze(
            graph, FlowState.from_mapping({'x': Presence.PRESENT, 'y': Presence.ABSENT}),
            ('x', 'y'), function_effects=effects)
        return result.before(graph.exit)

    def test_pure_call_keeps_facts(self):
        state = self.exit_state([Assignment('z', FunctionCall('read', []))], {'read': FunctionEffects()})
        self.assertEqual(state.get('x'), Presence.PRESENT)
        self.assertEqual(state.get('y'), Presence.ABSENT)

    def test_targeted_effect_invalidates_only_modified(self):
        state = self.exit_state([Assignment('z', FunctionCall('change_x', []))],
                                {'change_x': FunctionEffects({'x'})})
        self.assertEqual(state.get('x'), Presence.UNKNOWN)
        self.assertEqual(state.get('y'), Presence.ABSENT)

    def test_unknown_call_invalidates_all(self):
        state = self.exit_state([Assignment('z', FunctionCall('unknown', []))])
        self.assertEqual(state.get('x'), Presence.UNKNOWN)
        self.assertEqual(state.get('y'), Presence.UNKNOWN)

    def test_nested_unknown_argument_is_not_hidden_by_pure_outer(self):
        state = self.exit_state([Assignment('z', FunctionCall('read', [FunctionCall('unknown', [])]))],
                                {'read': FunctionEffects()})
        self.assertEqual(state.get('x'), Presence.UNKNOWN)

    def test_condition_with_pure_call_keeps_facts(self):
        state = self.exit_state([IfStatement(FunctionCall('check', []), [], [])],
                                {'check': FunctionEffects()})
        self.assertEqual(state.get('x'), Presence.PRESENT)

    def test_condition_with_targeted_effect(self):
        state = self.exit_state([IfStatement(FunctionCall('check', []), [], [])],
                                {'check': FunctionEffects({'y'})})
        self.assertEqual(state.get('x'), Presence.PRESENT)
        self.assertEqual(state.get('y'), Presence.UNKNOWN)

    def test_nested_binary_call_effects_union(self):
        expr = BinaryOperation(FunctionCall('a', []), 'and', FunctionCall('b', []))
        self.assertEqual(call_invalidations(expr, {'x','y'},
            {'a': FunctionEffects({'x'}), 'b': FunctionEffects({'y'})}), frozenset({'x','y'}))

    def test_presence_builtin_is_read_only(self):
        state = self.exit_state([Assignment('z', FunctionCall('present', [Variable('x')]))])
        self.assertEqual(state.get('x'), Presence.PRESENT)

    def test_assignment_after_effect_restores_fact(self):
        state = self.exit_state([Assignment('z', FunctionCall('change', [])), Assignment('x', Integer(3))])
        self.assertEqual(state.get('x'), Presence.PRESENT)

    def test_effect_summary_immutable_and_validated(self):
        effects = FunctionEffects({'x'})
        self.assertEqual(effects.modifies, frozenset({'x'}))
        with self.assertRaises(ValueError):
            FunctionEffects({''})


if __name__ == '__main__':
    unittest.main()
