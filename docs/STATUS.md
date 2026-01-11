# Ticker-Genius 프로젝트 현황

**최종 업데이트**: 2026-01-11
**현재 마일스톤**: M3 진행 중

---

## 마일스톤 현황

| 마일스톤 | 설명 | 상태 | Git 태그 | 검증일 |
|----------|------|------|----------|--------|
| M1 | Pydantic 스키마 | ✅ 완료 | - | 2026-01-08 |
| M2 | Core 인프라 | ✅ 완료 | - | 2026-01-08 |
| M3 | PDUFA 분석 모듈 | ✅ 90% 완료 | - | 2026-01-11 |
| M4 | MCP 서버 + 도구 | ⏳ 대기 | - | - |
| M5 | ML 모듈 | ⏳ 대기 | - | - |
| MT | 트레이딩 (Phase 9+) | ⏳ 대기 | - | - |

---

## M3: PDUFA 분석 모듈 ✅

### 완료 항목

```
✅ 데이터 수집 (523건)
✅ NCT ID 수집 (97.1%)
✅ FDA Designations 수집
✅ AdCom 정보 수집
✅ PAI/Warning Letter 수집
✅ 스키마 통합 (AnalysisContext.from_enriched)
✅ EventLoader 구현
✅ 백테스트 검증 (92.5% 정확도)
✅ 레거시 코드 정리
```

### 파일 구조

```
src/tickergenius/analysis/pdufa/
├── __init__.py
├── probability.py      # 승인 확률 계산 ✅
├── analyzer.py         # PDUFAAnalyzer ✅
├── _context.py         # AnalysisContext ✅
├── event_loader.py     # EventLoader ✅
├── _layers/            # 확률 계산 레이어 ✅
└── _constants.py       # 상수 ✅
```

### 백테스트 결과

| 방법 | 정확도 | CRL Recall |
|------|--------|------------|
| Simple Rule | 96.0% | 52% |
| PDUFAAnalyzer | 92.5% | 33% |

### 핵심 예측 인자

| 필드 | Approved | CRL | Gap |
|------|----------|-----|-----|
| endpoint_met | 99% | 70% | +29% |
| pai_passed | 100% | 74% | +26% |
| prior_crl | 35% | 56% | -21% |

---

## 데이터셋 현황

- **총 이벤트**: 523건
- **결과 분포**: approved 477, crl 27, pending 17, withdrawn 2
- **핵심 필드 완성률**: 97-100%
- **Ground Truth 보유**: ✅

---

## 활성 Collection 모듈 (16개)

```
src/tickergenius/collection/
├── web_search.py           # 웹 검색
├── designation_collector.py # FDA designation
├── nct_enricher.py         # ClinicalTrials.gov
├── search_chain.py         # 검색 체인
├── search_utils.py         # 검색 유틸
├── checkpoint.py           # 체크포인트
├── collector.py            # 기본 수집기
├── api_clients.py          # API 클라이언트
└── ... (총 16개)
```

---

## 다음 작업

### M3 남은 작업 (선택)
- CRL 탐지율 개선 (현재 33% → 목표 50%+)
- 역상관 필드 가중치 조정

### M4: MCP 서버
- MCP 프로토콜 구현
- 도구 정의

---

**Note**: M3 핵심 기능 완료. 데이터셋 프로덕션 준비 완료.
