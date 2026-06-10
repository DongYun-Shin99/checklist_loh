"""데이터 모델: 프리셋(템플릿) / 패치 / 체크리스트 / 항목.

구조: 패치(기한일) → 체크리스트(프리셋+국가로 생성) → 항목(체크/경로/메모)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

COUNTRIES = {"KR": "한국", "TW": "대만", "JP": "일본"}
COUNTRY_COLORS = {"KR": "#2563eb", "TW": "#059669", "JP": "#dc2626"}

STATUS_IN_PROGRESS = "in_progress"
STATUS_DONE = "done"


def new_id() -> str:
    return uuid.uuid4().hex


def _empty_paths() -> dict:
    return {code: "" for code in COUNTRIES}


@dataclass
class PresetItem:
    description: str = ""
    paths: dict = field(default_factory=_empty_paths)

    def to_dict(self) -> dict:
        return {"description": self.description, "paths": dict(self.paths)}

    @classmethod
    def from_dict(cls, d: dict) -> "PresetItem":
        paths = _empty_paths()
        paths.update(d.get("paths", {}))
        return cls(description=d.get("description", ""), paths=paths)


@dataclass
class Preset:
    id: str = field(default_factory=new_id)
    name: str = "새 프리셋"
    description: str = ""
    items: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "items": [i.to_dict() for i in self.items],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Preset":
        return cls(
            id=d.get("id") or new_id(),
            name=d.get("name", "이름 없는 프리셋"),
            description=d.get("description", ""),
            items=[PresetItem.from_dict(i) for i in d.get("items", [])],
        )


@dataclass
class ChecklistItem:
    description: str = ""
    path: str = ""
    status: str = STATUS_IN_PROGRESS
    memo: str = ""

    @property
    def done(self) -> bool:
        return self.status == STATUS_DONE

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "path": self.path,
            "status": self.status,
            "memo": self.memo,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ChecklistItem":
        return cls(
            description=d.get("description", ""),
            path=d.get("path", ""),
            status=d.get("status", STATUS_IN_PROGRESS),
            memo=d.get("memo", ""),
        )


@dataclass
class Checklist:
    """패치 안에 들어가는 작업 묶음(예: 영웅 추가). 기한과 국가는 패치를 따라간다."""

    id: str = field(default_factory=new_id)
    name: str = ""
    preset_name: str = ""
    items: list = field(default_factory=list)

    @property
    def progress(self) -> tuple[int, int]:
        done = sum(1 for i in self.items if i.done)
        return done, len(self.items)

    @property
    def is_done(self) -> bool:
        done, total = self.progress
        return total > 0 and done == total

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "preset_name": self.preset_name,
            "items": [i.to_dict() for i in self.items],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Checklist":
        return cls(
            id=d.get("id") or new_id(),
            name=d.get("name", ""),
            preset_name=d.get("preset_name", ""),
            items=[ChecklistItem.from_dict(i) for i in d.get("items", [])],
        )


@dataclass
class Patch:
    """최상위 단위: 패치일 + 국가. 안의 체크리스트는 이 국가의 경로로 생성된다."""

    id: str = field(default_factory=new_id)
    name: str = ""
    country: str = "KR"
    due_date: str = ""  # YYYY-MM-DD (패치일)
    created_at: str = ""
    completed_at: str | None = None
    checklists: list = field(default_factory=list)

    @property
    def country_name(self) -> str:
        return COUNTRIES.get(self.country, self.country)

    @property
    def progress(self) -> tuple[int, int]:
        done = sum(c.progress[0] for c in self.checklists)
        total = sum(c.progress[1] for c in self.checklists)
        return done, total

    @property
    def percent(self) -> int:
        done, total = self.progress
        return round(done / total * 100) if total else 0

    @property
    def is_done(self) -> bool:
        done, total = self.progress
        return total > 0 and done == total

    @property
    def is_archived(self) -> bool:
        return self.completed_at is not None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "country": self.country,
            "due_date": self.due_date,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "checklists": [c.to_dict() for c in self.checklists],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Patch":
        return cls(
            id=d.get("id") or new_id(),
            name=d.get("name", ""),
            country=d.get("country", "KR"),
            due_date=d.get("due_date", ""),
            created_at=d.get("created_at", ""),
            completed_at=d.get("completed_at"),
            checklists=[Checklist.from_dict(c) for c in d.get("checklists", [])],
        )


def create_checklist_from_preset(preset: Preset, country: str, name: str) -> Checklist:
    """프리셋에서 체크리스트 생성. 경로는 패치의 국가 것으로 확정된다."""
    items = [
        ChecklistItem(description=pi.description, path=pi.paths.get(country, ""))
        for pi in preset.items
    ]
    return Checklist(name=name, preset_name=preset.name, items=items)
