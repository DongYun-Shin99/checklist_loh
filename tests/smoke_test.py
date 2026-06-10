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
    ResourceEntry,
    STATUS_DONE,
    create_checklist_from_preset,
)
from app.storage import Storage
from app.style import STYLESHEET


def build_sample(storage: Storage) -> None:
    hero_preset = Preset(
        name="영웅 추가",
        description="신규 영웅 추가 작업",
        items=[
            PresetItem(
                "영웅 데이터 수정",
                {"KR": "/tmp/build/kor/heroes", "TW": "/tmp/build/tw/heroes", "JP": "/tmp/build/jpn/heroes"},
            ),
            PresetItem("스킬 테이블 갱신", {"KR": "/tmp", "TW": "/tmp", "JP": "/tmp"}),
            PresetItem("일러스트 리소스 반영", {"KR": "/없는/경로/illust", "TW": "", "JP": ""}),
            PresetItem("밸런스 검수", {"KR": "", "TW": "", "JP": ""}),
        ],
    )
    shop_preset = Preset(
        name="상점 업데이트",
        description="상점 상품 교체",
        items=[
            PresetItem("상품 테이블 교체", {"KR": "/tmp", "TW": "/tmp", "JP": "/tmp"}),
            PresetItem("배너 이미지 교체", {"KR": "/tmp", "TW": "/tmp", "JP": "/tmp"}),
        ],
    )
    storage.presets.extend([hero_preset, shop_preset])

    today = date.today()

    # 진행 중인 패치 (한국)
    kr_patch = Patch(
        name="6/15 한국 패치",
        country="KR",
        due_date=(today + timedelta(days=2)).isoformat(),
        created_at="2026-06-01 10:00",
    )
    hero = create_checklist_from_preset(hero_preset, "KR", "영웅 추가")
    hero.items[0].status = STATUS_DONE
    hero.items[1].status = STATUS_DONE
    hero.items[1].memo = "신규 스킬 이펙트는 별도 확인 필요"
    shop = create_checklist_from_preset(shop_preset, "KR", "상점 업데이트")
    kr_patch.checklists.extend([hero, shop])

    # 진행 중인 패치 (일본)
    jp_patch = Patch(
        name="6/22 일본 패치",
        country="JP",
        due_date=(today + timedelta(days=9)).isoformat(),
        created_at="2026-06-05 10:00",
    )
    jp_patch.checklists.append(create_checklist_from_preset(hero_preset, "JP", "영웅 추가"))

    # 완료된 패치 (보관함, 한국/대만)
    done_patches = []
    for code, name, days in [("KR", "5/20 한국 패치", 21), ("TW", "5/20 대만 패치", 21)]:
        p = Patch(
            name=name,
            country=code,
            due_date=(today - timedelta(days=days)).isoformat(),
            created_at="2026-05-01 10:00",
            completed_at=(today - timedelta(days=days + 1)).isoformat() + " 18:00",
        )
        c = create_checklist_from_preset(hero_preset, code, "영웅 추가")
        for item in c.items:
            item.status = STATUS_DONE
        p.checklists.append(c)
        done_patches.append(p)

    storage.patches.extend([kr_patch, jp_patch, *done_patches])

    storage.resources.extend([
        ResourceEntry(name="영웅 아이콘", path="/tmp"),
        ResourceEntry(name="배너 일러스트", path="/tmp/build/kor/banners"),
        ResourceEntry(name="사운드 리소스", path="/없는/경로/sounds"),
    ])
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

        # 2) 패치 상세 (작업 묶음 목록)
        active = storage.active_patches()
        window._open_patch(active[0].id)
        shot("2_patch_detail")

        # 3) 체크리스트 상세 (세세한 항목)
        hero = active[0].checklists[0]
        window._open_checklist(hero.id)
        shot("3_checklist_detail")

        # 항목 토글/진행률 집계 확인
        before_patch = active[0].progress
        hero.items[2].status = STATUS_DONE
        storage.save()
        assert active[0].progress[0] == before_patch[0] + 1
        assert 0 < active[0].percent < 100

        # 4) 프리셋 편집기
        window._on_nav(1)
        shot("4_preset_editor")

        # 5) 리소스 경로
        window._on_nav(2)
        shot("5_resources")

        # 6) 보관함 (국가 그룹핑)
        window._on_nav(3)
        shot("6_archive")

        # 저장/재로드 라운드트립 확인
        reloaded = Storage(Path(tmp))
        assert len(reloaded.presets) == 2
        assert len(reloaded.active_patches()) == 2
        assert len(reloaded.archived_patches()) == 2
        assert reloaded.active_patches()[0].country == "KR"
        assert len(reloaded.active_patches()[0].checklists) == 2
        assert reloaded.active_patches()[0].checklists[0].items[1].memo == "신규 스킬 이펙트는 별도 확인 필요"
        found_patch, found_checklist = reloaded.find_checklist(
            reloaded.active_patches()[1].checklists[0].id
        )
        assert found_patch is not None and found_patch.country == "JP"
        assert len(reloaded.resources) == 3
        assert reloaded.resources[0].name == "영웅 아이콘"

    print("스모크 테스트 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
