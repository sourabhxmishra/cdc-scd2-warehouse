"""Make the repository root importable so ``import src...`` works under any pytest invocation.

Running the ``pytest`` binary directly (as CI does) adds the ``tests/`` directory to ``sys.path``
rather than the repo root, so ``from src... import`` would fail. Inserting the root here fixes it
regardless of how pytest is launched.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
