"""오프스크린 스모크 테스트: 샘플 데이터로 각 화면을 렌더링하고 스크린샷 저장.

실행: QT_QPA_PLATFORM=offscreen python tests/smoke_test.py [스크린샷_저장_폴더]
"""
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.models import (
    Patch,
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
            PresetItem("번역 파일 검수", {"KR": "/tmp", "TW": "/tmp", "JP": "/tmp"}),
            PresetItem("패치노트 작성", {"KR": "/없는/경로/patchnote.md", "TW": "", "JP": ""}),
            PresetItem("QA 전달", {"KR": "", "TW": "", "JP": ""}),
        ],
    )
    storage.presets.append(preset)

    today = date.today()

    # 진행 중인 패치: 한국/일본 체크리스트 포함
    patch = Patch(
        name="6/15 패치",
        due_date=(today + timedelta(days=2)).isoformat(),
        created_at="2026-06-01 10:00",
    )
    kr = create_checklist_from_preset(preset, "KR", "정기 빌드 - 한국")
    kr.items[0].status = STATUS_DONE
    kr.items[1].status = STATUS_DONE
    kr.items[1].memo = "폰트 파일은 별도 확인 필요"
    jp = create_checklist_from_preset(preset, "JP", "정기 빌드 - 일본")
    jp.items[0].status = STATUS_DONE
    patch.checklists.extend([kr, jp])

    patch2 = Patch(
        name="7/1 패치",
        due_date=(today + timedelta(days=18)).isoformat(),
        created_at="2026-06-05 10:00",
    )
    patch2.checklists.append(create_checklist_from_preset(preset, "TW", "정기 빌드 - 대만"))

    # 완료된 패치 (보관함)
    done_patch = Patch(
        name="5/20 패치",
        due_date=(today - timedelta(days=21)).isoformat(),
        created_at="2026-05-01 10:00",
        completed_at=(today - timedelta(days=22)).isoformat() + " 18:00",
    )
    for code, name in [("KR", "정기 빌드 - 한국"), ("JP", "정기 빌드 - 일본")]:
        c = create_checklist_from_preset(preset, code, name)
        for item in c.items:
            item.status = STATUS_DONE
        done_patch.checklists.append(c)

    storage.patches.extend([patch, patch2, done_patch])
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

        # 1) 패치 목록
        shot("1_patch_list")

        # 2) 패치 상세 (체크리스트 목록)
        active = storage.active_patches()
        window._open_patch(active[0].id)
        shot("2_patch_detail")

        # 3) 체크리스트 상세 (항목)
        kr = active[0].checklists[0]
        window._open_checklist(kr.id)
        shot("3_checklist_detail")

        # 항목 토글/진행률 집계 확인
        before_patch = active[0].progress
        kr.items[2].status = STATUS_DONE
        storage.save()
        assert active[0].progress[0] == before_patch[0] + 1
        assert 0 < active[0].percent < 100

        # 4) 프리셋 편집기
        window._on_nav(1)
        shot("4_preset_editor")

        # 5) 보관함
        window._on_nav(2)
        shot("5_archive")

        # 저장/재로드 라운드트립 확인
        reloaded = Storage(Path(tmp))
        assert len(reloaded.presets) == 1
        assert len(reloaded.active_patches()) == 2
        assert len(reloaded.archived_patches()) == 1
        assert len(reloaded.active_patches()[0].checklists) == 2
        assert reloaded.active_patches()[0].checklists[0].items[1].memo == "폰트 파일은 별도 확인 필요"
        found_patch, found_checklist = reloaded.find_checklist(
            reloaded.active_patches()[0].checklists[1].id
        )
        assert found_patch is not None and found_checklist.country == "JP"

    print("스모크 테스트 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
