"""데이터 모델: 프리셋(템플릿)과 체크리스트(실제 진행 인스턴스)."""
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
    id: str = field(default_factory=new_id)
    name: str = ""
    preset_name: str = ""
    country: str = "KR"
    due_date: str = ""  # YYYY-MM-DD
    created_at: str = ""
    completed_at: str | None = None
    items: list = field(default_factory=list)

    @property
    def progress(self) -> tuple[int, int]:
        done = sum(1 for i in self.items if i.done)
        return done, len(self.items)

    @property
    def is_archived(self) -> bool:
        return self.completed_at is not None

    @property
    def country_name(self) -> str:
        return COUNTRIES.get(self.country, self.country)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "preset_name": self.preset_name,
            "country": self.country,
            "due_date": self.due_date,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "items": [i.to_dict() for i in self.items],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Checklist":
        return cls(
            id=d.get("id") or new_id(),
            name=d.get("name", ""),
            preset_name=d.get("preset_name", ""),
            country=d.get("country", "KR"),
            due_date=d.get("due_date", ""),
            created_at=d.get("created_at", ""),
            completed_at=d.get("completed_at"),
            items=[ChecklistItem.from_dict(i) for i in d.get("items", [])],
        )


def create_checklist_from_preset(
    preset: Preset, country: str, name: str, due_date: str, created_at: str
) -> Checklist:
    """프리셋에서 체크리스트 인스턴스 생성. 경로는 선택한 국가의 것으로 확정된다."""
    items = [
        ChecklistItem(description=pi.description, path=pi.paths.get(country, ""))
        for pi in preset.items
    ]
    return Checklist(
        name=name,
        preset_name=preset.name,
        country=country,
        due_date=due_date,
        created_at=created_at,
        items=items,
    )
