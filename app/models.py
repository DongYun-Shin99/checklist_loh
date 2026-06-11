"""데이터 모델: 프리셋(템플릿) / 패치 / 체크리스트 / 항목 / 리소스 경로.

구조: 패치(패치일+국가) → 체크리스트 → 항목 (→ 하위 항목 1단계)
경로는 폴더/파일로 분리되어 저장된다.
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


def _normalize_path_entry(value) -> dict:
    """경로 항목 정규화. 구버전(문자열 하나) 데이터는 폴더 칸으로 호환 처리."""
    if isinstance(value, str):
        return {"folder": value, "file": ""}
    if isinstance(value, dict):
        return {"folder": value.get("folder", ""), "file": value.get("file", "")}
    return {"folder": "", "file": ""}


def _empty_paths() -> dict:
    return {code: {"folder": "", "file": ""} for code in COUNTRIES}


@dataclass
class PresetItem:
    description: str = ""
    paths: dict = field(default_factory=_empty_paths)  # {국가: {folder, file}}
    children: list = field(default_factory=list)  # list[PresetItem], 1단계만 사용

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "paths": {code: dict(p) for code, p in self.paths.items()},
            "children": [c.to_dict() for c in self.children],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PresetItem":
        paths = _empty_paths()
        for code, value in d.get("paths", {}).items():
            if code in paths:
                paths[code] = _normalize_path_entry(value)
        return cls(
            description=d.get("description", ""),
            paths=paths,
            children=[PresetItem.from_dict(c) for c in d.get("children", [])],
        )


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
    folder: str = ""
    file: str = ""
    status: str = STATUS_IN_PROGRESS
    memo: str = ""
    children: list = field(default_factory=list)  # list[ChecklistItem], 1단계만 사용

    @property
    def has_children(self) -> bool:
        return bool(self.children)

    @property
    def is_done(self) -> bool:
        """하위 항목이 있으면 전부 완료됐을 때 완료로 본다."""
        if self.children:
            return all(c.is_done for c in self.children)
        return self.status == STATUS_DONE

    def set_done(self, done: bool) -> None:
        """완료 상태 설정. 하위 항목이 있으면 일괄 적용."""
        self.status = STATUS_DONE if done else STATUS_IN_PROGRESS
        for child in self.children:
            child.set_done(done)

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "folder": self.folder,
            "file": self.file,
            "status": self.status,
            "memo": self.memo,
            "children": [c.to_dict() for c in self.children],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ChecklistItem":
        # 구버전 호환: "path" 하나만 있던 데이터는 폴더 칸으로
        folder = d.get("folder", "")
        if not folder and d.get("path"):
            folder = d["path"]
        return cls(
            description=d.get("description", ""),
            folder=folder,
            file=d.get("file", ""),
            status=d.get("status", STATUS_IN_PROGRESS),
            memo=d.get("memo", ""),
            children=[ChecklistItem.from_dict(c) for c in d.get("children", [])],
        )


def iter_leaves(items: list) -> list:
    """진행률 계산용: 최하위 항목들만 모은다 (하위가 있으면 하위만 센다)."""
    leaves = []
    for item in items:
        if item.children:
            leaves.extend(iter_leaves(item.children))
        else:
            leaves.append(item)
    return leaves


@dataclass
class Checklist:
    """패치 안에 들어가는 작업 묶음(예: 영웅 추가). 기한과 국가는 패치를 따라간다."""

    id: str = field(default_factory=new_id)
    name: str = ""
    preset_name: str = ""
    items: list = field(default_factory=list)

    @property
    def progress(self) -> tuple[int, int]:
        leaves = iter_leaves(self.items)
        done = sum(1 for i in leaves if i.status == STATUS_DONE)
        return done, len(leaves)

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


@dataclass
class ResourceEntry:
    """리소스 경로 항목: 자주 쓰는 폴더/파일 바로가기 (아이콘, 일러스트 등)."""

    id: str = field(default_factory=new_id)
    name: str = ""
    folder: str = ""
    file: str = ""

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "folder": self.folder, "file": self.file}

    @classmethod
    def from_dict(cls, d: dict) -> "ResourceEntry":
        # 구버전 호환: "path" 하나만 있던 데이터는 폴더 칸으로
        folder = d.get("folder", "")
        if not folder and d.get("path"):
            folder = d["path"]
        return cls(
            id=d.get("id") or new_id(),
            name=d.get("name", ""),
            folder=folder,
            file=d.get("file", ""),
        )


def create_checklist_from_preset(preset: Preset, country: str, name: str) -> Checklist:
    """프리셋에서 체크리스트 생성. 경로는 패치의 국가 것으로 확정된다."""

    def convert(pi: PresetItem) -> ChecklistItem:
        path = pi.paths.get(country, {})
        return ChecklistItem(
            description=pi.description,
            folder=path.get("folder", ""),
            file=path.get("file", ""),
            children=[convert(c) for c in pi.children],
        )

    return Checklist(
        name=name,
        preset_name=preset.name,
        items=[convert(i) for i in preset.items],
    )
