"""
FDA Designation Collector
==========================
FDA Designation (BTD, Orphan, Priority Review, Fast Track, Accelerated Approval) 수집 모듈.

TDD 기반으로 개발됨.

사용법:
    from tickergenius.collection.designation_collector import collect_designations_for_event

    result = await collect_designations_for_event(event)

설계 원칙:
    1. False Negative 최소화 - 못 찾으면 NOT_FOUND (False 아님)
    2. 다중 쿼리 전략 - 약물당 여러 검색 시도
    3. 신뢰도 기반 - FDA 소스 > 뉴스 > 일반 웹
"""

import re
import json
import asyncio
import logging
import html as html_lib
from pathlib import Path
from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

DESIGNATION_TYPES = ["btd", "orphan", "priority", "fast_track", "accelerated"]

FIELD_NAMES = {
    "btd": "breakthrough_therapy",
    "orphan": "orphan_drug",
    "priority": "priority_review",
    "fast_track": "fast_track",
    "accelerated": "accelerated_approval",
}

# 검색 쿼리 템플릿
QUERY_TEMPLATES = {
    "btd": [
        '"{drug}" breakthrough therapy designation FDA',
        '"{drug}" BTD granted',
        '"{generic}" breakthrough therapy FDA',
        '{company} "{drug}" breakthrough therapy',
        'site:biospace.com OR site:fiercepharma.com "{drug}" breakthrough',
    ],
    "orphan": [
        '"{drug}" orphan drug designation FDA',
        '"{drug}" orphan designation granted',
        '"{generic}" orphan drug FDA',
        'site:accessdata.fda.gov "{drug}" orphan',
        '"{drug}" rare disease designation',
    ],
    "priority": [
        '"{drug}" priority review FDA',
        '"{drug}" priority review granted',
        '{company} "{drug}" priority review',
    ],
    "fast_track": [
        '"{drug}" fast track designation FDA',
        '"{drug}" fast track granted',
        '{company} "{drug}" fast track',
    ],
    "accelerated": [
        '"{drug}" accelerated approval FDA',
        '"{drug}" surrogate endpoint FDA approval',
        'site:fda.gov "{drug}" accelerated approval',
    ],
}

# 긍정적 패턴 (designation 있음)
POSITIVE_PATTERNS = {
    "btd": [
        r'(?:granted?|received?|awarded?|designated?).*breakthrough therapy',
        r'breakthrough therapy.*(?:designation|status)',
        r'fda.*(?:grants?|awards?).*(?:breakthrough|btd)',
        r'btd.*(?:granted|received|awarded|to)',
        r'(?:grants?|awards?).*btd.*(?:to|for)',
        r'breakthrough therapy designation.*(?:for|to)',
    ],
    "orphan": [
        r'orphan drug designation',
        r'orphan designation.*(?:granted|received)',
        r'(?:granted|received).*orphan',
        r'rare disease designation',
        r'orphan drug status',
    ],
    "priority": [
        r'priority review.*(?:granted|received|designated)',
        r'(?:granted|received).*priority review',
        r'fda.*priority review',
    ],
    "fast_track": [
        r'fast track.*(?:designation|status)',
        r'(?:granted|received).*fast track',
        r'fda.*fast track',
    ],
    "accelerated": [
        r'accelerated approval',
        r'surrogate endpoint.*approv',
    ],
}

# 부정적 패턴 (무시해야 할 것들)
NEGATIVE_PATTERNS = [
    r'seeking.*(?:breakthrough|orphan|fast track|priority)',
    r'may.*(?:receive|grant)',
    r'potential.*(?:breakthrough|orphan)',
    r'(?:denied|rejected|not granted)',
    r'plans? to (?:seek|apply)',
]


# =============================================================================
# Drug Name Variant Generator
# =============================================================================

def generate_drug_variants(drug_name: str, generic_name: str = "") -> list[str]:
    """
    약물명의 다양한 변형을 생성합니다.

    Args:
        drug_name: 브랜드명 (예: "KEYTRUDA (pembrolizumab)")
        generic_name: 성분명 (예: "pembrolizumab")

    Returns:
        변형 리스트 (예: ["KEYTRUDA", "pembrolizumab"])
    """
    variants = []

    if not drug_name and not generic_name:
        return variants

    # 1. Original drug name
    if drug_name:
        variants.append(drug_name.strip())

    # 2. Generic name
    if generic_name:
        variants.append(generic_name.strip())

    # 3. 괄호 안의 이름 추출: "AUVELITY (AXS-05)" -> "AXS-05"
    if drug_name:
        paren_match = re.search(r'\(([^)]+)\)', drug_name)
        if paren_match:
            inner = paren_match.group(1).strip()
            if inner and inner not in variants:
                variants.append(inner)

            # 괄호 앞 부분도 추출: "AUVELITY (AXS-05)" -> "AUVELITY"
            before_paren = drug_name.split('(')[0].strip()
            if before_paren and before_paren not in variants:
                variants.append(before_paren)

    # 4. 복합 약물명 처리: "KEYTRUDA + chemotherapy" -> "KEYTRUDA"
    if drug_name:
        # + 또는 & 로 분리
        if '+' in drug_name or '&' in drug_name:
            parts = re.split(r'[+&]', drug_name)
            first_part = parts[0].strip()
            if first_part and first_part not in variants:
                variants.append(first_part)

        # 첫 단어 추출 (공백으로 분리)
        words = drug_name.split()
        if words:
            first_word = words[0].strip()
            if first_word and first_word not in variants and len(first_word) > 2:
                variants.append(first_word)

    # 빈 문자열 제거
    variants = [v for v in variants if v]

    return variants


