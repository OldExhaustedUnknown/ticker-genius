# Ticker-Genius 구현 로드맵

**작성일**: 2026-01-10
**버전**: 3.0
**상태**: 설계 확정, 구현 대기

---

## 1. 목표

### 1.1 프로젝트 목표

FDA PDUFA 승인/CRL 확률 예측 및 제약 주식 거래 신호 시스템

### 1.2 리팩토링 목표

1. **스키마 단일화**: PDUFAEvent를 단일 진실 소스로
2. **레거시 제거**: 45개 일회성 스크립트 아카이브
3. **모듈 정리**: Collection 12개 파일로 통합
4. **주가 연동**: 확률 계산 → 거래 신호 파이프라인

---

## 2. 현재 상태

```
데이터: 523개 enriched JSON 파일
스키마: 혼재 (3종 중복)
스크립트: 66개 (45개 일회성)
분석 모듈: 12개 레이어 완성
MCP: 미구현
```

---

## 3. 구현 단계

### Wave 1: 레거시 정리 (2시간)

| Task | 파일/폴더 | 내용 | 의존성 |
|------|----------|------|--------|
| 1.1 | scripts/_archive/ | 45개 배치 스크립트 아카이브 | 없음 |
| 1.2 | collection/ | 12개 미사용 파일 삭제 | 1.1 |
| 1.3 | enrichment/ | 폴더 전체 삭제 | 1.2 |
| 1.4 | 검증 | 임포트 테스트 | 1.3 |

**결과물**:
- scripts/ 12개 파일
- collection/ 12개 파일
- 모든 테스트 통과

### Wave 2: 스키마 구현 (3시간)

| Task | 파일 | 내용 | 의존성 |
|------|------|------|--------|
| 2.1 | schemas/enums.py | SearchStatus, SourceTier 추가 | Wave 1 |
| 2.2 | schemas/pdufa_event.py | PDUFAEvent + **12개 신규 필드** 구현 | 2.1 |
| 2.3 | schemas/price_models.py | 주가 스키마 구현 | 2.1 |
| 2.4 | schemas/__init__.py | 공개 API 업데이트 | 2.2, 2.3 |
| 2.5 | schemas/pipeline.py | DEPRECATED 표시 | 2.4 |

**신규 12개 필드** (SCHEMA_REDESIGN.md Section 9 참조):
```
사전 수집 (5개): is_single_arm, trial_region, is_biosimilar,
                is_first_in_class, crl_reason_type
캐시+30일 (4개): warning_letter_date, fda_483_date,
                fda_483_observations, cdmo_name
분석시 검색 (3개): pai_passed, pai_date, clinical_hold_history
```

**결과물**:
- PDUFAEvent: StatusField 패턴 + 12개 신규 필드
- PriceHistory, PDUFAPriceWindow 스키마
- TradingSignal 스키마

### Wave 2.5: 신규 필드 수집기 구현 (2시간)

| Task | 파일 | 내용 | 의존성 |
|------|------|------|--------|
| 2.5.1 | collection/nct_enricher.py | is_single_arm, trial_region 수집 (NCT API) | Wave 2 |
| 2.5.2 | collection/biosimilar_detector.py | is_biosimilar 판별 (웹서치→Purple Book→패턴) | Wave 2 |
| 2.5.3 | collection/manufacturing_cache.py | 30일 캐시 (warning_letter, 483) | Wave 2 |
| 2.5.4 | collection/ondemand_searcher.py | 실시간 검색 (PAI, clinical_hold) | Wave 2 |

**결과물**:
- NCT 기반 임상 정보 수집기
- 바이오시밀러 판별 로직
- 제조 정보 캐시 레이어 (30일)
- 분석 시 실시간 검색기

### Wave 3: 데이터 마이그레이션 (1시간)

