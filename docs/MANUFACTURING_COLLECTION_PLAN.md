# Manufacturing Data Collection Plan (공장명 기반)

## 현재 상태
- warning_letter_date: 100% coverage (19.5% found, 80.5% confirmed_none)
- fda_483_date: 3.4% coverage

## 문제점
기존 검색은 회사명으로만 검색 → 공장별로 발급되는 Warning Letter/483 놓침

## 수집 전략

### Approach 1: FDA Warning Letters DB 직접 검색
```
소스: https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/warning-letters
방법: 연도별 Warning Letter 목록에서 제약사 추출
신뢰도: Tier 1 (95%)
```

### Approach 2: 공장명 + 지역 기반 검색
```
검색 패턴:
- "{company_name} {city} FDA warning letter"
- "{company_name} manufacturing facility FDA 483"
- "{drug_name} manufacturing site FDA inspection"

예시:
- "Pfizer McPherson Kansas FDA warning letter"
- "Genzyme Framingham FDA warning letter"
- "Hospira McPherson FDA 483"
```

### Approach 3: CDMO (Contract Manufacturing) 검색
```
많은 바이오텍이 자체 공장 없이 CDMO 사용
주요 CDMO Warning Letter 추적:
- Catalent (다수 바이오텍 위탁)
- Lonza
- Samsung Biologics
- WuXi Biologics
- Thermo Fisher
- Boehringer Ingelheim (위탁생산)

검색: "{drug_name} contract manufacturing FDA"
```

### Approach 4: FDA 483 전문 사이트
```
소스:
- redica.com (FDA 483 데이터베이스)
- pharmacompass.com (제조 이슈 추적)
- fdazilla.com (FDA 데이터 집계)

검색: site:redica.com "{company_name}" 483
```

### Approach 5: SEC 10-K 시설 정보 추출
```
10-K Item 2 "Properties"에 제조 시설 목록 공개
패턴: "manufacturing facility", "production site", "FDA-registered"
추출 후 각 시설별 Warning Letter 검색
```

## 구현 계획

### Phase 1: 시설 정보 수집 (Facility Discovery)
1. SEC 10-K에서 제조 시설 목록 추출
2. 기존 이벤트의 drug_name으로 제조사 역추적
3. CDMO 사용 여부 파악

### Phase 2: FDA 데이터 수집
1. FDA Warning Letters 페이지 크롤링 (2020-2025)
2. 회사명 매칭으로 이벤트와 연결
3. 시설별 Warning Letter 날짜 기록

### Phase 3: 483 데이터 보강
1. redica.com 검색 (rate limited)
2. pharmacompass 검색
3. 뉴스 검색으로 보완

## 예상 결과
- warning_letter_date: 19.5% → 25-30% found (시설 기반으로 추가 발견)
- fda_483_date: 3.4% → 15-20% found

## 구현 파일
```
scripts/
├── collect_facilities.py      # 시설 정보 수집
├── collect_fda_wl_direct.py   # FDA Warning Letters DB 직접
├── collect_fda_483.py         # FDA 483 수집
└── collect_cdmo_issues.py     # CDMO 이슈 추적
```

## Rate Limits
- FDA.gov: 10 req/sec
- redica.com: 1 req/5sec (보수적)
- websearch: 1 req/2sec
