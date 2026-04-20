# 설치 가이드 (Installation Guide)

Requirements Graph Manager를 **Python 3.12** 환경에서 설치하고 실행하는 방법입니다.

## 사전 준비

### Python 3.12 설치

| OS | 설치 방법 |
|---|---|
| **Windows** | https://www.python.org/downloads/ 에서 Python 3.12 다운로드 후 설치 (반드시 "Add Python to PATH" 체크) |
| **macOS** | `brew install python@3.12` 또는 https://www.python.org/downloads/macos/ |
| **Ubuntu/Debian** | `sudo apt install python3.12 python3.12-venv` |

설치 확인:
```bash
python --version    # 또는 python3.12 --version
# 출력: Python 3.12.x
```

## 오프라인 설치 지원

`setup/wheels/` 폴더에 모든 의존성 패키지(`.whl`)가 미리 다운로드되어 있습니다.
인터넷 연결이 없는 환경에서도 자동 설치 스크립트가 이 폴더를 우선 사용합니다.

```
setup/wheels/
├── windows/        # Windows x64 (33개 패키지)
├── linux/          # Linux x64 (33개 패키지)
├── macos_arm64/    # macOS Apple Silicon (33개 패키지)
└── macos_intel/    # macOS Intel x64 (33개 패키지)
```

설치 스크립트가 자동으로 OS를 감지하여 적절한 wheel 폴더를 사용합니다.

## 자동 설치 (권장)

### Windows

1. 프로젝트 폴더에서 파일 탐색기로 `setup` 폴더 진입
2. `install_windows.bat` **더블클릭** 실행
3. 가상환경 생성 + 의존성 설치 자동 진행
4. 설치 완료 후 `run_windows.bat` 더블클릭으로 서버 시작

### macOS / Linux

```bash
cd EveryThingYouWant
./setup/install_unix.sh
./setup/run_unix.sh
```

## 수동 설치

```bash
# 1. 프로젝트 폴더로 이동
cd EveryThingYouWant

# 2. Python 3.12 가상환경 생성
python3.12 -m venv venv

# 3. 가상환경 활성화
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 4. 의존성 설치
pip install --upgrade pip
pip install -r setup/requirements.txt

# 5. 서버 실행
python run.py
```

## 접속

서버 실행 후 브라우저에서:

```
http://localhost:8000
```

처음 실행 시 화면에서 **Demo Data** 버튼을 클릭하면 샘플 요구사항 데이터가 로드됩니다.

## 의존성 패키지

| 패키지 | 버전 | 용도 |
|---|---|---|
| fastapi | 0.115.5 | REST API 웹 프레임워크 |
| uvicorn | 0.32.1 | ASGI 서버 |
| python-multipart | 0.0.18 | 파일 업로드 처리 |
| pydantic | 2.10.3 | 데이터 검증 |
| networkx | 3.4.2 | 그래프 엔진 |
| jinja2 | 3.1.4 | 템플릿 엔진 |
| pyvis | 0.3.2 | 그래프 시각화 보조 |

## 문제 해결

### "python" 명령을 찾을 수 없음 (Windows)
- Python 설치 시 "Add Python to PATH" 체크 안 한 경우 발생
- Python 재설치 또는 환경 변수에 Python 경로 수동 추가

### 포트 8000이 이미 사용 중
- 다른 프로그램이 8000 포트 사용 중. 종료하거나 `run.py`에서 포트 번호 변경:
  ```python
  uvicorn.run("backend.app:app", host="0.0.0.0", port=8001, reload=True)
  ```

### 패키지 설치 실패 (Windows)
- Visual C++ Build Tools 필요할 수 있음
- https://visualstudio.microsoft.com/visual-cpp-build-tools/ 에서 설치

### macOS에서 SSL 인증서 오류
```bash
/Applications/Python\ 3.12/Install\ Certificates.command
```

### 가상환경 재생성
```bash
# 기존 venv 삭제 후 재설치
rm -rf venv          # macOS/Linux
rmdir /s venv        # Windows
./setup/install_unix.sh  # 또는 install_windows.bat
```

## 데이터 위치

프로그램 실행 시 자동으로 `data/` 폴더가 생성됩니다:

```
EveryThingYouWant/
└── data/
    ├── requirements.json     ← 노드/링크/베이스라인 등 모든 데이터
    └── attachments/          ← 첨부파일 저장 폴더
        └── *.pdf, *.png 등
```

**중요**: 데이터 백업은 헤더의 **Backup** 버튼으로 ZIP 파일을 다운로드받으면 됩니다.
새 환경에서는 **Restore** 버튼으로 ZIP 파일을 업로드해서 복원하세요.

## 폴더 구조

```
EveryThingYouWant/
├── backend/              # 백엔드 코드
│   ├── app.py            # FastAPI 앱
│   ├── graph_engine.py   # 그래프 엔진
│   └── models.py         # 데이터 모델
├── frontend/             # 프론트엔드 코드
│   └── index.html        # 단일 페이지 웹 UI
├── setup/                # 설치 관련 파일 (이 폴더)
│   ├── INSTALL.md        # 이 문서
│   ├── requirements.txt  # Python 의존성
│   ├── install_windows.bat
│   ├── install_unix.sh
│   ├── run_windows.bat
│   └── run_unix.sh
├── data/                 # (자동 생성) 데이터 저장
├── venv/                 # (자동 생성) Python 가상환경
├── run.py                # 서버 실행 진입점
├── requirements.txt      # 루트 의존성 (setup/과 동일)
├── README.md             # 프로젝트 설명서
└── LICENSE
```
