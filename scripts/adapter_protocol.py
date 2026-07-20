"""
adapter_protocol.py — 适配器协议 (eon-core 兼容存根)

Canonical: D:/Reasonix/scripts/adapter_protocol.py
通过 importlib 加载规范版本。
"""

from __future__ import annotations
import importlib.util
from pathlib import Path as _Path

_CANONICAL = str(_Path(__file__).resolve().parent.parent.parent / "scripts" / "adapter_protocol.py")

_spec = importlib.util.spec_from_file_location("_canonical_adapter_protocol", _CANONICAL)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

IProjectAdapter = _mod.IProjectAdapter
BayesianAdapterMixin = _mod.BayesianAdapterMixin

__all__ = ["IProjectAdapter", "BayesianAdapterMixin"]
