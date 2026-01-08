# Phase 4: Migration Plan (이행 계획)

**작성일**: 2026-01-08
**작성자**: 5인 전문가 팀

---

## 4.1 마일스톤 개요

```
┌─────────────────────────────────────────────────────────────────┐
│                      MIGRATION ROADMAP                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  M1 ──────► M2 ──────► M3 ──────► M4 ──────► M5                │
│  (완료)     (현재)                                              │
│                                                                 │
│  M1: Pydantic 스키마        ✓ 완료                              │
│  M2: Core 인프라            ← 다음 단계                          │
│  M3: PDUFA 분석 모듈                                            │
│  M4: MCP 서버 + 도구                                            │
│  M5: ML 모듈 + 추가 도구                                         │
│                                                                 │
│  [별도] MT: 트레이딩 모듈 (Safety 검증 후)                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4.2 M2: Core 인프라

### 4.2.1 태스크 목록

| ID | 태스크 | 소스 | 분류 | 의존성 |
|----|--------|------|------|--------|
| M2-01 | `__version__.py` 생성 | 신규 | NEW | - |
| M2-02 | `core/config.py` 구현 | D:\Stock\core\config.py | GREEN | M2-01 |
| M2-03 | `core/cache.py` 구현 | D:\Stock\core\disk_cache.py | YELLOW | M2-02 |
| M2-04 | `core/http.py` 구현 | 신규 | NEW | M2-02 |
| M2-05 | `core/logging.py` 구현 | 신규 (Phase 3 설계) | NEW | M2-02 |
| M2-06 | pyproject.toml 동적 버전 설정 | 신규 | NEW | M2-01 |
| M2-07 | 단위 테스트 작성 | 신규 | NEW | M2-02~05 |

### 4.2.2 M2-02: config.py 포팅 명세

**원본**: `D:\Stock\core\config.py`
**분류**: GREEN (수정 최소화)

```python
# 포팅 시 유지할 패턴
class Config:
    """
    우선순위: 환경변수 > .env 파일 > 기본값
    """
    # API 키 로딩 로직 유지
    # TRADING_MODE 환경변수 추가 (Phase 3 Safety 설계)
```

**변경 사항**:
- Pydantic v2 `BaseSettings` 마이그레이션
- `TRADING_MODE` 환경변수 추가
- 민감 정보 마스킹 로깅 추가

### 4.2.3 M2-03: cache.py 포팅 명세

**원본**: `D:\Stock\core\disk_cache.py`
**분류**: YELLOW (인터페이스 정리)

```python
# 유지할 기능
- 디스크 캐시 저장/로드
- TTL 기반 만료
- 티커별 디렉토리 구조

# 제거할 기능
- 미사용 메서드들 (정리 필요)

# 추가할 기능
- async 지원 (선택적)
- 캐시 통계 메서드
```

### 4.2.4 검증 체크포인트

```
□ __version__.py 존재 및 pyproject.toml 연동 확인
□ Config 클래스에서 API 키 로딩 테스트
□ 캐시 저장/로드 라운드트립 테스트
□ 로깅이 파일에 JSON 형식으로 기록됨 확인
□ 테스트 커버리지 80% 이상
```

---

## 4.3 M3: PDUFA 분석 모듈

### 4.3.1 태스크 목록

| ID | 태스크 | 소스 | 분류 | 의존성 |
|----|--------|------|------|--------|
| M3-01 | `analysis/pdufa/enums.py` | D:\Stock\modules\pdufa\enums.py | GREEN | M2 |
| M3-02 | `analysis/pdufa/probability.py` | D:\Stock\modules\pdufa\probability.py | GREEN | M3-01 |
| M3-03 | `analysis/pdufa/analyzer.py` | D:\Stock\modules\pdufa_analyzer.py | YELLOW | M3-01,02 |
| M3-04 | `data/repository.py` | 신규 | NEW | M2 |
| M3-05 | `data/sec.py` | D:\Stock\modules\sec_api.py | YELLOW | M2 |
| M3-06 | 단위/통합 테스트 | 신규 | NEW | M3-01~05 |

### 4.3.2 M3-01: enums.py 포팅 명세

**원본**: `D:\Stock\modules\pdufa\enums.py` (11KB)
**분류**: GREEN (그대로 포팅)

```python
# 포팅 대상 Enum
- CatalystType
- ApprovalStatus
- DrugType
- TherapeuticArea
- ReviewType
- AdvisoryCommitteeResult
# ... 기타 Enum들

