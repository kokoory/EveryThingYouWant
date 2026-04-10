# Requirements Graph Manager

IBM DOORS 스타일의 그래프 기반 요구사항 관리 도구입니다.
NetworkX 그래프 엔진 + FastAPI 백엔드 + 웹 UI로 구성되어 있습니다.

## 실행 방법

```bash
pip install -r requirements.txt
python run.py
```

브라우저에서 `http://localhost:8000` 접속 후 **Demo Data** 버튼을 클릭하면 샘플 데이터가 로드됩니다.

## 프로젝트 구조

```
backend/
├── models.py          # 데이터 모델 (Node, Link, Baseline 등)
├── graph_engine.py    # 핵심 그래프 엔진 (NetworkX 기반)
└── app.py             # FastAPI REST API 서버
frontend/
└── index.html         # 웹 UI (Graph + Tree + Table 뷰)
data/                  # 프로젝트 데이터 저장 (자동 생성)
├── requirements.json  # 노드/링크/베이스라인/히스토리
└── attachments/       # 첨부파일 (근거자료)
run.py                 # 서버 실행 스크립트
requirements.txt       # Python 의존성
```

## 핵심 기능

### 1. 그래프 기반 요구사항 관리

노드(Node)와 링크(Link)로 요구사항 간의 관계를 관리합니다.

**노드 타입:**

| 타입 | 설명 | 색상 |
|---|---|---|
| Requirement | 시스템 요구사항 | 파란색 |
| Specification | 설계 사양 | 보라색 |
| Test Case | 테스트 케이스 | 초록색 |
| Design | 상세 설계 | 노란색 |
| Risk | 위험 요소 | 빨간색 |

**링크 타입:**

| 타입 | 의미 |
|---|---|
| Derives From | ~에서 파생됨 |
| Satisfies | ~을 충족함 |
| Verified By | ~에 의해 검증됨 |
| Traces To | ~으로 추적됨 |
| Mitigated By | ~에 의해 완화됨 |

### 2. 노드 속성

각 노드는 다음 속성을 가집니다:

- **ID**: 고유 식별자 (예: SYS-001, SPC-001, TST-001)
- **Title / Content**: 제목 및 상세 내용
- **Type**: Requirement / Specification / Test Case / Design / Risk
- **Priority**: Critical / High / Medium / Low
- **Status**: Draft / Review / Approved / Suspect
- **Verification Method**: Inspection(검사) / Analysis(분석) / Demonstration(시연) / Test(시험)
- **Subsystem**: SS / GCS / DLS / AVS (동적으로 추가/삭제 가능)
- **Version**: 수정할 때마다 자동 증가
- **Attachments**: 근거자료 파일 첨부

### 3. Suspect Link (의심 링크)

상위 노드가 변경되면 연결된 하위 노드들이 자동으로 **Suspect** 상태가 됩니다.

- 그래프에서 **빨간색 점선**으로 표시
- 하위 노드에 **빨간 테두리 + ! 표시**
- Suspects 탭에서 목록 확인 가능
- **Resolve** 버튼으로 노드 단위 또는 링크 단위로 해제

**처리 흐름:**
1. SYS-001 요구사항을 수정
2. 연결된 SPC-001, TST-001이 자동으로 Suspect 상태로 변경
3. 각 항목을 검토한 후 Resolve 클릭하여 해제

### 4. 버전 관리 (Baseline)

특정 시점의 상태를 스냅샷으로 저장하고 비교할 수 있습니다.

- **Baseline 버튼**: 현재 상태를 이름 + 설명과 함께 저장
- **Compare 버튼**: 두 베이스라인 간 차이 비교 (Added / Removed / Modified)
- **Restore**: 이전 베이스라인 상태로 복원
- 변경된 노드의 필드별 상세 diff 표시

### 5. 버전 히스토리

노드를 수정할 때마다 변경 이력이 자동 기록됩니다.

- 버전 번호 + 날짜 + 변경된 필드(이전값 → 새값)
- Detail 패널의 **Version History** 섹션에서 확인

### 6. Subsystem 관리

서브시스템 목록을 동적으로 관리합니다.

- 기본 목록: SS, GCS, DLS, AVS
- **Subsystems 버튼**: 추가/삭제 관리 모달
- 사용 중인 서브시스템은 삭제 불가 (노드 수 표시)
- 노드 생성/편집 시 드롭다운으로 선택

### 7. 첨부파일 (근거자료)

각 노드에 검증 근거자료를 첨부할 수 있습니다.

- 노드 상세 패널 하단의 **Attachments** 섹션
- 파일 선택 + 설명 입력 후 **Upload**
- PDF, 이미지, 문서, 엑셀 등 모든 파일 형식 지원
- 클릭 시 새 탭에서 열림
- 보고서 출력 시 첨부파일 링크 포함

### 8. 영향도 분석 (Impact Analysis)

특정 노드가 변경될 때 영향받는 모든 하위 항목을 BFS로 추적합니다.

- 노드 상세 패널에서 **Analyze Impact** 클릭
- 그래프 뷰에서 노드 **더블클릭**으로도 실행
- 영향 깊이(Depth)별로 하위 노드 목록 표시

