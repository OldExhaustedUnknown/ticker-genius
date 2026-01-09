"""
Official FDA Source Scrapers
=============================
FDA 공식 소스에서 데이터를 수집하는 스크래퍼.

레거시 데이터 대체를 위한 공식 검증 소스:
1. FDA CDER BTD Approvals List
2. FDA OOPD Orphan Drug Database
3. FDA Advisory Committee Calendar
"""

import logging
import re
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class BTDDesignation:
    """Breakthrough Therapy Designation 정보."""
    drug_name: str
    sponsor: str
    indication: str
    designation_date: Optional[str] = None
    approval_date: Optional[str] = None
    status: str = "designated"  # designated, approved, withdrawn


@dataclass
class OrphanDesignation:
    """Orphan Drug Designation 정보."""
    drug_name: str
    generic_name: Optional[str]
    sponsor: str
    designation: str
    designation_date: str
    orphan_designation_status: str
    fda_orphan_approval: Optional[str] = None


@dataclass
class AdComMeeting:
    """Advisory Committee Meeting 정보."""
    drug_name: Optional[str]
    sponsor: Optional[str]
    committee: str
    meeting_date: str
    meeting_type: str  # scheduled, held, cancelled
    outcome: Optional[str] = None  # positive, negative, split
    vote_for: Optional[int] = None
    vote_against: Optional[int] = None


class FDABTDListScraper:
    """
    FDA CDER Breakthrough Therapy Approvals List 스크래퍼.

    소스: https://www.fda.gov/drugs/nda-and-bla-approvals/breakthrough-therapy-approvals
    """

    URL = "https://www.fda.gov/drugs/nda-and-bla-approvals/breakthrough-therapy-approvals"

    def __init__(self):
        self.timeout = 30.0
        self._cache: Optional[list[BTDDesignation]] = None
        self._cache_time: Optional[datetime] = None

    def fetch_btd_list(self, force_refresh: bool = False) -> list[BTDDesignation]:
        """BTD 목록 가져오기."""
        # 캐시 사용 (1시간)
        if not force_refresh and self._cache and self._cache_time:
            age = (datetime.now() - self._cache_time).seconds
            if age < 3600:
                return self._cache

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(self.URL)
                response.raise_for_status()
                html = response.text

            # HTML 파싱 (간단한 테이블 추출)
            designations = self._parse_btd_html(html)
            self._cache = designations
            self._cache_time = datetime.now()
            logger.info(f"Fetched {len(designations)} BTD designations from FDA")
            return designations

        except Exception as e:
            logger.error(f"Failed to fetch BTD list: {e}")
            return self._cache or []

    def _parse_btd_html(self, html: str) -> list[BTDDesignation]:
        """HTML에서 BTD 목록 추출."""
        designations = []

        # 테이블 행 패턴 (간단한 정규식)
        # FDA 페이지 구조에 따라 조정 필요
        table_pattern = re.compile(
            r'<tr[^>]*>\s*<td[^>]*>([^<]+)</td>\s*<td[^>]*>([^<]+)</td>',
            re.IGNORECASE | re.DOTALL
        )

        matches = table_pattern.findall(html)
        for match in matches:
            drug_name = match[0].strip()
            indication = match[1].strip() if len(match) > 1 else ""

            if drug_name and not drug_name.startswith("<"):
                designations.append(BTDDesignation(
                    drug_name=drug_name,
                    sponsor="",  # FDA 페이지에서 추출 필요
                    indication=indication,
                    status="approved",
                ))

        return designations

    def is_btd_designated(self, drug_name: str) -> Optional[BTDDesignation]:
        """특정 약물이 BTD인지 확인."""
        designations = self.fetch_btd_list()
        drug_upper = drug_name.upper()

        for d in designations:
            if drug_upper in d.drug_name.upper():
                return d

        return None


class FDAOrphanDatabaseScraper:
    """
    FDA OOPD Orphan Drug Database 스크래퍼.

    소스: https://www.accessdata.fda.gov/scripts/opdlisting/oopd/
    """

    SEARCH_URL = "https://www.accessdata.fda.gov/scripts/opdlisting/oopd/listResult.cfm"

    def __init__(self):
        self.timeout = 30.0

    def search_orphan_designation(
        self,
        drug_name: Optional[str] = None,
        sponsor: Optional[str] = None,
    ) -> list[OrphanDesignation]:
        """Orphan Drug 지정 검색."""
        try:
            params = {}
            if drug_name:
                params["productname"] = drug_name
            if sponsor:
                params["sponsorname"] = sponsor

            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(self.SEARCH_URL, params=params)
                response.raise_for_status()
                html = response.text

            return self._parse_search_results(html)

        except Exception as e:
            logger.error(f"Orphan drug search failed: {e}")
            return []

    def _parse_search_results(self, html: str) -> list[OrphanDesignation]:
        """검색 결과 파싱."""
        designations = []

        # 결과 테이블에서 데이터 추출
        # FDA 페이지 구조에 따라 조정 필요
        row_pattern = re.compile(
            r'<tr[^>]*class="[^"]*data[^"]*"[^>]*>(.*?)</tr>',
            re.IGNORECASE | re.DOTALL
        )

        for row_match in row_pattern.finditer(html):
            row_html = row_match.group(1)
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.DOTALL)

            if len(cells) >= 4:
                designations.append(OrphanDesignation(
                    drug_name=self._clean_html(cells[0]),
                    generic_name=self._clean_html(cells[1]) if len(cells) > 1 else None,
                    sponsor=self._clean_html(cells[2]) if len(cells) > 2 else "",
                    designation=self._clean_html(cells[3]) if len(cells) > 3 else "",
                    designation_date="",
                    orphan_designation_status="designated",
                ))

        return designations

    def _clean_html(self, text: str) -> str:
        """HTML 태그 제거."""
        return re.sub(r'<[^>]+>', '', text).strip()

    def is_orphan_designated(self, drug_name: str) -> bool:
        """특정 약물이 Orphan Drug인지 확인."""
        results = self.search_orphan_designation(drug_name=drug_name)
        return len(results) > 0