# 변경 없이 그대로 복사
```

### 4.3.3 M3-02: probability.py 포팅 명세

**원본**: `D:\Stock\modules\pdufa\probability.py` (5KB)
**분류**: GREEN

```python
# 유지할 함수
- calculate_base_probability()
- apply_modifiers()
- get_historical_rate()

# 검증 필요
- 확률 계산 로직 정확성 (기존 테스트 결과와 비교)
```

### 4.3.4 M3-03: analyzer.py 포팅 명세

**원본**: `D:\Stock\modules\pdufa_analyzer.py`
**분류**: YELLOW (스키마 통합 필요)

```python
# 변경 사항
- 기존 dict 반환 → Pydantic 스키마 반환
- M1 schemas 활용 (Pipeline, PDUFAEvent 등)
- StatusField 3-state 적용

# 인터페이스
class PDUFAAnalyzer:
    def analyze(self, ticker: str) -> Pipeline:
        """단일 티커 분석"""
        pass

    def analyze_batch(self, tickers: list[str]) -> list[Pipeline]:
        """배치 분석"""
        pass
```

### 4.3.5 검증 체크포인트

```
□ Enum 정의가 레거시와 동일한지 확인
□ 확률 계산 결과가 레거시와 ±0.01 이내 일치
□ analyzer가 Pydantic 스키마 반환 확인
□ SEC 데이터 조회 동작 확인
□ 기존 245개 티커 JSON과 호환성 확인
```

---

## 4.4 M4: MCP 서버 + 도구

> **도구 전체 로드맵**: [Phase 5: 도구 로드맵](./PHASE5_TOOL_ROADMAP.md) 참조
>
> Phase 5에서 레거시 55개 도구를 25개로 통폐합한 상세 계획을 확인하세요.

### 4.4.1 태스크 목록

| ID | 태스크 | 소스 | 분류 | 의존성 |
|----|--------|------|------|--------|
| M4-01 | `mcp/server.py` 기본 구조 | 신규 (FastMCP) | NEW | M3 |
| M4-02 | `mcp/tools/_registry.py` | Phase 5 ToolSpec 표준 | NEW | M4-01 |
| M4-03 | Tier 1 READ 도구 구현 | Phase 5 정의 | YELLOW | M4-01,02 |
| M4-04 | Tier 2 ANALYSIS 도구 구현 | Phase 5 정의 | YELLOW | M4-03 |
| M4-05 | 레거시 호환 래퍼 작성 | Phase 5 매핑 테이블 | NEW | M4-03,04 |
| M4-06 | Claude Desktop 연동 테스트 | - | TEST | M4-01~05 |

### 4.4.2 M4-01: server.py 구조

```python
# src/tickergenius/mcp/server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ticker-genius")

# 도구 자동 로딩
from .tools import fda, market

# 서버 실행
if __name__ == "__main__":
    mcp.run()
```

### 4.4.3 M4-03: fda.py 도구

```python
# src/tickergenius/mcp/tools/fda.py
from mcp.server.fastmcp import FastMCP
from tickergenius.analysis.pdufa import PDUFAAnalyzer
from tickergenius.mcp.tools._registry import register_tool, ToolSpec

@register_tool(ToolSpec(
    name="analyze_pdufa",
    description="PDUFA 날짜 기반 FDA 승인 확률 분석",
    version="1.0.0",
    category="fda",
    input_schema={"ticker": "str", "include_history": "bool"},
    output_schema={"probability": "float", "factors": "list"},
    doc_path="docs/tools/analyze_pdufa.md"
))
def analyze_pdufa(ticker: str, include_history: bool = True) -> dict:
    analyzer = PDUFAAnalyzer()
    result = analyzer.analyze(ticker)
    return result.model_dump()
```

### 4.4.4 검증 체크포인트

```
□ FastMCP 서버 정상 시작
□ Claude Desktop claude_desktop_config.json 연동
□ analyze_pdufa 도구 호출 성공
□ get_market_data 도구 호출 성공
□ 도구 명세서 docs/tools/ 에 생성됨
□ 도구 레지스트리에 등록됨 확인
```

---

## 4.5 M5: ML 모듈 + 추가 도구

### 4.5.1 태스크 목록

| ID | 태스크 | 소스 | 분류 | 의존성 |
|----|--------|------|------|--------|
| M5-01 | `ml/features.py` | D:\Stock\modules\ml\feature_store.py | GREEN | M4 |
| M5-02 | `ml/bayesian.py` | D:\Stock\modules\ml\bayesian.py | GREEN | M5-01 |
| M5-03 | `ml/trainer.py` | D:\Stock\modules\ml\xgboost_trainer.py | YELLOW | M5-01,02 |
| M5-04 | `mcp/tools/backtest.py` | D:\Stock\server.py 일부 | YELLOW | M5-01~03 |
| M5-05 | `mcp/tools/meme.py` | D:\Stock\modules\meme_analyzer.py | YELLOW | M4 |

### 4.5.2 M5-02: bayesian.py 포팅 명세

**원본**: `D:\Stock\modules\ml\bayesian.py`
**분류**: GREEN

```python
# 유지할 핵심 로직
class BayesianUpdater:
    def update_probability(
        self,
        prior: float,
        evidence: Evidence,
        likelihood_matrix: dict
    ) -> float:
        """TF 59-60차 구현 베이지안 업데이트"""
        pass

