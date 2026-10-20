"""Package boundary and backwards-compatible import tests."""
import unittest
from frontend.quar import ir
from frontend.quar.ir import model, builder

class IRPackageTests(unittest.TestCase):
    def test_public_api_identity(self):
        self.assertIs(ir.IRProject, model.IRProject)
        self.assertIs(ir.lower_expression, builder.lower_expression)

    def test_model_has_no_frontend_ast_dependency(self):
        from pathlib import Path
        source = Path(model.__file__).read_text()
        self.assertNotIn('ast_nodes', source)
        self.assertNotIn('module_loader', source)

    def test_immutable_ir(self):
        from dataclasses import FrozenInstanceError
        value = ir.IRLiteral(42)
        with self.assertRaises(FrozenInstanceError):
            value.value = 7

if __name__ == '__main__':
    unittest.main()
