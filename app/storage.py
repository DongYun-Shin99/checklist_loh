"""로컬 JSON 저장소. 모든 변경은 즉시 저장된다(자동 저장)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .models import Patch, Preset


def default_data_dir() -> Path:
    # PyInstaller exe로 실행될 때는 exe 옆에, 개발 중에는 프로젝트 루트에 data/ 생성
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "data"


class Storage:
    def __init__(self, directory: Path | None = None):
        self.dir = Path(directory) if directory else default_data_dir()
        self.file = self.dir / "app_data.json"
        self.presets: list[Preset] = []
        self.patches: list[Patch] = []
        self.load()

    def load(self) -> None:
        if not self.file.exists():
            return
        try:
            data = json.loads(self.file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        self.presets = [Preset.from_dict(d) for d in data.get("presets", [])]
        self.patches = [Patch.from_dict(d) for d in data.get("patches", [])]

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        data = {
            "presets": [p.to_dict() for p in self.presets],
            "patches": [p.to_dict() for p in self.patches],
        }
        self.file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ---- 조회 ----
    def active_patches(self) -> list[Patch]:
        return [p for p in self.patches if not p.is_archived]

    def archived_patches(self) -> list[Patch]:
        return [p for p in self.patches if p.is_archived]

    def find_patch(self, patch_id: str) -> Patch | None:
        return next((p for p in self.patches if p.id == patch_id), None)

    def find_checklist(self, checklist_id: str):
        """체크리스트 id로 (패치, 체크리스트) 쌍을 찾는다."""
        for patch in self.patches:
            for checklist in patch.checklists:
                if checklist.id == checklist_id:
                    return patch, checklist
        return None, None

    def find_preset_by_name(self, name: str) -> Preset | None:
        return next((p for p in self.presets if p.name == name), None)

    def unique_preset_name(self, base: str) -> str:
        if not self.find_preset_by_name(base):
            return base
        n = 2
        while self.find_preset_by_name(f"{base} ({n})"):
            n += 1
        return f"{base} ({n})"
