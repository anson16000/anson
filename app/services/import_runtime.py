from __future__ import annotations


def should_skip_success_registry(mode: str, registry_hit: bool) -> bool:
    return mode != "force" and registry_hit