# scipy 의존성: optional (없으면 순수 Python 구현)
```

### 4.5.3 검증 체크포인트

```
□ BayesianUpdater 결과가 레거시와 일치
□ FeatureStore 저장/로드 정상
□ backtest 도구 동작 확인
□ meme 분석 도구 동작 확인
```

---

## 4.6 MT: 트레이딩 모듈 (별도)

> ⚠️ **주의**: 트레이딩 모듈은 Safety Layer 검증 완료 후 진행

### 4.6.1 선행 조건

```
□ Paper Trading 환경 구축 완료
□ Kill Switch 단위 테스트 통과
□ Dry-run 모드 검증 완료
□ 일일 손실 한도 로직 검증
□ 포지션 한도 로직 검증
□ 사용자 명시적 승인 ("트레이딩 모듈 구현해")
```

### 4.6.2 태스크 목록 (승인 후)

| ID | 태스크 | 소스 | 분류 | 의존성 |
|----|--------|------|------|--------|
| MT-01 | `trading/_safety.py` | 신규 (Phase 3 설계) | NEW | M4 |
| MT-02 | `trading/paper.py` | 신규 | NEW | MT-01 |
| MT-03 | `trading/risk.py` | D:\Stock\trading\risk.py | YELLOW | MT-01 |
| MT-04 | `trading/alpaca/client.py` | D:\Stock\trading\alpaca.py | RED | MT-01~03 |
| MT-05 | Paper Trading 통합 테스트 | - | TEST | MT-01~04 |
| MT-06 | Dry-run 모드 검증 | - | TEST | MT-01~04 |

---

## 4.7 의존성 그래프

```
                    ┌─────────┐
                    │   M1    │ ✓ 완료
                    │ Schemas │
                    └────┬────┘
                         │
                    ┌────▼────┐
                    │   M2    │ ← 다음
                    │  Core   │
                    └────┬────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
         ┌────▼────┐┌────▼────┐     │
         │   M3    ││  data/  │     │
         │  PDUFA  ││ repos   │     │
         └────┬────┘└────┬────┘     │
              │          │          │
              └────┬─────┘          │
                   │                │
              ┌────▼────┐           │
              │   M4    │           │
              │   MCP   │           │
              └────┬────┘           │
                   │                │
         ┌─────────┼─────────┐      │
         │         │         │      │
    ┌────▼────┐┌───▼───┐┌────▼────┐ │
    │   M5    ││backtest││  meme  │ │
    │   ML    ││ tool   ││  tool  │ │
    └─────────┘└────────┘└────────┘ │
                                    │
              ┌─────────────────────┘
              │ (별도 승인 필요)
         ┌────▼────┐
         │   MT    │
         │Trading  │
         └─────────┘
```

---

## 4.8 롤백 계획

### 각 마일스톤별 롤백 전략

| 마일스톤 | 롤백 트리거 | 롤백 방법 |
|----------|-------------|-----------|
| M2 | Config/Cache 로딩 실패 | git revert, 레거시 유지 |
| M3 | 확률 계산 오차 > 5% | M3 브랜치 폐기, M2 유지 |
| M4 | MCP 서버 불안정 | M4 브랜치 폐기, CLI 모드 전환 |
| M5 | ML 결과 불일치 | M5 비활성화, M4까지만 운영 |
| MT | Safety 취약점 발견 | 즉시 중단, Paper 전용 |

### 롤백 명령어

```bash
# 특정 마일스톤 롤백
git revert --no-commit <M3-commit>..<HEAD>
git commit -m "Rollback to M2"

