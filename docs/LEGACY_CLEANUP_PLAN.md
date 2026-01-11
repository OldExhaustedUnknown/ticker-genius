# 레거시/스파게티 정리 계획

**작성일**: 2026-01-10
**목표**: 코드베이스 정리 및 아키텍처 단순화
**원칙**: "레거시, 스파게티는 용납할 수 없어"

---

## 1. 현재 상태 요약

### 1.1 Scripts (66개)

| 카테고리 | 개수 | 처리 방침 |
|----------|------|----------|
| 일회성 배치 스크립트 | 45 | **아카이브** |
| 유틸리티/재사용 가능 | 12 | **유지/리팩토링** |
| 마이그레이션 스크립트 | 5 | **실행 후 아카이브** |
| 테스트/검증 스크립트 | 4 | **유지** |

### 1.2 Collection 모듈 (30개 파일)

| 상태 | 개수 | 처리 방침 |
|------|------|----------|
| 미사용/중복 | 12 | **삭제** |
| 리팩토링 필요 | 8 | **통합** |
| 유지 | 10 | **유지** |

### 1.3 Schema 파일 (6개)

| 파일 | 상태 | 처리 방침 |
|------|------|----------|
| pipeline.py | 중복 | **DEPRECATED 표시** |
| event_models.py | 중복 | **삭제** |
| models.py | 부분 사용 | **SearchStatus만 추출** |
| pdufa_event.py | 신규 | **메인 스키마** |
| price_models.py | 신규 | **주가 스키마** |

---

## 2. 스크립트 정리 계획

### 2.1 아카이브 대상 (45개)

```
scripts/_archive/  (새 폴더)
├── batch_nct/      # NCT 배치 스크립트들
│   ├── apply_nct_batch.py
│   ├── apply_nct_batch2.py
│   ├── apply_nct_batch3.py
│   ├── apply_nct_batch4.py
│   ├── apply_nct_batch5.py
│   ├── apply_nct_batch6.py
│   ├── apply_nct_batch7.py
│   ├── apply_nct_batch8.py
│   └── apply_nct_final.py
│
├── batch_fda/      # FDA 지정 배치 스크립트들
│   ├── apply_fda_designations.py
│   ├── apply_fda_batch5.py ~ apply_fda_batch18.py (14개)
│   └── verify_fda_designations.py
│
├── batch_moa/      # MoA 배치 스크립트들
│   └── apply_moa_batch1.py ~ apply_moa_batch10.py (10개)
│
├── batch_other/    # 기타 배치 스크립트들
│   ├── apply_therapeutic_area.py
│   ├── apply_adcom_batch1.py
│   ├── apply_crl_reasons.py
│   ├── apply_remaining_crl.py
│   └── apply_pvalue_websearch.py
│
├── one_time/       # 일회성 수정 스크립트들
│   ├── derive_phase_from_result.py
│   ├── derive_prior_crl.py
│   ├── set_pai_defaults.py
│   ├── fix_safety_fields.py
│   ├── fix_remaining_nct.py
│   ├── parse_pvalue.py
│   ├── add_company_names.py
│   ├── clean_duplicate_fields.py
│   ├── reset_inferred_fields.py
│   └── set_regulatory_defaults.py
│
└── README.md       # 아카이브 설명
```

### 2.2 유지/리팩토링 대상 (12개)

```
scripts/  (정리 후)
├── run_enrichment.py          # 메인 보강 스크립트 → 유지
├── resume_enrichment.py       # 재개 스크립트 → 유지
├── migrate_to_enriched.py     # 마이그레이션 → 실행 후 아카이브
├── migrate_to_v3.py           # 신규 마이그레이션 → 실행 후 아카이브
├── calculate_days_to_pdufa.py # 유틸리티 → 유지
├── collect_enrollment.py      # 데이터 수집 → 유지
├── collect_study_names.py     # 데이터 수집 → 유지
├── collect_nct_ids.py         # 데이터 수집 → 유지
├── collect_nct_websearch.py   # 데이터 수집 → 유지
├── compute_has_prior_crl.py   # 유틸리티 → 유지
├── auto_derive_fields.py      # 유틸리티 → 유지
└── update_enriched_data.py    # 유틸리티 → 유지
```

### 2.3 아카이브 README.md 내용

```markdown
# Scripts Archive

이 폴더는 데이터 수집/마이그레이션 과정에서 사용된 일회성 스크립트들의 아카이브입니다.

## 사용하지 마세요

이 스크립트들은:
- 이미 실행 완료됨
- 데이터가 이미 반영됨
- 다시 실행하면 문제 발생 가능

## 카테고리 설명

- `batch_nct/`: NCT ID 수집 배치 스크립트 (9개)
- `batch_fda/`: FDA 지정 수집 배치 스크립트 (15개)
- `batch_moa/`: Mechanism of Action 수집 배치 스크립트 (10개)
- `batch_other/`: 기타 배치 스크립트 (5개)
- `one_time/`: 일회성 수정 스크립트 (10개)

## 참조용으로만 보관

로직 참조가 필요할 때만 확인하세요.

**아카이브 날짜**: 2026-01-10
```

