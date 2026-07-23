"""Load an agent declaration from YAML — the whole of 'adding an agent'."""

from pathlib import Path

import yaml

from arp.registry.models import AgentSpec


def load_agent(agent_id: str, agents_dir: Path) -> AgentSpec:
    path = Path(agents_dir) / f"{agent_id}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"no registry spec for agent '{agent_id}' at {path}")
    return AgentSpec.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
