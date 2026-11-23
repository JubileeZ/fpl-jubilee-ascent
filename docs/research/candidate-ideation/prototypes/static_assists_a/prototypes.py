"""Frozen static assists branch from the EXT-41 Arm A diagnostic."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import ClassVar

_DEPENDENCIES = {
    "static_attack_counts/prototypes.py": "64d5aaa0da48a5fbf06a0926c7aee3fc95d03189c16ad0690f34fadc0fe511ff",
    "ext_40/panel.py": "f58415afd3526eea9e4e5d5d90fd549ded770c238b4c0785b019232875fefaee",
    "ext_40/prototypes.py": "e305d411d8224a0ba109a863f11cee1f53c44f7658a885ca8cb6db5b20022fce",
}
for _path, _expected in _DEPENDENCIES.items():
    _payload = (Path(__file__).resolve().parents[1] / _path).read_bytes()
    if sha256(_payload.replace(b"\r\n", b"\n")).hexdigest() != _expected:
        raise ValueError(f"Reviewed static-attack dependency changed: {_path}")

from prototypes.ext_40.prototypes import Component
from prototypes.static_attack_counts.prototypes import FEATURES as COUNT_FEATURES
from prototypes.static_attack_counts.prototypes import (
    StaticAttackCountsModel,
    load_development_head,
)


class StaticAssistsA(StaticAttackCountsModel):
    component: ClassVar[Component] = "assists"
    development_head = load_development_head(
        component, "e5f8ea7821b3d3de9e68bea34ac6ced9ac4743e71dc32cda93d01f7626648a21"
    )

    @property
    def name(self) -> str:
        return "static_assists_a"


StaticAssistsA.load_optional_historical_filter_source(
    "ff5c60da865d22ec357bf32bbc458371aec2d95bbb6a63a4cb8745534084d97b"
)
PROTOTYPES = {"static_assists_a": StaticAssistsA}
FEATURES = {"static_assists_a": COUNT_FEATURES}
