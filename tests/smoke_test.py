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
    Checklist,
    ChecklistItem,
    Patch,
    Preset,
    PresetItem,
    ResourceEntry,
    STATUS_DONE,
    create_checklist_from_preset,
    join_base,
)
from app.storage import Storage
from app.style import STYLESHEET


def build_sample(storage: Storage) -> None:
    # 설정: 빌드별 기본 폴더
    storage.base_paths().update({"KR": "/tmp", "TW": "/tmp", "JP": "/tmp"})

    hero_preset = Preset(
        name="영웅 추가",
        description="신규 영웅 추가 작업",
        items=[
            PresetItem(  # 공통 모드: 기본 폴더 + 상대 경로
                "Gacha 테이블 수정",
                folder="Assets/DB",
                file="gacha_table.json",
                children=[
                    PresetItem("상시 소환 수정"),
                    PresetItem("상시 소환 수정에서 기원 무기 추가"),
                    PresetItem("픽업 소환풀에 영웅 추가"),
                ],
            ),
            PresetItem("스킬 테이블 갱신", folder="Assets/DB", file="skill_table.json"),
            PresetItem(  # 예외 모드: 국가별 따로 입력
                "일러스트 리소스 반영",
                per_country=True,
                paths={
                    "KR": {"folder": "/없는/경로/illust", "file": ""},
                    "TW": {"folder": "", "file": ""},
                    "JP": {"folder": "", "file": ""},
                },
            ),
            PresetItem("밸런스 검수"),
        ],
    )
    shop_preset = Preset(
        name="상점 업데이트",
        description="상점 상품 교체",
        items=[
            PresetItem("상품 테이블 교체", folder="Assets/Shop", file="shop.json"),
            PresetItem("배너 이미지 교체", folder="Assets/Banners"),
        ],
    )
    storage.presets.extend([hero_preset, shop_preset])

    today = date.today()
    bases = storage.base_paths()

    # 진행 중인 패치 (한국)
    kr_patch = Patch(
        name="6/15 한국 패치",
        country="KR",
        due_date=(today + timedelta(days=2)).isoformat(),
        created_at="2026-06-01 10:00",
    )
    hero = create_checklist_from_preset(hero_preset, "KR", "영웅 추가", bases)
    hero.items[0].children[0].status = STATUS_DONE
    hero.items[0].children[1].status = STATUS_DONE
    hero.items[1].status = STATUS_DONE
    hero.items[1].memo = "신규 스킬 이펙트는 별도 확인 필요"
    shop = create_checklist_from_preset(shop_preset, "KR", "상점 업데이트", bases)
    # 즉석(프리셋 없는) 체크리스트 + 직접 추가한 항목
    adhoc = Checklist(
        name="긴급 핫픽스",
        items=[
            ChecklistItem(description="크래시 원인 파악", folder="/tmp", file="crash.log"),
            ChecklistItem(description="수정 빌드 배포"),
        ],
    )
    kr_patch.checklists.extend([hero, shop, adhoc])

    # 진행 중인 패치 (일본)
    jp_patch = Patch(
        name="6/22 일본 패치",
        country="JP",
        due_date=(today + timedelta(days=9)).isoformat(),
        created_at="2026-06-05 10:00",
    )
    jp_patch.checklists.append(
        create_checklist_from_preset(hero_preset, "JP", "영웅 추가", bases)
    )

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
        c = create_checklist_from_preset(hero_preset, code, "영웅 추가", bases)
        for item in c.items:
            item.set_done(True)
        p.checklists.append(c)
        done_patches.append(p)

    storage.patches.extend([kr_patch, jp_patch, *done_patches])

    storage.resources.extend([
        ResourceEntry(name="영웅 아이콘", folder="/tmp", file=""),
        ResourceEntry(name="배너 일러스트", folder="/tmp/build/kor/banners", file="banner.png"),
        ResourceEntry(name="사운드 리소스", folder="/없는/경로/sounds", file=""),
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

        # 3) 체크리스트 상세 (하위 항목 포함)
        hero = active[0].checklists[0]
        window._open_checklist(hero.id)
        shot("3_checklist_detail")

        # 기본 폴더 + 상대 경로 조합 확인
        assert hero.items[0].folder == "/tmp/Assets/DB"
        assert hero.items[0].file == "gacha_table.json"
        assert hero.items[2].folder == "/없는/경로/illust"  # 국가별 예외 모드
        assert join_base("C:\\00.SVN\\00.KR_LOH_Trunk", "Assets\\DB") == "C:\\00.SVN\\00.KR_LOH_Trunk\\Assets\\DB"
        assert join_base("/base", "C:\\abs\\path") == "C:\\abs\\path"  # 절대 경로는 그대로
        assert join_base("", "Assets/DB") == "Assets/DB"  # 기본 폴더 미설정

        # 하위 항목/진행률 동작 확인
        gacha = hero.items[0]
        assert gacha.has_children and not gacha.is_done
        gacha.children[2].status = STATUS_DONE
        assert gacha.is_done  # 하위 전부 완료 → 부모 완료
        gacha.set_done(False)
        assert not gacha.is_done
        gacha.set_done(True)  # 부모 일괄 토글
        assert all(c.is_done for c in gacha.children)
        done, total = hero.progress
        assert total == 6  # 최하위 기준: 하위 3 + 일반 3
        storage.save()

        # 4) 프리셋 편집기 (하위 항목 트리 + 공통/국가별 모드)
        window._on_nav(1)
        shot("4_preset_editor")

        # 5) 리소스 경로
        window._on_nav(2)
        shot("5_resources")

        # 6) 보관함 (국가 그룹핑)
        window._on_nav(3)
        shot("6_archive")

        # 7) 설정 (빌드별 기본 폴더)
        window._on_nav(4)
        shot("7_settings")

        # 저장/재로드 라운드트립 확인
        reloaded = Storage(Path(tmp))
        assert reloaded.base_paths()["KR"] == "/tmp"
        assert len(reloaded.presets) == 2
        assert reloaded.presets[0].items[0].per_country is False
        assert reloaded.presets[0].items[0].folder == "Assets/DB"
        assert reloaded.presets[0].items[2].per_country is True
        assert len(reloaded.active_patches()) == 2
        assert len(reloaded.archived_patches()) == 2
        first = reloaded.active_patches()[0]
        assert first.country == "KR"
        assert len(first.checklists) == 3
        assert first.checklists[0].items[0].children[0].description == "상시 소환 수정"
        assert first.checklists[2].preset_name == ""  # 즉석 체크리스트
        assert reloaded.resources[1].file == "banner.png"

        # 구버전 데이터 호환 확인
        old_item = ChecklistItem.from_dict({"description": "옛 항목", "path": "/old/path"})
        assert old_item.folder == "/old/path" and old_item.file == ""
        old_preset_item = PresetItem.from_dict({"description": "옛", "paths": {"KR": "/old/kr"}})
        assert old_preset_item.per_country is True  # 국가별 입력 데이터는 예외 모드 유지
        assert old_preset_item.paths["KR"]["folder"] == "/old/kr"
        old_resource = ResourceEntry.from_dict({"name": "옛 리소스", "path": "/old/res"})
        assert old_resource.folder == "/old/res"

    print("스모크 테스트 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
