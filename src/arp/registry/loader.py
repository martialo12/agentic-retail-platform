"""Load an agent declaration from YAML — the whole of 'adding an agent'."""

from pathlib import Path

import yaml

from arp.registry.models import AgentSpec


def _spec_path(agent_id: str, agents_dir: Path) -> Path:
    """Resolve a spec, preferring the folder layout.

    An agent is a folder (`spec.yaml` + prompt + nodes), but its id is hyphenated
    while the Python package is underscored — so both spellings are accepted. A
    bare `<id>.yaml` still works for minimal specs and fixtures.
    """
    base = Path(agents_dir)
    for candidate in (
        base / agent_id / "spec.yaml",
        base / agent_id.replace("-", "_") / "spec.yaml",
        base / f"{agent_id}.yaml",
    ):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"no registry spec for agent '{agent_id}' under {base}")


def load_agent(agent_id: str, agents_dir: Path) -> AgentSpec:
    path = _spec_path(agent_id, agents_dir)
    return AgentSpec.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def prompt_for(spec: AgentSpec, agents_dir: Path) -> str:
    """Read the agent's prompt, resolved relative to its own folder."""
    path = _spec_path(spec.id, agents_dir).parent / spec.prompt_path
    return path.read_text(encoding="utf-8")