---

## 3. Collection 모듈 정리 계획

### 3.1 삭제 대상 (12개)

```python
# 미사용 또는 중복된 파일들

# collection/
│
├── data_enricher.py      # 미사용 - 기능이 scripts/로 이동됨
├── event_extractor.py    # 미사용 - 직접 JSON 파싱 사용
├── event_store.py        # 미사용 - 직접 파일 접근 사용
├── event_models.py       # 중복 - pdufa_event.py로 대체
├── migration.py          # 완료됨 - 아카이브
├── predictor.py          # 미완성 - 삭제 (analysis 모듈에서 구현)
├── feature_calculator.py # 미완성 - 삭제 (analysis 모듈에서 구현)
│
├── ddg_searcher.py       # v1 - v2로 대체됨
├── ddg_searcher_v2.py    # web_search.py로 통합
│
└── enrichment/           # 전체 폴더
    ├── models.py         # 중복 - pdufa_event.py로 대체
    ├── drug_profiler.py  # 미사용
    ├── clinical_searcher.py # search_chain.py로 통합
    ├── orchestrator.py   # 미사용
    └── ddg_orchestrator.py # 미사용
```

### 3.2 유지 대상 (통합 후 10개)

```python
# collection/ (정리 후)
│
├── __init__.py           # 공개 API
├── models.py             # SearchStatus, SourceTier (필수 enum만)
├── collector.py          # 메인 수집기
├── manifest.py           # 매니페스트 관리
├── api_clients.py        # API 클라이언트들
├── web_search.py         # 웹 검색 통합
├── search_chain.py       # 검색 체인 오케스트레이터
├── search_exceptions.py  # 검색 예외
├── fallback_chain.py     # 폴백 체인
├── checkpoint.py         # 체크포인트 관리
├── batch_processor.py    # 배치 처리
└── verification_runner.py # 검증 실행기
```

### 3.3 통합 계획

```
[Before]                          [After]
─────────────────────────────────────────────────────
ddg_searcher.py          ──┐
ddg_searcher_v2.py       ──┼──→  web_search.py
enrichment/ddg_*.py      ──┘

search_utils.py          ──┐
clinical_data_enricher.py──┼──→  search_chain.py
enrichment/clinical_*.py ──┘
enrichment/orchestrator.py──┘

models.py                ──┐
event_models.py          ──┼──→  schemas/pdufa_event.py
enrichment/models.py     ──┘
```

---

## 4. Schema 정리 계획

### 4.1 현재 상태

```
schemas/
├── base.py          # 유지 - 기본 타입들
├── enums.py         # 유지 - Enum 정의
├── pipeline.py      # DEPRECATED - 점진적 삭제
├── clinical.py      # 유지 - 임상 타입들
├── manufacturing.py # 유지 - 제조 타입들
└── __init__.py      # 업데이트 필요

collection/
├── models.py        # SearchStatus만 추출 → schemas/로 이동
└── event_models.py  # 삭제 → pdufa_event.py로 대체
```

### 4.2 목표 상태

```
schemas/
├── __init__.py       # 공개 API
├── base.py           # 기본 타입들 (유지)
├── enums.py          # Enum 정의 + SearchStatus, SourceTier 통합
├── pdufa_event.py    # 신규 - 메인 PDUFA 이벤트 스키마
├── price_models.py   # 신규 - 주가 관련 스키마
├── clinical.py       # 유지
├── manufacturing.py  # 유지
└── _deprecated/
    └── pipeline.py   # DEPRECATED 표시
```

### 4.3 SearchStatus/SourceTier 이동

```python
# schemas/enums.py에 추가

class SearchStatus(str, Enum):
    """검색 상태 - 5가지."""
    FOUND = "found"
    CONFIRMED_NONE = "confirmed_none"
    NOT_APPLICABLE = "not_applicable"
    NOT_FOUND = "not_found"
    NOT_SEARCHED = "not_searched"

    @property
    def needs_retry(self) -> bool:
        return self in (SearchStatus.NOT_FOUND, SearchStatus.NOT_SEARCHED)

    @property
    def is_complete(self) -> bool:
        return self in (
            SearchStatus.FOUND,
            SearchStatus.CONFIRMED_NONE,
            SearchStatus.NOT_APPLICABLE,
        )


class SourceTier(int, Enum):
    """소스 신뢰도."""
    TIER1 = 1  # FDA 공식 (99%)
    TIER2 = 2  # SEC EDGAR, ClinicalTrials.gov (90%)
    TIER3 = 3  # 뉴스, PR (75%)
    TIER4 = 4  # 추론 (50%)
```

---

## 5. 실행 계획

### Stage 1: 준비 (즉시)