class FDAAdvisoryCalendarScraper:
    """
    FDA Advisory Committee Calendar 스크래퍼.

    소스: https://www.fda.gov/advisory-committees/advisory-committee-calendar
    """

    CALENDAR_URL = "https://www.fda.gov/advisory-committees/advisory-committee-calendar"

    def __init__(self):
        self.timeout = 30.0
        self._cache: Optional[list[AdComMeeting]] = None

    def fetch_meetings(self, year: int = None) -> list[AdComMeeting]:
        """Advisory Committee 미팅 목록 가져오기."""
        if year is None:
            year = datetime.now().year

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(self.CALENDAR_URL)
                response.raise_for_status()
                html = response.text

            meetings = self._parse_calendar_html(html)
            self._cache = meetings
            logger.info(f"Fetched {len(meetings)} advisory committee meetings")
            return meetings

        except Exception as e:
            logger.error(f"Failed to fetch advisory calendar: {e}")
            return self._cache or []

    def _parse_calendar_html(self, html: str) -> list[AdComMeeting]:
        """캘린더 HTML 파싱."""
        meetings = []

        # 미팅 항목 패턴 (FDA 페이지 구조에 따라 조정)
        # 일반적으로 날짜 + 위원회 이름 + 주제
        meeting_pattern = re.compile(
            r'(\d{1,2}/\d{1,2}/\d{4})[^<]*<[^>]*>([^<]+)</[^>]*>',
            re.IGNORECASE
        )

        for match in meeting_pattern.finditer(html):
            date_str = match.group(1)
            description = match.group(2).strip()

            meetings.append(AdComMeeting(
                drug_name=None,  # 설명에서 추출 필요
                sponsor=None,
                committee=description,
                meeting_date=date_str,
                meeting_type="scheduled",
            ))

        return meetings

    def find_meetings_for_drug(self, drug_name: str) -> list[AdComMeeting]:
        """특정 약물 관련 미팅 찾기."""
        all_meetings = self.fetch_meetings()
        drug_upper = drug_name.upper()

        relevant = []
        for meeting in all_meetings:
            if meeting.committee and drug_upper in meeting.committee.upper():
                meeting.drug_name = drug_name
                relevant.append(meeting)

        return relevant


class DataContaminationGuard:
    """
    데이터 오염 방지 가드.

    다중 파이프라인에서 발생할 수 있는 데이터 오염을 감지하고 방지.
    """

    def __init__(self, log_dir: str = "data/contamination_log"):
        from pathlib import Path
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def check_update_safety(
        self,
        case_id: str,
        field_name: str,
        new_value: any,
        new_source: str,
        existing_value: any,
        existing_source: str,
    ) -> tuple[bool, str]:
        """
        업데이트 안전성 검사.

        Returns:
            (is_safe, reason)
        """
        # 1. 동일 소스에서 다른 값 → 시간차 업데이트 가능
        if new_source == existing_source:
            return True, "Same source update"

        # 2. 상위 Tier 소스가 하위 Tier 대체 → 안전
        source_priority = {
            "openfda": 1,
            "fda_cder": 1,
            "fda_oopd": 1,
            "sec_edgar": 2,
            "clinicaltrials.gov": 2,
            "pubmed": 2,
            "company_pr": 3,
            "news": 3,
            "legacy_v12": 99,
        }

        new_priority = source_priority.get(new_source, 50)
        existing_priority = source_priority.get(existing_source, 50)

        if new_priority < existing_priority:
            return True, f"Higher tier source ({new_source}) replacing lower tier ({existing_source})"

        # 3. 동일 Tier에서 값 충돌 → 경고
        if new_priority == existing_priority and new_value != existing_value:
            self._log_conflict(case_id, field_name, new_value, new_source, existing_value, existing_source)
            return False, f"Value conflict at same tier: {new_value} vs {existing_value}"

        # 4. 하위 Tier가 상위 Tier 대체 시도 → 거부
        if new_priority > existing_priority:
            return False, f"Lower tier source ({new_source}) cannot replace higher tier ({existing_source})"

        return True, "Update allowed"

    def _log_conflict(
        self,
        case_id: str,
        field_name: str,
        new_value: any,
        new_source: str,
        existing_value: any,
        existing_source: str,
    ):
        """충돌 로그 기록."""
        import json

        log_file = self.log_dir / f"{case_id}_conflicts.json"

        conflicts = []
        if log_file.exists():
            with open(log_file, encoding="utf-8") as f:
                conflicts = json.load(f)

        conflicts.append({
            "timestamp": datetime.now().isoformat(),
            "field": field_name,
            "new_value": new_value,
            "new_source": new_source,
            "existing_value": existing_value,
            "existing_source": existing_source,
        })

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(conflicts, f, indent=2, ensure_ascii=False)

        logger.warning(
            f"Data conflict logged: {case_id}.{field_name} - "
            f"{existing_value} ({existing_source}) vs {new_value} ({new_source})"
        )

    def get_conflict_report(self) -> list[dict]:
        """모든 충돌 보고서 반환."""
        import json

        conflicts = []
        for log_file in self.log_dir.glob("*_conflicts.json"):
            with open(log_file, encoding="utf-8") as f:
                case_conflicts = json.load(f)
                for c in case_conflicts:
                    c["case_id"] = log_file.stem.replace("_conflicts", "")
                conflicts.extend(case_conflicts)

        return conflicts
