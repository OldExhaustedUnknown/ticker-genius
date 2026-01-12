# PDUFA Event Schema v2

**작성일**: 2026-01-12
**상태**: 확정

---

## 1. 개요

### 변경 사유
- `is_resubmission`, `has_prior_crl` 필드 신뢰성 문제 발견
- `prior_crl_reason` 필드명 오류 (실제로는 현재 CRL 사유)
- 타임라인 컨텍스트 없이 파생된 값들

### 핵심 원칙
1. **검증된 데이터만 분석에 사용**
2. **미검증 데이터는 명시적으로 표시**
3. **기존 데이터 구조 유지하면서 점진적 개선**

---

## 2. 파일 구조

```
data/enriched/{event_id}.json
```

파일 구조 변경 없음. 필드 의미와 상태 관리 방식 변경.

---

## 3. 필드 정의

### 3.1 식별 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `event_id` | string | 이벤트 고유 ID |
| `ticker` | string | 종목 코드 |
| `drug_name` | string | 약물명 |
| `indication` | string | 적응증 |

### 3.2 시점 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `pdufa_date` | StatusField | PDUFA 날짜 (최종/현재) |
| `submission_date` | StatusField | 제출일 (NEW, 선택) |
| `pdufa_history` | list | PDUFA 변경 이력 (선택) |

**PDUFA 날짜 변경 가능성**:
- FDA가 추가 정보 요청 시 3개월 연장 가능 (CRL 없이)
- 같은 제출에 대해 PDUFA가 여러 번 변경될 수 있음
- 현재 구조에서는 **최종 PDUFA만 기록**

```json
// 선택적 PDUFA 이력 (추후 확장)
"pdufa_history": [
  {"date": "2024-06-01", "type": "original"},
  {"date": "2024-09-01", "type": "extended", "reason": "RTF response"}
]
```

### 3.3 제출 유형

```json
"submission_type": {
  "value": "original | resubmission | supplement | null",
  "search_status": "FOUND | NOT_SEARCHED | NOT_VERIFIED",
  "source": "string",
  "evidence": []
}
```

| value | 설명 |
|-------|------|
| `original` | 첫 제출 |
| `resubmission` | CRL 후 재제출 |
| `supplement` | sNDA/sBLA |
| `null` | 미확인 |

### 3.4 과거 히스토리

```json
"prior_history": {
  "has_prior_crl": "bool | null",
  "prior_crl_date": "date | null",
  "prior_crl_reason": "string | null",
  "search_status": "FOUND | NOT_SEARCHED | NOT_VERIFIED",
  "source": "string"
}
```

**중요**: 이 PDUFA 날짜 **이전**의 CRL 여부

### 3.5 결과

| 필드 | 타입 | 설명 |
|------|------|------|
| `result` | enum | approved / crl / pending / withdrawn |

### 3.6 CRL 상세 (result=crl인 경우)

```json
"crl_details": {
  "reason": "string",
  "category": "safety | efficacy | cmc | other",
  "search_status": "FOUND | NOT_SEARCHED"
}
```

**주의**: 기존 `prior_crl_reason`은 실제로 **현재** CRL 사유임

---

## 4. search_status 정의

| 값 | 의미 | 분석 사용 |
|----|------|----------|
| `FOUND` | 검색 완료, 값 확인됨 | ✅ 사용 |
| `CONFIRMED_NONE` | 검색 완료, 없음 확인 | ✅ 사용 (false로) |
| `NOT_SEARCHED` | 미검색 | ❌ 스킵 |
| `NOT_VERIFIED` | 값 있으나 미검증 | ❌ 스킵 |
| `NOT_FOUND` | 검색했으나 판단 불가 | ❌ 스킵 |

---

## 5. DEPRECATED 필드

다음 필드는 하위 호환을 위해 유지하나 분석에서 사용하지 않음:

| 필드 | 대체 필드 | 사유 |
|------|----------|------|
| `is_resubmission` | `submission_type` | 미검증, 신뢰 불가 |
| `has_prior_crl` | `prior_history.has_prior_crl` | 미검증, 신뢰 불가 |
| `prior_crl_reason` | `crl_details.reason` | 필드명 오류 |

---

## 6. 분석 시 필드 사용 규칙

### 사용 가능 (신뢰)
- `primary_endpoint_met` - ✅
- `pai_passed` - ✅
- `designations` (BTD, Priority 등) - ✅
- `crl_details.reason` (result=crl만) - ✅

### 사용 불가 (미검증)
- `is_resubmission` - ❌
- `has_prior_crl` - ❌
- `prior_history.*` (search_status != FOUND) - ❌

### 코드 구현

```python
def should_use_field(field_data: dict) -> bool:
    """필드를 분석에 사용해도 되는지 판단"""
    if not isinstance(field_data, dict):
        return False

    status = field_data.get('search_status',
             field_data.get('status', 'NOT_VERIFIED'))

    return status in ['FOUND', 'CONFIRMED_NONE', 'found']
```

---

## 7. 마이그레이션

### 기존 데이터 처리

```python
# is_resubmission: NOT_VERIFIED로 표시
old_resub = data.get('is_resubmission')
data['submission_type'] = {
    'value': 'resubmission' if old_resub in [1, True] else 'original',
    'search_status': 'NOT_VERIFIED',
    'source': 'legacy_v12',
    'note': 'Migrated from is_resubmission, requires verification'
}

# prior_crl_reason → crl_details (result=crl만)
if data.get('result') == 'crl':
    reason = data.get('prior_crl_reason', {})
    data['crl_details'] = {
        'reason': reason.get('value') if isinstance(reason, dict) else reason,
        'category': None,  # 수동 분류 필요
        'search_status': 'FOUND' if reason else 'NOT_SEARCHED'
    }
```

---

## 8. 예시

### 첫 제출 → 승인

```json
{
  "event_id": "ABBV_abc123",
  "drug_name": "Rinvoq",
  "pdufa_date": {"value": "2019-08-16", "search_status": "FOUND"},
  "result": "approved",

  "submission_type": {
    "value": "original",
    "search_status": "FOUND",
    "source": "fda_database"
  },

  "prior_history": {
    "has_prior_crl": false,
    "search_status": "CONFIRMED_NONE"
  }
}
```

### 재제출 → 승인

```json
{
  "event_id": "XYZ_def456",
  "drug_name": "DrugX",
  "pdufa_date": {"value": "2024-03-01", "search_status": "FOUND"},
  "result": "approved",

  "submission_type": {
    "value": "resubmission",
    "search_status": "FOUND",
    "source": "websearch",
    "evidence": ["Company announced resubmission after 2023 CRL"]
  },

  "prior_history": {
    "has_prior_crl": true,
    "prior_crl_date": "2023-06-15",
    "prior_crl_reason": "CMC deficiencies",
    "search_status": "FOUND"
  }
}
```

### 현재 CRL

```json
{
  "event_id": "GILD_ghi789",
  "drug_name": "Filgotinib",
  "pdufa_date": {"value": "2020-08-01", "search_status": "FOUND"},
  "result": "crl",

  "submission_type": {
    "value": "original",
    "search_status": "FOUND"
  },

  "prior_history": {
    "has_prior_crl": false,
    "search_status": "CONFIRMED_NONE"
  },

  "crl_details": {
    "reason": "Testicular toxicity concerns",
    "category": "safety",
    "search_status": "FOUND"
  }
}
```

---

**문서 끝**