## 뷰 (View)

### Graph View
- vis.js 기반 인터랙티브 그래프 시각화
- 노드 클릭 → 상세 패널 / 더블클릭 → 영향도 분석
- 마우스 드래그로 이동, 스크롤로 확대/축소
- 노드 타입별 색상, Suspect 노드는 빨간 테두리

### Tree View (사이드바)
- 요구사항 계층 구조를 트리 형태로 표시
- 루트 노드(incoming link 없는 노드) 기준 자동 정렬
- Suspect 노드는 빨간 마크 표시

### Table View
- 전체 노드를 테이블로 표시
- ID, Title, Type, Status, Priority, Verification, Subsystem, Version, Updated 컬럼

## 내보내기 (Export)

| 버튼 | 기능 |
|---|---|
| **CSV** | 트리 구조를 CSV 파일로 다운로드 (엑셀 호환, 계층 들여쓰기 포함) |
| **PDF** | 그래프 뷰를 이미지로 캡처하여 인쇄/PDF 저장 |
| **Report** | 종합 보고서 HTML 생성 (새 탭에서 열림, Ctrl+P로 PDF 저장) |

### Report 보고서 내용
1. **통계 요약**: 노드/링크/Suspect/서브시스템/베이스라인 수
2. **Suspect 경고**: 미해결 Suspect 항목 목록
3. **계층 트리**: 전체 요구사항 트리 구조
4. **추적성 매트릭스**: 전체 링크 테이블
5. **노드 상세**: 각 노드별 카드 (속성, 연결, 첨부파일, 버전 이력)

## 백업 / 복원

### Backup
헤더의 **Backup** 버튼 → ZIP 파일 다운로드

```
rgm_backup_20260410.zip
├── project_data.json     ← 노드/링크/베이스라인/서브시스템/히스토리
├── attachments/          ← 모든 첨부파일
└── backup_meta.json      ← 백업 메타정보
```

### Restore
헤더의 **Restore** 버튼 → ZIP 파일 선택 → 확인 → 복원 완료

복원되는 데이터:

| 항목 | 포함 |
|---|---|
| 노드 (속성, verification, subsystem) | O |
| 링크 (suspect 상태 포함) | O |
| 베이스라인 (스냅샷 전체) | O |
| 서브시스템 리스트 | O |
| 버전 히스토리 | O |
| 변경 이력 (최근 100건) | O |
| 첨부파일 (근거자료) | O |

## API 목록

| Method | Endpoint | 설명 |
|---|---|---|
| GET | `/api/nodes` | 전체 노드 조회 |
| POST | `/api/nodes` | 노드 생성 |
| GET | `/api/nodes/{id}` | 노드 상세 조회 |
| PUT | `/api/nodes/{id}` | 노드 수정 |
| DELETE | `/api/nodes/{id}` | 노드 삭제 |
| GET | `/api/links` | 전체 링크 조회 |
| POST | `/api/links` | 링크 생성 |
| DELETE | `/api/links/{src}/{tgt}` | 링크 삭제 |
| GET | `/api/suspects/nodes` | Suspect 노드 목록 |
| GET | `/api/suspects/links` | Suspect 링크 목록 |
| POST | `/api/suspects/{id}/resolve` | Suspect 노드 해제 |
| POST | `/api/suspects/link/resolve` | Suspect 링크 해제 |
| GET | `/api/impact/{id}` | 영향도 분석 |
| GET | `/api/baselines` | 베이스라인 목록 |
| POST | `/api/baselines` | 베이스라인 생성 |
| POST | `/api/baselines/{name}/restore` | 베이스라인 복원 |
| GET | `/api/baselines/compare` | 베이스라인 비교 |
| GET | `/api/tree` | 트리 뷰 |
| GET | `/api/graph/vis` | 그래프 시각화 데이터 |
| GET | `/api/subsystems` | 서브시스템 목록 |
| POST | `/api/subsystems` | 서브시스템 추가 |
| DELETE | `/api/subsystems/{name}` | 서브시스템 삭제 |
| POST | `/api/nodes/{id}/attachments` | 첨부파일 업로드 |
| GET | `/api/attachments/{name}` | 첨부파일 다운로드 |
| DELETE | `/api/nodes/{id}/attachments/{fid}` | 첨부파일 삭제 |
| GET | `/api/export/csv` | CSV 내보내기 |
| GET | `/api/report` | 종합 보고서 HTML |
| GET | `/api/backup` | 백업 ZIP 다운로드 |
| POST | `/api/restore` | 백업 복원 |
| GET | `/api/stats` | 통계 |
| GET | `/api/history` | 변경 이력 |
| POST | `/api/demo/load` | 데모 데이터 로드 |

## 기술 스택

| 레이어 | 기술 |
|---|---|
| Graph Engine | NetworkX (Python) |
| Backend | FastAPI + Uvicorn |
| Frontend | HTML/CSS/JS + vis-network.js |
| Data Storage | JSON 파일 + 파일 시스템 |

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참고하세요.
