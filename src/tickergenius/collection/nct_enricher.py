"""
NCT Enricher - ClinicalTrials.gov API 기반 임상 정보 수집
=======================================================
Wave 2.5: is_single_arm, trial_region 필드 수집

소스: ClinicalTrials.gov API v2
- is_single_arm: designInfo.interventionModel == "SINGLE_GROUP"
- trial_region: locations[].country 집계

Note: httpx가 403을 받는 문제로 requests 사용 (asyncio.to_thread로 async 지원)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import requests

from tickergenius.schemas.base import StatusField
from tickergenius.schemas.enums import TrialRegion

logger = logging.getLogger(__name__)

# ClinicalTrials.gov API v2
NCT_API_BASE = "https://clinicaltrials.gov/api/v2/studies"

# ClinicalTrials.gov requires browser-like User-Agent
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


class NCTEnricher:
    """ClinicalTrials.gov API를 통한 임상 정보 수집."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self._session: Optional[requests.Session] = None

    async def __aenter__(self):
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)
        return self

    async def __aexit__(self, *args):
        if self._session:
            self._session.close()

    def _ensure_session(self):
        """Session 초기화."""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(DEFAULT_HEADERS)

    def _get_study_sync(self, nct_id: str) -> dict:
        """동기 API 호출."""
        self._ensure_session()

        url = f"{NCT_API_BASE}/{nct_id}"
        params = {
            "fields": "protocolSection.designModule,protocolSection.contactsLocationsModule,protocolSection.statusModule",
            "format": "json",
        }

        response = self._session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    async def get_study_design(self, nct_id: str) -> dict:
        """
        NCT ID로 임상시험 디자인 정보 조회.

        Returns:
            {
                "is_single_arm": StatusField[bool],
                "trial_region": StatusField[str],
                "enrollment": int | None,
                "phase": str | None,
            }
        """
        if not nct_id or not nct_id.startswith("NCT"):
            return {
                "is_single_arm": StatusField.not_applicable("invalid_nct_id"),
                "trial_region": StatusField.not_applicable("invalid_nct_id"),
                "enrollment": None,
                "phase": None,
            }

        try:
            # Run sync request in thread pool
            data = await asyncio.to_thread(self._get_study_sync, nct_id)
            return self._parse_study_design(data, nct_id)

        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return {
                    "is_single_arm": StatusField.not_found(["clinicaltrials.gov"]),
                    "trial_region": StatusField.not_found(["clinicaltrials.gov"]),
                    "enrollment": None,
                    "phase": None,
                }
            logger.warning(f"NCT API error for {nct_id}: {e}")
            return {
                "is_single_arm": StatusField.not_found(["clinicaltrials.gov"]),
                "trial_region": StatusField.not_found(["clinicaltrials.gov"]),
                "enrollment": None,
                "phase": None,
                "error": str(e),
            }
        except Exception as e:
            logger.error(f"NCT API unexpected error for {nct_id}: {e}")
            return {
                "is_single_arm": StatusField.not_found(["clinicaltrials.gov"]),
                "trial_region": StatusField.not_found(["clinicaltrials.gov"]),
                "enrollment": None,
                "phase": None,
                "error": str(e),
            }

    def _parse_study_design(self, data: dict, nct_id: str) -> dict:
        """API 응답에서 디자인 정보 파싱."""
        result = {
            "is_single_arm": StatusField.not_found(["clinicaltrials.gov"]),
            "trial_region": StatusField.not_found(["clinicaltrials.gov"]),
            "enrollment": None,
            "phase": None,
        }

        protocol = data.get("protocolSection", {})

        # Design Module
        design_module = protocol.get("designModule", {})
        design_info = design_module.get("designInfo", {})

        # is_single_arm 판별
        intervention_model = design_info.get("interventionModel", "")
        allocation = design_info.get("allocation", "")

        is_single_arm = (
            intervention_model == "SINGLE_GROUP"
            or allocation == "NON_RANDOMIZED"
            or intervention_model == "SEQUENTIAL"  # Dose escalation
        )

        result["is_single_arm"] = StatusField.found(
            value=is_single_arm,
            source="clinicaltrials.gov",
            confidence=0.95,
            tier=2,
            evidence=[f"interventionModel={intervention_model}", f"allocation={allocation}"],
        )

        # Phase
        phases = design_module.get("phases", [])
        if phases:
            result["phase"] = phases[-1]  # 가장 높은 phase

        # Enrollment
        enrollment_info = design_module.get("enrollmentInfo", {})
        result["enrollment"] = enrollment_info.get("count")

        # Location/Region
        locations_module = protocol.get("contactsLocationsModule", {})
        locations = locations_module.get("locations", [])

        if locations:
            countries = set()
            for loc in locations:
                country = loc.get("country", "")
                if country:
                    countries.add(country.upper())

            region = self._classify_region(countries)
            result["trial_region"] = StatusField.found(
                value=region.value,
                source="clinicaltrials.gov",
                confidence=0.95,
                tier=2,
                evidence=[f"countries={list(countries)[:5]}..."],  # 처음 5개만
            )
        else:
            result["trial_region"] = StatusField.not_found(["clinicaltrials.gov"])

        return result

    def _classify_region(self, countries: set[str]) -> TrialRegion:
        """국가 목록에서 지역 분류."""
        us_names = {"UNITED STATES", "USA", "US", "UNITED STATES OF AMERICA"}
        china_names = {"CHINA", "PEOPLE'S REPUBLIC OF CHINA", "PRC"}

        has_us = bool(countries & us_names)
        has_china = bool(countries & china_names)
        other_countries = countries - us_names - china_names

        # 분류 로직
        if len(countries) == 1:
            if has_us:
                return TrialRegion.US_ONLY
            elif has_china:
                return TrialRegion.CHINA_ONLY
            else:
                return TrialRegion.EX_US

        if has_us and other_countries:
            return TrialRegion.GLOBAL

        if not has_us:
            return TrialRegion.EX_US

        return TrialRegion.GLOBAL

    async def enrich_event(self, nct_ids: list[str]) -> dict:
        """
        여러 NCT ID에서 정보 수집 후 병합.

        Primary NCT (첫 번째)의 디자인 정보 사용.
        """
        if not nct_ids:
            return {
                "is_single_arm": StatusField.not_applicable("no_nct_ids"),
                "trial_region": StatusField.not_applicable("no_nct_ids"),
            }

        # Primary NCT 조회
        primary_nct = nct_ids[0]
        result = await self.get_study_design(primary_nct)

        # 다른 NCT들에서 보완 (trial_region 등)
        if len(nct_ids) > 1:
            trial_region = result.get("trial_region")
            if trial_region and hasattr(trial_region, "status"):
                from tickergenius.schemas.enums import SearchStatus
                if trial_region.status == SearchStatus.NOT_FOUND:
                    for nct_id in nct_ids[1:]:
                        other = await self.get_study_design(nct_id)
                        other_region = other.get("trial_region")
                        if other_region and other_region.status == SearchStatus.FOUND:
                            result["trial_region"] = other_region
                            break

        return result


async def enrich_from_nct(nct_ids: list[str]) -> dict:
    """편의 함수: NCT ID 목록에서 정보 수집."""
    async with NCTEnricher() as enricher:
        return await enricher.enrich_event(nct_ids)


__all__ = ["NCTEnricher", "enrich_from_nct"]