# 브랜치 전략
git checkout -b m3-attempt-2  # 재시도
git checkout main             # 안정 버전으로 복귀
```

---

## 4.9 리스크 매트릭스

| 리스크 | 영향 | 확률 | 대응 |
|--------|------|------|------|
| 스키마 호환성 깨짐 | HIGH | LOW | M1 테스트 강화, 마이그레이션 스크립트 |
| FastMCP 버그 | MED | MED | FastAPI 백업 플랜 준비 |
| 레거시 로직 오류 발견 | MED | MED | 단계별 검증, 비교 테스트 |
| 트레이딩 Safety 취약점 | CRITICAL | LOW | 별도 감사, 단계적 활성화 |
| 문서-코드 불일치 | LOW | MED | CI/CD 자동 검증 |

---

## 4.10 Definition of Done (DoD) 체크리스트

> **POSTMORTEM_001 교훈**: 문서에 "완료"라고 적기 전에 반드시 아래 체크리스트를 통과해야 함

### 4.10.1 M1 Definition of Done ✅

```
[x] 파일 존재 확인
    - schemas/__init__.py
    - schemas/base.py (StatusField 3-state)
    - schemas/enums.py (16개 Enum)
    - schemas/pipeline.py (Pipeline, PDUFAEvent)
    - schemas/clinical.py (ClinicalTrial)
    - schemas/manufacturing.py (PAITracking)
[x] Import 테스트: python -c "from tickergenius.schemas import Pipeline"
[x] StatusField 3-state 동작 확인
[x] Pipeline 생성 테스트
[x] Git 커밋 완료
[x] STATUS.md 업데이트
```

### 4.10.2 M2 Definition of Done ✅

```
[x] 파일 존재 확인
    - __version__.py (v4.0.0)
    - core/__init__.py
    - core/config.py
    - core/cache.py
    - core/http.py
    - core/data_provider.py
[x] Import 테스트: python -c "from tickergenius.core import Config"
[x] Config 환경변수 로딩 테스트
[x] Cache 저장/로드 라운드트립
[x] DataProvider 연동 테스트
[x] M1+M2 통합 Import 테스트
[x] Git 커밋 완료
[x] STATUS.md 업데이트
```

### 4.10.3 M3 Definition of Done (예정)

```
□ 파일 존재 확인
    - analysis/pdufa/__init__.py
    - analysis/pdufa/probability.py
    - analysis/pdufa/analyzer.py
    - analysis/pdufa/factors.py
    - analysis/pdufa/crl.py
□ Import 테스트: python -c "from tickergenius.analysis.pdufa import PDUFAAnalyzer"
□ calculate_pdufa_probability 동작 확인
□ Pipeline 스키마 연동 확인
□ 레거시 확률과 ±0.05 일치 검증
□ Git 커밋 + 태그 (M3-complete)
□ STATUS.md 업데이트
```

### 4.10.4 M4 Definition of Done (예정)

```
□ 파일 존재 확인
    - mcp/server.py
    - mcp/tools/__init__.py
    - mcp/tools/fda.py
    - mcp/tools/market.py
□ FastMCP 서버 시작 테스트
□ Claude Desktop 연동 테스트
□ analyze_pdufa 도구 호출 성공
□ 도구 명세서 생성 확인
□ Git 커밋 + 태그 (M4-complete)
□ STATUS.md 업데이트
```

### 4.10.5 M5 Definition of Done (예정)

```
□ 파일 존재 확인
    - ml/features.py
    - ml/bayesian.py
    - ml/trainer.py
□ BayesianUpdater 결과 검증
□ 레거시 ML 결과와 비교
□ Git 커밋 + 태그 (M5-complete)
□ STATUS.md 업데이트
```

### 4.10.6 MT Definition of Done (별도 승인 필요)

```
□ Safety Layer 선행 조건 충족 (4.6.1 참조)
□ Paper Trading 환경 구축
□ Kill Switch 테스트 통과
□ Dry-run 모드 검증
□ 사용자 명시적 승인
□ Git 커밋 + 태그 (MT-complete)
□ STATUS.md 업데이트
```

---

## 4.11 다음 액션

### 현재 상태 (2026-01-08)

```
✅ M1: Pydantic 스키마 - 완료
✅ M2: Core 인프라 - 완료
⏳ M3: PDUFA 분석 모듈 - 대기
```

### 사용자 확인 필요 사항

```
□ M3 구현 시작 승인
□ 트레이딩 모듈 구현 여부 (별도 결정)
□ CI/CD 파이프라인 설정 (GitHub Actions)
```

---

## 4.12 문서 상태

| 문서 | 상태 | 비고 |
|------|------|------|
| PHASE1_ANALYSIS.md | current | 포렌식 분석 완료 |
| PHASE2_ISSUE_PORTING.md | current | Issue Register 완료 |
| PHASE3_ARCHITECTURE.md | current | 아키텍처 설계 완료 |
| PHASE4_MIGRATION_PLAN.md | current | 이 문서 |

---

**설계 단계 완료. 사용자의 "코드 만들어" 승인 대기 중.**
