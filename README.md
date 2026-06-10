# 업무 체크리스트

윈도우용 업무 체크리스트 관리 프로그램. 프리셋(템플릿)으로 반복 작업을 정의하고,
국가(한국/대만/일본)별로 파일 경로가 자동 적용된 체크리스트를 만들어 진행 상황을 관리한다.

## 주요 기능

- **프리셋**: 체크리스트 템플릿. 항목마다 작업 설명 + 국가별 경로 3개(한국/대만/일본) 입력.
  드래그로 순서 변경, JSON 내보내기/불러오기로 공유 가능.
- **체크리스트**: 프리셋 + 국가 + 작업 기한을 정해 생성. 생성 시 경로가 해당 국가 것으로 확정.
  - 항목 상태: 진행중 / 완료
  - 항목별 메모, 경로를 탐색기에서 바로 열기, 없는 경로는 빨간 경고 표시
  - 진행률 바, 기한 D-day 표시 (임박 시 주황, 초과 시 빨강)
- **보관함**: 완료된 체크리스트를 국가 단위로 그룹핑해 보관. 읽기 전용 열람, 복원, 삭제.
- **자동 저장**: 모든 변경은 즉시 `data/app_data.json`에 저장.

## 실행 (개발)

```
pip install -r requirements.txt
python main.py
```

## 윈도우용 exe 빌드

```
pip install pyinstaller
pyinstaller --onefile --windowed --name checklist main.py
```

`dist/checklist.exe` 생성. 데이터는 exe 옆의 `data/` 폴더에 저장된다.

## 테스트

```
QT_QPA_PLATFORM=offscreen python tests/smoke_test.py [스크린샷_폴더]
```

## 구조

```
main.py                      진입점
app/
  models.py                  프리셋/체크리스트 데이터 모델
  storage.py                 JSON 저장소 (자동 저장)
  utils.py                   D-day 계산, 탐색기 열기
  style.py                   QSS 스타일시트
  dialogs.py                 새 체크리스트 생성 / 보관함 상세 다이얼로그
  main_window.py             사이드바 + 페이지 전환
  pages/
    checklists.py            진행 중 체크리스트 목록
    checklist_detail.py      체크리스트 상세 (체크/경로/메모)
    presets.py               프리셋 목록 + 편집기 + 내보내기/불러오기
    archive.py               보관함 (국가별 그룹핑)
```
