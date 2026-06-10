"""오프스크린 스모크 테스트: 샘플 데이터로 각 화면을 렌더링하고 스크린샷 저장.

실행: QT_QPA_PLATFORM=offscreen python tests/smoke_test.py [스크린샷_저장_폴더]
"""
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.models import (
    Checklist,
    ChecklistItem,
    Preset,
    PresetItem,
    STATUS_DONE,
    create_checklist_from_preset,
)
from app.storage import Storage
from app.style import STYLESHEET


def build_sample(storage: Storage) -> None:
    preset = Preset(
        name="정기 빌드",
        description="월간 빌드 배포 작업",
        items=[
            PresetItem(
                "리소스 파일 교체",
                {"KR": "/tmp/build/kor/resources", "TW": "/tmp/build/tw/resources", "JP": "/tmp/build/jpn/resources"},
            ),
            PresetItem(
                "번역 파일 검수",
                {"KR": "/tmp", "TW": "/tmp", "JP": "/tmp"},
            ),
            PresetItem("패치노트 작성", {"KR": "/없는/경로/patchnote.md", "TW": "", "JP": ""}),
            PresetItem("QA 전달", {"KR": "", "TW": "", "JP": ""}),
        ],
    )
    storage.presets.append(preset)

    today = date.today()
    kr = create_checklist_from_preset(
        preset, "KR", "6월 정기 빌드 - 한국",
        (today + timedelta(days=2)).isoformat(), "2026-06-01 10:00",
    )
    kr.items[0].status = STATUS_DONE
    kr.items[1].status = STATUS_DONE
    kr.items[1].memo = "폰트 파일은 별도 확인 필요"
    jp = create_checklist_from_preset(
        preset, "JP", "6월 정기 빌드 - 일본",
        (today + timedelta(days=9)).isoformat(), "2026-06-01 10:00",
    )
    done = create_checklist_from_preset(
        preset, "TW", "5월 정기 빌드 - 대만",
        (today - timedelta(days=20)).isoformat(), "2026-05-01 10:00",
    )
    for item in done.items:
        item.status = STATUS_DONE
    done.completed_at = (today - timedelta(days=22)).isoformat() + " 18:00"
    storage.checklists.extend([kr, jp, done])
    storage.save()


def main() -> int:
    shot_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    with tempfile.TemporaryDirectory() as tmp:
        storage = Storage(Path(tmp))
        build_sample(storage)

        window = MainWindow(storage)
        window.show()
        app.processEvents()

        def shot(name: str) -> None:
            if shot_dir:
                shot_dir.mkdir(parents=True, exist_ok=True)
                app.processEvents()
                window.grab().save(str(shot_dir / f"{name}.png"))

        # 1) 체크리스트 목록
        shot("1_checklist_list")

        # 2) 상세 화면
        active = storage.active_checklists()
        window._open_detail(active[0].id)
        shot("2_checklist_detail")

        # 항목 토글 동작 확인
        checklist = active[0]
        before = checklist.progress
        checklist.items[2].status = STATUS_DONE
        storage.save()
        assert checklist.progress[0] == before[0] + 1

        # 3) 프리셋 편집기
        window._on_nav(1)
        shot("3_preset_editor")

        # 4) 보관함
        window._on_nav(2)
        shot("4_archive")

        # 저장/재로드 라운드트립 확인
        reloaded = Storage(Path(tmp))
        assert len(reloaded.presets) == 1
        assert len(reloaded.presets[0].items) == 4
        assert len(reloaded.active_checklists()) == 2
        assert len(reloaded.archived_checklists()) == 1
        assert reloaded.active_checklists()[0].items[1].memo == "폰트 파일은 별도 확인 필요"

    print("스모크 테스트 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
