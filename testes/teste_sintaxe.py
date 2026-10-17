"""Teste rápido de sintaxe; execute com: python -m unittest discover -s testes"""
import ast
import unittest
from pathlib import Path

class SyntaxTests(unittest.TestCase):
    def test_app_parses(self):
        source = Path(__file__).resolve().parents[1] / "necromante.py"
        ast.parse(source.read_text(encoding="utf-8"), filename=str(source))

if __name__ == "__main__":
    unittest.main()
