"""CheckpointManager — 管线检查点/恢复机制.

允许长时间运行的管线 (物种检索、批量文献收集) 在崩溃后从断点恢复,
避免重复已完成的阶段。

Usage:
    # 在管线中
    from eon_core_shared.checkpoint import CheckpointManager

    cpm = CheckpointManager("search_tribolodon", base_dir="data/checkpoints/")

    # 创建或恢复
    if cpm.has_checkpoint("phase_2_cognitive"):
        state = cpm.restore("phase_2_cognitive")
        papers = state["papers"]
    else:
        papers = search_papers()

    # 阶段完成后保存
    cpm.save("phase_2_cognitive", {"papers": papers, "query": species})

    # 完成所有阶段后清除
    cpm.complete()
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class CheckpointManager:
    """管线检查点管理器 — 断点续传.

    Attributes:
        name: 管线名称 (用于区分不同管线)
        base_dir: 检查点存储目录
        ttl_sec: 检查点生存时间, 超过此时间的检查点视为过期
        compress: 是否压缩存储 (未来支持)
    """
    name: str
    base_dir: str = "data/checkpoints"
    ttl_sec: int = 86400  # 24小时
    compress: bool = False

    def __post_init__(self):
        self._dir = Path(self.base_dir) / self.name.replace(" ", "_")
        self._dir.mkdir(parents=True, exist_ok=True)
        self._stages_completed: set[str] = set()
        self._load_index()

    # ── Public API ────────────────────────────────────────────────

    def save(self, stage: str, data: dict) -> str:
        """保存一个阶段的检查点.

        Args:
            stage: 阶段标识符 (如 "phase_1_kb", "phase_2_search")
            data: 要保存的状态数据 (JSON 可序列化)

        Returns:
            检查点文件路径
        """
        # Clean stage name for filesystem
        safe_key = self._sanitize(stage)
        path = self._dir / f"{safe_key}.json"

        payload = {
            "stage": stage,
            "timestamp": time.time(),
            "pipeline": self.name,
            "data": data,
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, default=str)

        self._stages_completed.add(stage)
        self._save_index()

        return str(path)

    def restore(self, stage: str) -> Optional[dict]:
        """从检查点恢复阶段数据.

        Args:
            stage: 阶段标识符

        Returns:
            阶段数据, 如果检查点不存在或过期则返回 None
        """
        safe_key = self._sanitize(stage)
        path = self._dir / f"{safe_key}.json"

        if not path.exists():
            return None

        # Check TTL
        age = time.time() - path.stat().st_mtime
        if age > self.ttl_sec:
            self._remove(stage)
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            return payload.get("data")
        except (json.JSONDecodeError, KeyError):
            self._remove(stage)
            return None

    def has_checkpoint(self, stage: str) -> bool:
        """检查阶段是否有未过期的检查点. """
        safe_key = self._sanitize(stage)
        path = self._dir / f"{safe_key}.json"
        if not path.exists():
            return False
        age = time.time() - path.stat().st_mtime
        if age > self.ttl_sec:
            self._remove(stage)
            return False
        return True

    def list_stages(self) -> list[str]:
        """列出所有未过期的阶段. """
        valid = []
        for path in self._dir.glob("*.json"):
            if path.name == "_index.json":
                continue
            age = time.time() - path.stat().st_mtime
            if age <= self.ttl_sec:
                stage = path.stem.replace("_", " ", 1)  # crude reverse sanitize
                valid.append(stage)
        return valid

    def complete(self) -> None:
        """管线完成: 清除所有检查点. """
        for path in self._dir.glob("*.json"):
            try:
                path.unlink()
            except OSError:
                pass
        self._stages_completed.clear()
        self._save_index()

    def clear(self) -> None:
        """清除所有检查点 (别名). """
        self.complete()

    def __enter__(self) -> CheckpointManager:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """异常退出时不清除检查点, 方便断点续传. """
        pass

    # ── Internal ──────────────────────────────────────────────────

    def _sanitize(self, stage: str) -> str:
        """将阶段名转为安全文件名. """
        return stage.replace("/", "_").replace("\\", "_").replace(" ", "_")[:120]

    def _remove(self, stage: str) -> None:
        """移除一个阶段的检查点. """
        safe_key = self._sanitize(stage)
        path = self._dir / f"{safe_key}.json"
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        self._stages_completed.discard(stage)

    def _index_path(self) -> Path:
        return self._dir / "_index.json"

    def _load_index(self) -> None:
        """加载已完成阶段索引. """
        idx = self._index_path()
        if idx.exists():
            try:
                with open(idx) as f:
                    data = json.load(f)
                self._stages_completed = set(data.get("stages", []))
                # Validate & prune stale entries
                for stage in list(self._stages_completed):
                    if not self.has_checkpoint(stage):
                        self._stages_completed.discard(stage)
            except (json.JSONDecodeError, OSError):
                self._stages_completed = set()

    def _save_index(self) -> None:
        """保存已完成阶段索引. """
        try:
            with open(self._index_path(), "w") as f:
                json.dump({
                    "pipeline": self.name,
                    "stages": sorted(self._stages_completed),
                    "updated_at": time.time(),
                }, f)
        except OSError:
            pass