```bash
# 1. 아카이브 폴더 생성
mkdir -p scripts/_archive/{batch_nct,batch_fda,batch_moa,batch_other,one_time}

# 2. 백업 생성
cp -r scripts scripts_backup_$(date +%Y%m%d)
cp -r src/tickergenius src_backup_$(date +%Y%m%d)
```

### Stage 2: 스크립트 아카이브 (1시간)

```bash
# 1. NCT 배치 스크립트 이동
mv scripts/apply_nct_batch*.py scripts/_archive/batch_nct/
mv scripts/apply_nct_final.py scripts/_archive/batch_nct/
mv scripts/apply_nct_wave1.py scripts/_archive/batch_nct/

# 2. FDA 배치 스크립트 이동
mv scripts/apply_fda_*.py scripts/_archive/batch_fda/
mv scripts/verify_fda_designations.py scripts/_archive/batch_fda/

# 3. MoA 배치 스크립트 이동
mv scripts/apply_moa_*.py scripts/_archive/batch_moa/

# 4. 기타 배치 스크립트 이동
mv scripts/apply_therapeutic_area.py scripts/_archive/batch_other/
mv scripts/apply_adcom_batch1.py scripts/_archive/batch_other/
mv scripts/apply_crl_reasons.py scripts/_archive/batch_other/
mv scripts/apply_remaining_crl.py scripts/_archive/batch_other/
mv scripts/apply_pvalue_websearch.py scripts/_archive/batch_other/

# 5. 일회성 스크립트 이동
mv scripts/derive_*.py scripts/_archive/one_time/
mv scripts/set_*.py scripts/_archive/one_time/
mv scripts/fix_*.py scripts/_archive/one_time/
mv scripts/parse_pvalue.py scripts/_archive/one_time/
mv scripts/add_company_names.py scripts/_archive/one_time/
mv scripts/clean_duplicate_fields.py scripts/_archive/one_time/
mv scripts/reset_inferred_fields.py scripts/_archive/one_time/
```

### Stage 3: Collection 모듈 정리 (2시간)

```bash
# 1. 미사용 파일 삭제
rm src/tickergenius/collection/data_enricher.py
rm src/tickergenius/collection/event_extractor.py
rm src/tickergenius/collection/event_store.py
rm src/tickergenius/collection/event_models.py
rm src/tickergenius/collection/migration.py
rm src/tickergenius/collection/predictor.py
rm src/tickergenius/collection/feature_calculator.py
rm src/tickergenius/collection/ddg_searcher.py

# 2. 중복 폴더 삭제
rm -rf src/tickergenius/collection/enrichment/

# 3. __init__.py 업데이트
# (공개 API만 노출)
```

### Stage 4: Schema 정리 (1시간)

```bash
# 1. 새 스키마 파일 생성
# src/tickergenius/schemas/pdufa_event.py
# src/tickergenius/schemas/price_models.py

# 2. enums.py 업데이트 (SearchStatus, SourceTier 추가)

# 3. pipeline.py에 DEPRECATED 주석 추가

# 4. __init__.py 업데이트
```

### Stage 5: 검증 (30분)

```bash
# 1. 임포트 테스트
python -c "from tickergenius.schemas import PDUFAEvent; print('OK')"
python -c "from tickergenius.collection import Collector; print('OK')"

# 2. 기존 테스트 실행
pytest tests/ -v

# 3. 타입 체크
mypy src/tickergenius --ignore-missing-imports
```

---

## 6. 검증 체크리스트

### 정리 전 확인

- [ ] 백업 완료
- [ ] git stash 또는 별도 브랜치

### 스크립트 정리 후

- [ ] scripts/ 폴더에 12개 파일만 존재
- [ ] scripts/_archive/ 폴더에 45개 파일 이동
- [ ] README.md 작성 완료

### Collection 정리 후

- [ ] collection/ 폴더에 12개 파일만 존재
- [ ] enrichment/ 폴더 삭제됨
- [ ] 미사용 파일 12개 삭제됨
- [ ] 임포트 에러 없음

### Schema 정리 후

- [ ] pdufa_event.py 생성됨
- [ ] price_models.py 생성됨
- [ ] SearchStatus, SourceTier가 enums.py로 이동됨
- [ ] pipeline.py에 DEPRECATED 표시됨

### 최종 검증

- [ ] 모든 테스트 통과
- [ ] 타입 체크 통과
- [ ] 마이그레이션 스크립트 작동 확인

---

## 7. 롤백 계획

문제 발생 시:

```bash
# 백업에서 복원
rm -rf scripts src/tickergenius
cp -r scripts_backup_* scripts
cp -r src_backup_* src/tickergenius
```

---

## 8. 관련 문서

- [SCHEMA_REDESIGN.md](./SCHEMA_REDESIGN.md) - 스키마 재설계
- [M3_BLUEPRINT_v3.md](./M3_BLUEPRINT_v3.md) - 전체 아키텍처
- [DATA_COLLECTION_DESIGN.md](./DATA_COLLECTION_DESIGN.md) - 수집 파이프라인