# =============================================================================
# Search Query Builder
# =============================================================================

def build_search_queries(
    drug_name: str,
    generic_name: str,
    company_name: str,
    designation_type: str
) -> list[str]:
    """
    검색 쿼리들을 생성합니다.

    Args:
        drug_name: 약물명
        generic_name: 성분명
        company_name: 회사명
        designation_type: "btd", "orphan", "priority", "fast_track", "accelerated"

    Returns:
        쿼리 리스트
    """
    templates = QUERY_TEMPLATES.get(designation_type, [])
    queries = []

    # 변형 생성
    drug_variants = generate_drug_variants(drug_name, generic_name)
    primary_drug = drug_variants[0] if drug_variants else drug_name
    primary_generic = generic_name or (drug_variants[1] if len(drug_variants) > 1 else "")

    for template in templates:
        query = template.format(
            drug=primary_drug,
            generic=primary_generic,
            company=company_name or ""
        )
        # 빈 따옴표 제거
        query = re.sub(r'\"\"', '', query)
        query = re.sub(r'\s+', ' ', query).strip()

        if query and query not in queries:
            queries.append(query)

    # 추가 변형 쿼리
    for variant in drug_variants[1:3]:  # 최대 2개 추가 변형
        extra_query = f'"{variant}" {designation_type.replace("_", " ")} FDA'
        if extra_query not in queries:
            queries.append(extra_query)

    return queries


# =============================================================================
# DuckDuckGo Search
# =============================================================================

def search_ddg(query: str, timeout: float = 30.0, max_results: int = 10) -> list[dict]:
    """
    웹 검색 (ddgs 라이브러리, yahoo 백엔드 사용).

    Args:
        query: 검색 쿼리
        timeout: 타임아웃 (초)
        max_results: 최대 결과 수

    Returns:
        [{"title": str, "url": str, "snippet": str}]
    """
    try:
        from ddgs import DDGS

        results = []
        with DDGS(verify=False) as ddgs:
            # yahoo 백엔드가 가장 빠르고 안정적
            search_results = list(ddgs.text(query, max_results=max_results, backend='yahoo'))
            for r in search_results:
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", r.get("link", "")),
                    "snippet": r.get("body", r.get("snippet", "")),
                })
        return results

    except ImportError:
        logger.warning("ddgs not installed, using manual fallback")
        return _search_ddg_fallback(query, timeout)
    except Exception as e:
        logger.warning(f"Web search failed for '{query}': {e}")
        return []


