"""Registered agents.

Each agent is a self-contained folder: `spec.yaml` (what it may do), `prompt.md`
(how it is asked), `schema.py` (what it must return), `nodes.py` (its steps).
Adding one touches nothing under registry/, policy/ or orchestration/.
"""

from pathlib import Path

AGENTS_DIR = Path(__file__).resolve().parent

__all__ = ["AGENTS_DIR"]