| Task | 파일 | 내용 | 의존성 |
|------|------|------|--------|
| 3.1 | scripts/migrate_to_v3.py | 마이그레이션 스크립트 작성 | Wave 2 |
| 3.2 | data/enriched_backup_v2/ | 백업 생성 | 3.1 |
| 3.3 | data/enriched/*.json | 523건 마이그레이션 실행 | 3.2 |
| 3.4 | 검증 | PDUFAEvent.load() 전체 검증 | 3.3 |

**마이그레이션 시 처리사항** (SCHEMA_REDESIGN.md Section 9.6 참조):
- adcom_info.vote → vote_ratio 변환
- mechanism_of_action 문자열 → StatusField
- 신규 12개 필드 = not_searched 초기화

**결과물**:
- 523개 JSON 파일 v3 스키마로 변환
- 백업 폴더 생성
- 마이그레이션 스크립트 아카이브

### Wave 4: 분석 파이프라인 연결 (3시간)

| Task | 파일 | 내용 | 의존성 |
|------|------|------|--------|
| 4.1 | analysis/pdufa/_context.py | from_pdufa_event() + 파생 필드 로직 | Wave 3 |
| 4.2 | analysis/pdufa/_layers/clinical.py | **rwe_external_control 제거**, single_arm 패널티 조정 | 4.1 |
| 4.3 | analysis/pdufa/_layers/manufacturing.py | **cdmo_high_risk 제거** | 4.1 |
| 4.4 | analysis/pdufa/_layers/base.py | crl_reason_type 기반 base rate 파생 | 4.1 |
| 4.5 | analysis/runner.py | 분석 실행기 (실시간 검색 통합) | 4.1-4.4, Wave 2.5 |
| 4.6 | 테스트 | 전체 파이프라인 테스트 | 4.5 |

**알고리즘 수정사항** (SCHEMA_REDESIGN.md Section 9.9 참조):
- rwe_external_control → is_single_arm에 통합 (패널티 -5% → -7%)
- cdmo_high_risk → 제거 (warning_letter로 대체)
- crl_reason_type → is_cmc_only 파생, base rate 결정

**파생 필드 로직**:
```python
is_mental_health = therapeutic_area in ["Psychiatry", "Neurology", "CNS"]
is_cmc_only = crl_reason_type == "cmc" if has_prior_crl else False
is_supplement = approval_type in ["snda", "sbla"]
```

**결과물**:
- PDUFAEvent → AnalysisContext 변환 (파생 필드 포함)
- 수정된 확률 계산 알고리즘
- 실시간 검색 통합 분석 실행기

### Wave 5: 주가 수집 (2시간)

| Task | 파일 | 내용 | 의존성 |
|------|------|------|--------|
| 5.1 | collection/price_collector.py | 주가 수집기 구현 | Wave 2 |
| 5.2 | data/prices/ | 주가 데이터 저장 폴더 | 5.1 |
| 5.3 | scripts/collect_prices.py | 주가 수집 스크립트 | 5.1 |
| 5.4 | scripts/build_price_windows.py | 주가 윈도우 생성 | 5.3 |

**결과물**:
- 티커별 주가 히스토리 수집
- PDUFA 이벤트별 주가 윈도우 생성

### Wave 6: 데이터베이스 (선택적, 3시간)

| Task | 파일 | 내용 | 의존성 |
|------|------|------|--------|
| 6.1 | database/schema.sql | 테이블 정의 | Wave 3, 5 |
| 6.2 | repositories/sqlite_repo.py | SQLite 레포지토리 | 6.1 |
| 6.3 | scripts/migrate_to_db.py | JSON → DB 마이그레이션 | 6.2 |

**결과물**:
- SQLite 데이터베이스 구축
- JSON과 DB 병행 사용 가능

### Wave 7: MCP 도구 (4시간)

| Task | 파일 | 내용 | 의존성 |
|------|------|------|--------|
| 7.1 | mcp/server.py | MCP 서버 | Wave 4 |
| 7.2 | mcp/tools/pdufa_probability.py | 확률 계산 도구 | 7.1 |
| 7.3 | mcp/tools/pdufa_events.py | 이벤트 조회 도구 | 7.1 |
| 7.4 | mcp/tools/price_analysis.py | 주가 분석 도구 | 7.1, Wave 5 |

**결과물**:
- Claude Desktop에서 사용 가능한 MCP 도구
- 실시간 PDUFA 확률 계산

---

## 4. 파일 구조 (최종)

```
ticker-genius/
├── src/tickergenius/
│   ├── __init__.py
│   ├── __version__.py
│   │
│   ├── core/                    # 핵심 인프라
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── cache.py
│   │   └── http.py
│   │
│   ├── schemas/                 # 데이터 스키마 (통합됨)
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── enums.py            # SearchStatus, SourceTier 포함
│   │   ├── pdufa_event.py      # 신규 - 메인 스키마
│   │   ├── price_models.py     # 신규 - 주가 스키마
│   │   ├── clinical.py
│   │   ├── manufacturing.py
│   │   └── _deprecated/
│   │       └── pipeline.py     # DEPRECATED
│   │
│   ├── collection/             # 데이터 수집 (정리됨)
│   │   ├── __init__.py
│   │   ├── models.py           # 필수 enum만
│   │   ├── collector.py
│   │   ├── manifest.py
│   │   ├── api_clients.py
│   │   ├── web_search.py       # 통합됨
│   │   ├── search_chain.py     # 통합됨
│   │   ├── search_exceptions.py
│   │   ├── fallback_chain.py
│   │   ├── checkpoint.py
│   │   ├── batch_processor.py
│   │   ├── price_collector.py  # 신규
│   │   └── verification_runner.py
│   │
│   ├── analysis/               # 분석
│   │   ├── __init__.py
│   │   ├── runner.py           # 신규 - 분석 실행기
│   │   └── pdufa/
│   │       ├── __init__.py
│   │       ├── _analyzer.py
│   │       ├── _context.py     # from_pdufa_event() 추가
│   │       ├── _result.py
│   │       ├── _registry.py
│   │       └── _layers/        # 12개 레이어
│   │
│   ├── repositories/           # 데이터 접근
│   │   ├── __init__.py
│   │   ├── constants.py
│   │   └── sqlite_repo.py      # 신규 (선택적)
│   │
│   └── mcp/                    # MCP 도구 (신규)
│       ├── __init__.py
│       ├── server.py
│       └── tools/
│           ├── __init__.py
│           ├── pdufa_probability.py
│           ├── pdufa_events.py
│           └── price_analysis.py
│
├── scripts/                    # 스크립트 (정리됨, 12개)
│   ├── run_enrichment.py
│   ├── resume_enrichment.py
│   ├── migrate_to_v3.py
│   ├── calculate_days_to_pdufa.py
│   ├── collect_enrollment.py
│   ├── collect_study_names.py
│   ├── collect_nct_ids.py
│   ├── collect_nct_websearch.py
│   ├── compute_has_prior_crl.py
│   ├── auto_derive_fields.py
│   ├── update_enriched_data.py
│   ├── collect_prices.py       # 신규
│   ├── build_price_windows.py  # 신규
│   └── _archive/               # 아카이브됨 (45개)
│       ├── batch_nct/
│       ├── batch_fda/
│       ├── batch_moa/
│       ├── batch_other/
│       ├── one_time/
│       └── README.md
│
├── data/
│   ├── enriched/               # PDUFA 이벤트 (v3 스키마)
│   ├── enriched_backup_v2/     # v2 백업
│   ├── prices/                 # 주가 데이터 (신규)
│   └── database.sqlite         # SQLite DB (선택적)
│
├── tests/
│   ├── test_schemas.py
│   ├── test_collection.py
│   ├── test_analysis.py
│   └── test_mcp.py
│
└── docs/
    ├── M3_BLUEPRINT_v3.md
    ├── SCHEMA_REDESIGN.md
    ├── LEGACY_CLEANUP_PLAN.md
    ├── IMPLEMENTATION_ROADMAP.md  # 이 문서
    └── DATA_COLLECTION_DESIGN.md
```

---

## 5. 의존성 그래프

```
Wave 1 (레거시 정리)
    │
    ▼
Wave 2 (스키마 + 12개 신규 필드)
    │
    ├──────────────┬──────────────┐
    ▼              ▼              ▼
Wave 2.5       Wave 3          Wave 5
(수집기)       (마이그레이션)   (주가)
    │              │              │
    └──────┬───────┘              │
           ▼                      │
       Wave 4                     │
    (분석 + 알고리즘 수정)        │
           │                      │
           ├──────────────────────┘
           ▼
       Wave 6 (DB) ← 선택적
           │
           ▼
       Wave 7 (MCP)
```

---

## 6. 검증 명령

### Wave 1 완료 후

```bash
# 스크립트 개수 확인
ls scripts/*.py | wc -l  # 12개여야 함

# 아카이브 확인
ls scripts/_archive/ | wc -l  # 5개 폴더

# 임포트 테스트
python -c "from tickergenius.collection import Collector; print('OK')"
```

### Wave 2 완료 후

```bash
# 스키마 임포트
python -c "from tickergenius.schemas import PDUFAEvent, SearchStatus; print('OK')"
python -c "from tickergenius.schemas.price_models import PriceHistory; print('OK')"
```

### Wave 3 완료 후

```bash
# 마이그레이션 검증
python scripts/migrate_to_v3.py --dry-run
python scripts/migrate_to_v3.py

# 로드 테스트
python -c "
from tickergenius.schemas import PDUFAEvent
import glob
files = glob.glob('data/enriched/*.json')
for f in files[:5]:
    event = PDUFAEvent.load(f)
    print(f'{event.ticker}: {event.drug_name}')
"
```

### Wave 4 완료 후

```bash
# 분석 파이프라인 테스트
python -c "
from tickergenius.schemas import PDUFAEvent
from tickergenius.analysis.runner import AnalysisRunner

event = PDUFAEvent.load('data/enriched/ABBV_0f6cbdde2a91.json')
runner = AnalysisRunner()
result = runner.analyze(event)
print(f'P(CRL): {result.p_crl:.2%}')
print(f'P(Approval): {result.p_approval:.2%}')
"
```

### Wave 5 완료 후

```bash
# 주가 수집 테스트
python -c "
from tickergenius.collection.price_collector import PriceCollector
from datetime import date, timedelta

collector = PriceCollector()
history = collector.fetch_history('ABBV', date.today() - timedelta(days=30), date.today())
print(f'수집된 가격: {len(history.prices)}개')
"
```

### Wave 7 완료 후

```bash
# MCP 서버 테스트
python -m tickergenius.mcp.server --test
```

---

## 7. 리스크 및 완화

| 리스크 | 영향 | 완화 방법 |
|--------|------|----------|
| 마이그레이션 데이터 손실 | 높음 | 백업 필수, 검증 단계 |
| 임포트 에러 | 중간 | 점진적 정리, 테스트 |
| 주가 API Rate Limit | 낮음 | 캐싱, 배치 처리 |
| MCP 호환성 | 낮음 | 독립 모듈로 구현 |

---

## 8. 관련 문서

- [SCHEMA_REDESIGN.md](./SCHEMA_REDESIGN.md) - 스키마 상세 설계
- [LEGACY_CLEANUP_PLAN.md](./LEGACY_CLEANUP_PLAN.md) - 레거시 정리 계획
- [M3_BLUEPRINT_v3.md](./M3_BLUEPRINT_v3.md) - 전체 아키텍처
- [DATA_COLLECTION_DESIGN.md](./DATA_COLLECTION_DESIGN.md) - 수집 파이프라인

---

## 9. 실행 준비 상태

| 항목 | 상태 | 참조 |
|------|------|------|
| 설계 문서 | ✅ 완료 | M3_BLUEPRINT_v3.md |
| 스키마 정의 (37개 기존) | ✅ 완료 | SCHEMA_REDESIGN.md Section 1-8 |
| **스키마 확장 (12개 신규)** | ✅ 완료 | SCHEMA_REDESIGN.md Section 9 |
| **알고리즘 수정 계획** | ✅ 완료 | SCHEMA_REDESIGN.md Section 9.9 |
| 마이그레이션 로직 | ✅ 완료 | SCHEMA_REDESIGN.md Section 9.6 |
| 레거시 정리 계획 | ✅ 완료 | LEGACY_CLEANUP_PLAN.md |
| 주가 스키마 | ✅ 완료 | SCHEMA_REDESIGN.md Section 7 |
| DB 스키마 | ✅ 완료 | SCHEMA_REDESIGN.md Section 8 |
| 구현 | ⏳ 대기 | - |

### 신규 필드 요약 (4명 페르소나 검토 완료)

| 수집 전략 | 필드 | 소스 |
|----------|------|------|
| 사전 수집 | is_single_arm, trial_region | NCT API |
| 사전 수집 | is_biosimilar | 웹서치 → Purple Book |
| 사전 수집 | is_first_in_class | FDA 보고서 |
| 사전 수집 | crl_reason_type | CRL 발표문 웹서치 |
| 캐시 (30일) | warning_letter_date, fda_483_* | FDA DB |
| 캐시 (30일) | cdmo_name | SEC 10-K |
| 분석시 검색 | pai_passed, pai_date | 웹서치 |
| 분석시 검색 | clinical_hold_history | 웹서치 |

**다음 단계**: Wave 1 실행 (레거시 정리)