def _search_ddg_fallback(query: str, timeout: float = 30.0) -> list[dict]:
    """DuckDuckGo HTML 폴백 검색."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, verify=False) as client:
            resp = client.post(
                'https://html.duckduckgo.com/html/',
                data={'q': query, 'b': ''},
                headers=headers
            )

            if resp.status_code == 403:
                logger.warning("DuckDuckGo returned 403 Forbidden")
                return []

            text = resp.text
            results = []

            # Title과 URL 추출
            title_pattern = re.compile(
                r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>',
                re.IGNORECASE
            )

            # Snippet 추출
            snippet_pattern = re.compile(
                r'<a[^>]*class="result__snippet"[^>]*>([^<]+)',
                re.IGNORECASE
            )

            # 결과 블록 분리
            blocks = re.split(r'<div[^>]*class="[^"]*result[^"]*results_links[^"]*"[^>]*>', text)

            for block in blocks[1:20]:  # 최대 20개
                title_match = title_pattern.search(block)
                if not title_match:
                    continue

                url = title_match.group(1)
                title = html_lib.unescape(title_match.group(2).strip())

                snippet = ""
                snippet_match = snippet_pattern.search(block)
                if snippet_match:
                    snippet = html_lib.unescape(snippet_match.group(1).strip())

                results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet,
                })

            return results

    except Exception as e:
        logger.warning(f"DuckDuckGo fallback search failed for '{query}': {e}")
        return []


# =============================================================================
# Result Parser
# =============================================================================

def parse_designation_result(
    search_results: list[dict],
    drug_name: str,
    designation_type: str
) -> dict:
    """
    검색 결과에서 designation 여부를 파싱합니다.

    Args:
        search_results: 검색 결과 리스트
        drug_name: 약물명
        designation_type: designation 타입

    Returns:
        {"found": bool, "value": bool|None, "confidence": float, "evidence": list, "url": str}
    """
    positive_patterns = POSITIVE_PATTERNS.get(designation_type, [])
    drug_variants = generate_drug_variants(drug_name, "")

    best_match = None
    best_confidence = 0.0

    for result in search_results:
        title = result.get("title", "")
        snippet = result.get("snippet", "")
        url = result.get("url", "")
        combined_text = f"{title} {snippet}".lower()

        # 약물명 확인
        drug_found = any(
            variant.lower() in combined_text
            for variant in drug_variants
            if variant
        )

        if not drug_found:
            continue

        # 부정적 패턴 체크 (신청 중, 거부 등)
        is_negative = any(
            re.search(pattern, combined_text, re.IGNORECASE)
            for pattern in NEGATIVE_PATTERNS
        )

        if is_negative:
            continue

        # 긍정적 패턴 체크
        for pattern in positive_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                # 신뢰도 계산
                confidence = 0.75

                # FDA 소스면 높은 신뢰도
                if "fda.gov" in url.lower():
                    confidence = 0.95
                elif any(domain in url.lower() for domain in ["biospace.com", "fiercepharma.com"]):
                    confidence = 0.85

                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = {
                        "found": True,
                        "value": True,
                        "confidence": confidence,
                        "evidence": [title[:100]],
                        "url": url,
                        "pattern": pattern,
                    }

    if best_match:
        return best_match

    return {
        "found": False,
        "value": None,
        "confidence": 0.0,
        "evidence": [],
        "url": None,
    }


# =============================================================================
# Status Field Creation
# =============================================================================

def create_designation_status(
    value: Any,
    found: bool,
    source: str,
    confidence: float,
    evidence: list = None,
    confirmed_none: bool = False,
) -> dict:
    """
    StatusField 형식의 designation 상태를 생성합니다.

    Args:
        value: 값 (True/False/None)
        found: 찾았는지 여부
        source: 소스
        confidence: 신뢰도
        evidence: 증거 리스트
        confirmed_none: 확실히 없음 확인 여부

    Returns:
        StatusField dict
    """
    if confirmed_none:
        status = "confirmed_none"
    elif found:
        status = "found"
    else:
        status = "not_found"

    return {
        "value": value,
        "status": status,
        "source": source,
        "confidence": confidence,
        "tier": 1 if "fda" in source.lower() else (2 if found else 3),
        "evidence": evidence or [],
        "searched_sources": [source],
        "last_searched": datetime.now(tz=None).isoformat(),
    }


# =============================================================================
# Main Search Function
# =============================================================================

async def search_designation_websearch(
    drug_name: str,
    generic_name: str,
    company_name: str,
    designation_type: str,
    rate_limit: float = 1.5,
) -> dict:
    """
    웹서치로 designation을 검색합니다.

    Args:
        drug_name: 약물명
        generic_name: 성분명
        company_name: 회사명
        designation_type: "btd", "orphan", "priority", "fast_track", "accelerated"
        rate_limit: 쿼리 간 대기 시간 (초)

    Returns:
        {"found": bool, "value": bool|None, "confidence": float, ...}
    """
    queries = build_search_queries(drug_name, generic_name, company_name, designation_type)

    all_results = []
    best_result = {"found": False, "value": None, "confidence": 0.0, "evidence": []}

    for query in queries[:2]:  # 최대 2개 쿼리 (속도 최적화)
        try:
            # 동기 검색을 비동기로 실행
            results = await asyncio.to_thread(search_ddg, query)
            all_results.extend(results)

            # 파싱
            parsed = parse_designation_result(results, drug_name, designation_type)

            if parsed["found"] and parsed["confidence"] > best_result.get("confidence", 0):
                best_result = parsed
                # 찾으면 조기 종료
                if parsed["found"]:
                    break

            # Rate limit
            await asyncio.sleep(rate_limit)

        except asyncio.TimeoutError:
            logger.warning(f"Timeout searching {designation_type} for {drug_name}")
            continue
        except Exception as e:
            logger.warning(f"Error searching {designation_type} for {drug_name}: {e}")
            continue

    # 결과가 없으면 not_found
    if not best_result["found"]:
        best_result["status"] = "not_found"
        best_result["source"] = "websearch"
    else:
        best_result["status"] = "found"
        best_result["source"] = "websearch"

    return best_result


# =============================================================================
# Collect All Designations for Event
# =============================================================================

async def collect_designations_for_event(
    event: dict,
    rate_limit: float = 1.5,
) -> dict:
    """
    단일 이벤트에 대해 모든 designation을 수집합니다.

    Args:
        event: 이벤트 dict
        rate_limit: 쿼리 간 대기 시간

    Returns:
        {"breakthrough_therapy": {...}, "orphan_drug": {...}, ...}
    """
    drug_name = event.get("drug_name", "")
    generic_name = event.get("generic_name", {})
    if isinstance(generic_name, dict):
        generic_name = generic_name.get("value", "")
    company_name = event.get("company_name", "")

    results = {}

    for designation_type in DESIGNATION_TYPES:
        field_name = FIELD_NAMES[designation_type]

        try:
            search_result = await search_designation_websearch(
                drug_name=drug_name,
                generic_name=generic_name,
                company_name=company_name,
                designation_type=designation_type,
                rate_limit=rate_limit,
            )

            results[field_name] = create_designation_status(
                value=search_result.get("value"),
                found=search_result.get("found", False),
                source=search_result.get("source", "websearch"),
                confidence=search_result.get("confidence", 0.0),
                evidence=search_result.get("evidence", []),
            )

        except Exception as e:
            logger.error(f"Error collecting {designation_type} for {drug_name}: {e}")
            results[field_name] = create_designation_status(
                value=None,
                found=False,
                source="error",
                confidence=0.0,
                evidence=[str(e)],
            )

    return results


# =============================================================================
# Save Event Designations (Race Condition Safe)
# =============================================================================

def save_event_designations(file_path: str, designations: dict) -> None:
    """
    이벤트 파일에 designation 필드를 안전하게 저장합니다.
    기존 필드를 유지하면서 designation만 업데이트합니다.

    Args:
        file_path: 이벤트 JSON 파일 경로
        designations: designation dict
    """
    path = Path(file_path)

    # 기존 데이터 로드
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            event = json.load(f)
    else:
        event = {}

    # Designation 필드 업데이트
    for field_name, value in designations.items():
        event[field_name] = value

    # 메타데이터 업데이트
    event["enriched_at"] = datetime.now(tz=None).isoformat()

    # 저장
    with open(path, "w", encoding="utf-8") as f:
        json.dump(event, f, indent=2, ensure_ascii=False)


# =============================================================================
# Batch Collection
# =============================================================================

async def collect_all_events(
    events_dir: str = "data/enriched",
    checkpoint_file: str = "data/temp/designation_checkpoint.json",
    rate_limit: float = 1.5,
) -> dict:
    """
    모든 이벤트에 대해 designation을 수집합니다.

    Args:
        events_dir: 이벤트 파일 디렉토리
        checkpoint_file: 체크포인트 파일
        rate_limit: 쿼리 간 대기 시간

    Returns:
        {"total": int, "processed": int, "found": dict}
    """
    events_path = Path(events_dir)
    checkpoint_path = Path(checkpoint_file)

    # 체크포인트 로드
    processed_ids = set()
    if checkpoint_path.exists():
        with open(checkpoint_path, "r") as f:
            checkpoint = json.load(f)
            processed_ids = set(checkpoint.get("processed_ids", []))

    # 이벤트 파일 로드
    event_files = list(events_path.glob("*.json"))
    total = len(event_files)

    stats = {
        "total": total,
        "processed": 0,
        "found": {dtype: 0 for dtype in DESIGNATION_TYPES},
    }

    for i, event_file in enumerate(event_files):
        event_id = event_file.stem

        # 이미 처리된 경우 스킵
        if event_id in processed_ids:
            continue

        try:
            # 이벤트 로드
            with open(event_file, "r", encoding="utf-8") as f:
                event = json.load(f)

            # Designation 수집
            designations = await collect_designations_for_event(event, rate_limit)

            # 저장
            save_event_designations(str(event_file), designations)

            # 통계 업데이트
            stats["processed"] += 1
            for dtype in DESIGNATION_TYPES:
                field_name = FIELD_NAMES[dtype]
                if designations.get(field_name, {}).get("value") is True:
                    stats["found"][dtype] += 1

            # 체크포인트 저장
            processed_ids.add(event_id)
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            with open(checkpoint_path, "w") as f:
                json.dump({"processed_ids": list(processed_ids)}, f)

            # 진행 상황 출력
            if (i + 1) % 10 == 0:
                logger.info(f"Progress: {i + 1}/{total}")

        except Exception as e:
            logger.error(f"Error processing {event_id}: {e}")
            continue

    return stats
