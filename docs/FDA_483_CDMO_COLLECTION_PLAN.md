# FDA 483 + CDMO 수집 계획

## 현재 상태
- fda_483_date: 24.1% found (126/523)
- 나머지 75.9% (397건)는 not_searched

## Task 1: FDA 483 웹서치 추가 수집

### 전략
1. **대상**: fda_483_date가 not_searched인 397건
2. **검색 쿼리**:
   - `"{company}" FDA 483 inspection`
   - `"{company}" form 483 observations`
   - `site:redica.com "{company}"`
3. **Rate Limit**: 2초/검색 (보수적)

### 예상 결과
- 대형 제약사: 이미 처리됨 (16개)
- 중소형 바이오텍: FDA 483 수신 확률 낮음
- 예상 추가 발견: 10-20건 (대부분 confirmed_none 처리)

### 실행 방법
```bash
python scripts/collect_fda_483.py --search --limit 50  # 테스트
python scripts/collect_fda_483.py --search             # 전체
```

---

## Task 2: CDMO 기반 매핑

### 배경
많은 바이오텍은 자체 제조시설 없이 CDMO(Contract Development Manufacturing Organization) 사용
→ CDMO의 FDA 이슈가 해당 약물에 영향

### 주요 CDMO 목록
| CDMO | 주요 고객 | 최근 이슈 |
|------|---------|----------|
| Catalent | 다수 소형 바이오텍 | Bloomington 483 (2023) |
| Lonza | Moderna, 기타 | Portsmouth 483 (2023) |
| Samsung Biologics | 다수 대형사 | Clean record |
| Thermo Fisher | Greenville 483 (2023) |
| WuXi Biologics | 다수 | China-based |
| Boehringer Ingelheim | 위탁생산 | Clean |

### 매핑 전략
1. **SEC 10-K에서 CDMO 관계 추출**
   - "manufacturing agreement", "contract manufacturing"
   - "Catalent", "Lonza" 등 CDMO 이름 검색

2. **Drug-CDMO 매핑 테이블 구축**
   ```
   drug_name -> cdmo_name -> cdmo_issues[]
   ```

3. **CDMO 이슈를 이벤트에 전파**
   - CDMO에 Warning Letter/483 있으면 해당 약물 이벤트에 반영

### 구현 파일
```
scripts/
├── collect_cdmo_mapping.py    # CDMO 관계 수집
├── cdmo_issue_propagation.py  # 이슈 전파
```

### 예상 영향
- 소형 바이오텍 이벤트 중 CDMO 사용하는 경우
- Catalent 고객: ~50-100건 예상
- 영향도: fda_483_date 커버리지 30-40%까지 향상 가능

---

## 실행 순서

### Phase 1: FDA 483 웹서치 (1시간)
```bash
# 백그라운드 실행
python scripts/collect_fda_483.py --search
```

### Phase 2: CDMO 매핑 수집 (30분)
```bash
# CDMO 관계 수집
python scripts/collect_cdmo_mapping.py --fetch

# 이슈 전파
python scripts/collect_cdmo_mapping.py --propagate
```

### Phase 3: 검증 (10분)
```bash
# 최종 커버리지 확인
python scripts/collect_fda_483.py --status
```

---

## 예상 최종 결과
| 필드 | Before | After |
|------|--------|-------|
| fda_483_date | 24.1% | 35-40% found |
| | | 60-65% confirmed_none |
