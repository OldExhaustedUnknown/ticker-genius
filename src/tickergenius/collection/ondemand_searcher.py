"""
On-Demand Searcher - 분석 시 실시간 검색
========================================
Wave 2.5: pai_passed, pai_date, clinical_hold_history 필드 수집

분석 시점에 실시간 웹서치로 수집:
- PAI (Pre-Approval Inspection) 통과 여부
- Clinical Hold 이력
"""

from __future__ import annotations

import re
import logging
from datetime import date, datetime
from typing import Optional

from tickergenius.schemas.base import StatusField

logger = logging.getLogger(__name__)


class OnDemandSearcher:
    """분석 시 실시간 검색기."""

    def __init__(self, web_search_client=None):
        """
        Args:
            web_search_client: WebSearchClient 인스턴스 (없으면 생성)
        """
        self._web_search = web_search_client

    async def _get_web_search(self):
        """WebSearchClient 지연 로딩."""
        if self._web_search is None:
            try:
                from tickergenius.collection.web_search import WebSearchClient
                self._web_search = WebSearchClient()
            except ImportError:
                logger.warning("WebSearchClient not available")
                return None
        return self._web_search

    async def search_pai_status(
        self,
        drug_name: str,
        company_name: str,
    ) -> dict:
        """
        PAI 상태 검색.

        Returns:
            {
                "pai_passed": StatusField[bool],
                "pai_date": StatusField[date],
            }
        """
        web_search = await self._get_web_search()
        if not web_search:
            return {
                "pai_passed": StatusField.not_found(["websearch_unavailable"]),
                "pai_date": StatusField.not_found(["websearch_unavailable"]),
            }

        try:
            # PAI 관련 검색
            query = f'"{drug_name}" "{company_name}" FDA PAI inspection passed'
            results = await web_search.search(query, max_results=10)

            if not results:
                return {
                    "pai_passed": StatusField.not_found(["websearch"]),
                    "pai_date": StatusField.not_found(["websearch"]),
                }

            # 결과 분석
            pai_passed = None
            pai_date = None
            evidence = []

            for result in results:
                text = (result.get("title", "") + " " + result.get("snippet", "")).lower()

                # PAI 통과 패턴
                if any(phrase in text for phrase in [
                    "pai passed", "inspection passed", "pai completed",
                    "pre-approval inspection completed", "satisfactory pai",
                    "pai successful", "passed pre-approval"
                ]):
                    pai_passed = True
                    evidence.append(result.get("title", "")[:100])

                    # 날짜 추출 시도
                    date_match = re.search(
                        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})|(\w+ \d{1,2},? \d{4})',
                        text
                    )
                    if date_match and pai_date is None:
                        try:
                            date_str = date_match.group()
                            # 간단한 파싱 시도
                            pai_date = self._parse_date(date_str)
                        except Exception:
                            pass

                # PAI 실패 패턴
                elif any(phrase in text for phrase in [
                    "pai failed", "inspection failed", "form 483",
                    "warning letter", "pai issues", "inspection issues"
                ]):
                    if pai_passed is None:  # 먼저 찾은 passed가 우선
                        pai_passed = False
                        evidence.append(f"[FAILED] {result.get('title', '')[:100]}")

            # 결과 구성
            if pai_passed is not None:
                pai_passed_field = StatusField.found(
                    value=pai_passed,
                    source="websearch_pai",
                    confidence=0.75,
                    tier=3,
                    evidence=evidence[:3],
                )
            else:
                pai_passed_field = StatusField.not_found(["websearch"])

            if pai_date is not None:
                pai_date_field = StatusField.found(
                    value=pai_date,
                    source="websearch_pai",
                    confidence=0.7,
                    tier=3,
                )
            else:
                pai_date_field = StatusField.not_found(["websearch"])

            return {
                "pai_passed": pai_passed_field,
                "pai_date": pai_date_field,
            }

        except Exception as e:
            logger.error(f"PAI search error: {e}")
            return {
                "pai_passed": StatusField.not_found(["websearch"]),
                "pai_date": StatusField.not_found(["websearch"]),
                "error": str(e),
            }

    async def search_clinical_hold(
        self,
        drug_name: str,
        company_name: str,
    ) -> StatusField[bool]:
        """
        Clinical Hold 이력 검색.

        Returns:
            StatusField[bool]: clinical_hold_history
        """
        web_search = await self._get_web_search()
        if not web_search:
            return StatusField.not_found(["websearch_unavailable"])

        try:
            query = f'"{drug_name}" "{company_name}" FDA clinical hold'
            results = await web_search.search(query, max_results=10)

            if not results:
                # 검색 결과 없음 = Clinical Hold 없음 (확인됨)
                return StatusField.confirmed_none("websearch_clinical_hold")

            # 결과 분석
            evidence = []
            has_hold = False

            for result in results:
                text = (result.get("title", "") + " " + result.get("snippet", "")).lower()

                # Clinical Hold 패턴
                if any(phrase in text for phrase in [
                    "clinical hold", "fda hold", "placed on hold",
                    "partial clinical hold", "full clinical hold",
                    "study halted", "trial halted", "trial suspended"
                ]):
                    has_hold = True
                    evidence.append(result.get("title", "")[:100])

            if has_hold:
                return StatusField.found(
                    value=True,
                    source="websearch_clinical_hold",
                    confidence=0.75,
                    tier=3,
                    evidence=evidence[:3],
                )
            else:
                # 검색했지만 hold 관련 내용 없음
                return StatusField.found(
                    value=False,
                    source="websearch_clinical_hold",
                    confidence=0.7,
                    tier=3,
                )

        except Exception as e:
            logger.error(f"Clinical hold search error: {e}")
            return StatusField.not_found(["websearch"])

    def _parse_date(self, date_str: str) -> Optional[date]:
        """간단한 날짜 파싱."""
        import re
        from datetime import datetime

        # MM/DD/YYYY or MM-DD-YYYY
        match = re.match(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', date_str)
        if match:
            m, d, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if y < 100:
                y += 2000
            try:
                return date(y, m, d)
            except ValueError:
                pass

        # Month DD, YYYY
        months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12,
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
            'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        match = re.match(r'(\w+)\s+(\d{1,2}),?\s+(\d{4})', date_str, re.IGNORECASE)
        if match:
            month_name = match.group(1).lower()
            if month_name in months:
                try:
                    return date(int(match.group(3)), months[month_name], int(match.group(2)))
                except ValueError:
                    pass

        return None

    async def search_all(
        self,
        drug_name: str,
        company_name: str,
    ) -> dict:
        """
        모든 on-demand 필드 검색.

        Returns:
            {
                "pai_passed": StatusField[bool],
                "pai_date": StatusField[date],
                "clinical_hold_history": StatusField[bool],
            }
        """
        # 병렬 검색
        import asyncio

        pai_task = self.search_pai_status(drug_name, company_name)
        hold_task = self.search_clinical_hold(drug_name, company_name)

        pai_result, hold_result = await asyncio.gather(pai_task, hold_task)

        return {
            **pai_result,
            "clinical_hold_history": hold_result,
        }


async def search_ondemand_fields(
    drug_name: str,
    company_name: str,
) -> dict:
    """편의 함수: 분석 시 실시간 검색."""
    searcher = OnDemandSearcher()
    return await searcher.search_all(drug_name, company_name)


__all__ = ["OnDemandSearcher", "search_ondemand_fields"]
