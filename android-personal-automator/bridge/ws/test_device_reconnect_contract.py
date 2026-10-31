"""Regression tests for reconnect behavior of the Termux listener."""
import ast
import unittest
from pathlib import Path

DEVICE = Path(__file__).with_name("device.py")

class ReconnectContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = ast.parse(DEVICE.read_text())

    def test_connection_closed_is_handled(self):
        handlers = [n for n in ast.walk(self.tree) if isinstance(n, ast.ExceptHandler)]
        names = set()
        for handler in handlers:
            if isinstance(handler.type, ast.Tuple):
                names.update(n.id for n in handler.type.elts if isinstance(n, ast.Name))
        self.assertIn("ConnectionClosed", names)

    def test_backoff_is_capped(self):
        source = DEVICE.read_text()
        self.assertIn("min(60.0,", source)
        self.assertIn("random.random()", source)

    def test_security_contract_retained(self):
        source = DEVICE.read_text()
        self.assertIn('URL.startswith("wss://")', source)
        self.assertIn('"Authorization": "Bearer " + TOKEN', source)
        self.assertIn('request_id in seen', source)
        self.assertIn('while not STOP.exists()', source)
        self.assertIn('COMMANDS[diagnostic]', source)

if __name__ == "__main__":
    unittest.main()
