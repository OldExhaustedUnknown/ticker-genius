# 데이터셋 갭 분석 보고서

**작성일**: 2026-01-10
**분석 대상**: 523건 PDUFA 이벤트 데이터

---

## 1. 크리티컬 갭 (즉시 해결 필요)

### 1.1 enrollment (0%)
- **현황**: 523건 모두 None
- **영향**: 통계적 power 평가 불가, 소규모 시험 리스크 미반영
- **해결**: ClinicalTrials.gov API로 NCT ID 기반 수집
- **예상 커버리지**: 90%+ (NCT 보유 513건)

### 1.2 p_value_numeric (11%)
- **현황**: 58건만 수치, 나머지 텍스트 또는 None
- **영향**: 통계적 유의성 정량 비교 불가
- **해결**: 텍스트 파싱 ("p<0.001" → 0.001)
- **예상 커버리지**: 60%+ (파싱 가능한 케이스)

### 1.3 phase3_study_names (0%)
- **현황**: 523건 모두 empty list
- **영향**: 임상 시험 식별 불가
- **해결**: NCT ID → trial title 매핑
- **예상 커버리지**: 90%+

---

## 2. 스키마 불일치

### 2.1 Pipeline 스키마 vs 실제 데이터

| Pipeline 스키마 | 데이터 필드 | 상태 |
|----------------|------------|------|
| company_name | - | ❌ 없음 |
| drug_classification | - | ❌ 없음 |
| days_to_pdufa | - | ❌ 없음 (계산 가능) |
| pdufa_history | - | ❌ 없음 |
| crl_history | prior_crl_reason | ⚠️ 부분 |
| pai_status (enum) | pai_passed (bool) | ⚠️ 타입 다름 |
| manufacturing_site | - | ❌ 없음 |
| approval_probability | - | ❌ 없음 (M3 구현 후) |
| market_cap | - | ❌ 없음 |
| current_price | - | ❌ 없음 |

### 2.2 ClinicalTrial 스키마 vs 실제 데이터

| ClinicalTrial 스키마 | 데이터 필드 | 상태 |
|---------------------|------------|------|
| nct_id | nct_ids[0] | ⚠️ 배열 vs 단일 |
| title | phase3_study_names | ❌ 비어있음 |
| status | - | ❌ 없음 |
| enrollment | enrollment | ❌ 모두 None |
| sponsor | - | ❌ 없음 |
| endpoints | - | ❌ 없음 |

---

## 3. 중복 필드 분석

### 3.1 FDA Designations (이중화)
```
개별 필드:
- btd: StatusField
- priority_review: StatusField
- fast_track: StatusField
- orphan_drug: StatusField
- accelerated_approval: StatusField

통합 필드:
- fda_designations: dict (btd, ft, pr, od, aa)

권장: 통합 필드만 사용, 개별 필드 deprecated
```

### 3.2 AdCom 정보 (이중화)
```
개별 필드:
- adcom_held: StatusField
- adcom_date: NoneType (대부분 None)
- adcom_vote_favorable: NoneType (10% 채워짐)
- adcom_recommendation: NoneType (모두 None)

통합 필드:
- adcom_info: dict (scheduled, held, outcome, vote)

권장: adcom_info만 사용, 개별 필드 deprecated
```

---

## 4. 데이터 타입 이슈

### 4.1 텍스트 vs 숫자
```python
# 현재 (텍스트)
effect_size.value = "31% vs 8% improvement"
p_value.value = "p<0.001"

# 권장 (숫자 분리)
effect_size_text = "31% vs 8% improvement"
effect_size_numeric = 0.31
p_value_text = "p<0.001"
p_value_numeric = 0.001
```

### 4.2 StatusField 일관성
```python
# 불일치 예시
has_prior_crl: dict (StatusField 구조)
result: str (단순 값)
mechanism_of_action: str (단순 값)

# 권장: 확정 데이터는 단순 값, 불확실 데이터는 StatusField
```

---

## 5. 개선 우선순위

### Wave 1 (확률 계산 필수)
1. [ ] enrollment 수집 (NCT API)
2. [ ] p_value 숫자 파싱
3. [ ] days_to_pdufa 필드 추가 (런타임 계산)

### Wave 2 (스키마 정규화)
4. [ ] 중복 필드 정리 (fda_designations, adcom_info로 통합)
5. [ ] phase3_study_names 수집
6. [ ] company_name 추가

### Wave 3 (확장)
7. [ ] manufacturing_site 수집
8. [ ] sponsor_track_record 수집
9. [ ] competitor_landscape 추가

---

## 6. 스키마 개선 제안

### 6.1 EnrichedPDUFAEvent (새 스키마)
```python
class EnrichedPDUFAEvent(BaseSchema):
    """현재 데이터 구조에 맞춘 스키마."""

    # 기본 식별자
    event_id: str
    ticker: str
    drug_name: str
    pdufa_date: date

    # 결과
    result: Literal["approved", "crl", "pending", "withdrawn"]

    # FDA 지정 (통합)
    fda_designations: FDADesignations

    # 임상 데이터
    phase: str
    nct_ids: list[str]
    primary_endpoint_met: bool

    # AdCom (통합)
    adcom_info: AdComInfo

    # 제조
    pai_passed: bool
    warning_letter: bool
    safety_signal: bool

    # CRL 이력
    has_prior_crl: bool
    prior_crl_reason: Optional[str]

    # 메타데이터
    therapeutic_area: str
    mechanism_of_action: str
    collected_at: datetime
    enriched_at: datetime
```

### 6.2 변환 함수
```python
def to_pipeline(event: EnrichedPDUFAEvent) -> Pipeline:
    """데이터 → 스키마 변환."""
    return Pipeline(
        ticker=event.ticker,
        drug_name=event.drug_name,
        pdufa_date=StatusField.found(event.pdufa_date),
        days_to_pdufa=compute_days_to_pdufa(event.pdufa_date),
        has_prior_crl=event.has_prior_crl,
        # ...
    )
```

---

## 7. 다음 단계

1. **즉시**: enrollment 수집 스크립트 작성
2. **단기**: 중복 필드 정리, 스키마 정규화
3. **중기**: Pipeline 스키마와 데이터 동기화
4. **장기**: 실시간 갱신 파이프라인 구축

---

**결론**: 핵심 확률 계산 필드는 96%+ 완성.
enrollment, p_value_numeric 수집과 스키마 정규화가 다음 우선순위.
