"""
Incremental Verification Runner
================================
수집된 데이터를 점진적으로 검증하고 레거시 의존도를 줄이는 실행기.

핵심 전략:
1. 작동하는 소스부터 활용 (OpenFDA, SEC EDGAR, PubMed)
2. 레거시 필드를 하나씩 검증된 값으로 대체
3. 검증 불가 필드는 UNVERIFIED로 명시 (레거시 값 사용 X)
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from tickergenius.collection.incremental_verifier import (
    IncrementalVerifier,
    VerifiableCase,
    VerifiedValue,
    VerificationStatus,
    SourceTier,
)
from tickergenius.collection.api_clients import (
    OpenFDAClient,
    SECEdgarClient,
    PubMedClient,
    FDAWarningLettersClient,
)
from tickergenius.collection.official_sources import DataContaminationGuard

logger = logging.getLogger(__name__)


class VerificationRunner:
    """
    점진적 검증 실행기.

    레거시 데이터를 신뢰하지 않고, 공식 소스에서 하나씩 검증.
    """

    def __init__(
        self,
        collected_dir: str = "data/collected/processed",
        verified_dir: str = "data/verified",
    ):
        self.collected_dir = Path(collected_dir)
        self.verified_dir = Path(verified_dir)
        self.verified_dir.mkdir(parents=True, exist_ok=True)

        # 검증 시스템
        self.verifier = IncrementalVerifier(verified_dir)
        self.guard = DataContaminationGuard()

        # API 클라이언트
        self.openfda = OpenFDAClient()
        self.sec_edgar = SECEdgarClient()
        self.pubmed = PubMedClient()
        self.fda_enforcement = FDAWarningLettersClient()

        # 통계
        self.stats = {
            "total_cases": 0,
            "verified_fields": 0,
            "legacy_replaced": 0,
            "not_found": 0,
            "conflicts": 0,
        }

    def import_all_cases(self):
        """수집된 케이스를 검증 시스템으로 가져오기."""
        case_files = list(self.collected_dir.glob("*.json"))
        logger.info(f"Importing {len(case_files)} cases for verification")

        for case_file in case_files:
            with open(case_file, encoding="utf-8") as f:
                collected = json.load(f)

            case = self.verifier.import_from_collected(collected)
            self.verifier.save_case(case)

        self.stats["total_cases"] = len(case_files)
        logger.info(f"Imported {len(case_files)} cases")

    def verify_field_openfda(
        self,
        case: VerifiableCase,
        field_name: str,
        drug_name: str,
    ) -> bool:
        """OpenFDA에서 필드 검증 시도."""
        try:
            results = self.openfda.search_drug_approvals(drug_name)
            if not results:
                return False

            for result in results:
                submissions = result.get("submissions", [])
                products = result.get("products", [])

                for sub in submissions:
                    value = None

                    if field_name == "pdufa_date":
                        if sub.get("submission_status") == "AP":
                            value = sub.get("submission_status_date")

                    elif field_name == "result":
                        if sub.get("submission_status") == "AP":
                            value = "approved"

                    elif field_name == "priority_review":
                        if "PRIORITY" in sub.get("submission_type", "").upper():
                            value = True

                    elif field_name == "orphan_drug":
                        if sub.get("orphan_drug"):
                            value = True

                    if value is not None:
                        # 오염 방지 검사
                        existing = case.fields.get(field_name)
                        if existing:
                            is_safe, reason = self.guard.check_update_safety(
                                case.case_id, field_name,
                                value, "openfda",
                                existing.value, existing.source_name,
                            )
                            if not is_safe:
                                self.stats["conflicts"] += 1
                                logger.warning(f"Update blocked: {reason}")
                                continue

                        self.verifier.update_field(
                            case, field_name, value,
                            "openfda", SourceTier.TIER1_OFFICIAL,
                        )
                        self.stats["verified_fields"] += 1
                        return True

            return False

        except Exception as e:
            logger.error(f"OpenFDA verification failed for {drug_name}.{field_name}: {e}")
            return False

    def verify_field_sec_edgar(
        self,
        case: VerifiableCase,
        field_name: str,
        ticker: str,
        drug_name: str,
    ) -> bool:
        """SEC EDGAR에서 필드 검증 시도."""
        try:
            filings = self.sec_edgar.get_recent_8k_filings(ticker, limit=100)
            if not filings:
                return False

            for filing in filings:
                info = self.sec_edgar.extract_pdufa_info(filing)
                value = None

                if field_name == "adcom_held" and info.get("has_adcom"):
                    value = True

                elif field_name == "breakthrough_therapy" and "BREAKTHROUGH" in info.get("detected_keywords", []):
                    value = True

                elif field_name == "priority_review" and "PRIORITY REVIEW" in info.get("detected_keywords", []):
                    value = True

                elif field_name == "has_prior_crl" and info.get("has_crl"):
                    value = True

                if value is not None:
                    existing = case.fields.get(field_name)
                    if existing:
                        is_safe, reason = self.guard.check_update_safety(
                            case.case_id, field_name,
                            value, "sec_edgar",
                            existing.value, existing.source_name,
                        )
                        if not is_safe:
                            self.stats["conflicts"] += 1
                            continue

                    self.verifier.update_field(
                        case, field_name, value,
                        "sec_edgar", SourceTier.TIER2_REGULATED,
                    )
                    self.stats["verified_fields"] += 1
                    return True

            return False

        except Exception as e:
            logger.error(f"SEC EDGAR verification failed for {ticker}.{field_name}: {e}")
            return False

    def verify_field_pubmed(
        self,
        case: VerifiableCase,
        field_name: str,
        drug_name: str,
    ) -> bool:
        """PubMed에서 NCT ID 검증 시도."""
        if field_name != "nct_id":
            return False

        try:
            nct_ids = self.pubmed.find_nct_ids_for_drug(drug_name)
            if not nct_ids:
                return False

            self.verifier.update_field(
                case, field_name, nct_ids[0],
                "pubmed", SourceTier.TIER2_REGULATED,
            )
            self.stats["verified_fields"] += 1
            return True

        except Exception as e:
            logger.error(f"PubMed verification failed for {drug_name}: {e}")
            return False

    def verify_single_case(self, case: VerifiableCase) -> dict:
        """단일 케이스의 모든 레거시 필드 검증 시도."""
        progress_before = case.get_verification_progress()

        # 레거시 필드 찾기
        legacy_fields = [
            name for name, val in case.fields.items()
            if val.status == VerificationStatus.LEGACY
        ]

        for field_name in legacy_fields:
            verified = False

            # 1. OpenFDA 시도
            if not verified:
                verified = self.verify_field_openfda(case, field_name, case.drug_name)

            # 2. SEC EDGAR 시도
            if not verified:
                verified = self.verify_field_sec_edgar(case, field_name, case.ticker, case.drug_name)

            # 3. PubMed 시도 (NCT ID)
            if not verified and field_name == "nct_id":
                verified = self.verify_field_pubmed(case, field_name, case.drug_name)

            # 검증 실패 시 NOT_FOUND로 마크 (레거시 값 버림)
            if not verified:
                self.verifier.mark_not_found(case, field_name, "all_sources_tried")
                self.stats["not_found"] += 1

            # 레거시 대체 성공
            if verified:
                self.stats["legacy_replaced"] += 1

        # 저장
        self.verifier.save_case(case)

        progress_after = case.get_verification_progress()
        return {
            "case_id": case.case_id,
            "before": progress_before,
            "after": progress_after,
            "fields_verified": progress_after["verified"] - progress_before["verified"],
        }

    def run_verification(self, limit: int = None) -> dict:
        """
        전체 검증 실행.

        Args:
            limit: 처리할 케이스 수 제한 (테스트용)
        """
        case_files = list(self.verified_dir.glob("*.json"))
        if limit:
            case_files = case_files[:limit]

        logger.info(f"Running verification on {len(case_files)} cases")

        results = []
        for i, case_file in enumerate(case_files):
            case = self.verifier.load_case(case_file.stem)
            if not case:
                continue

            result = self.verify_single_case(case)
            results.append(result)

            if (i + 1) % 10 == 0:
                logger.info(f"Progress: {i+1}/{len(case_files)}")

        return {
            "total_processed": len(results),
            "stats": self.stats,
            "results": results,
        }

    def get_verification_report(self) -> dict:
        """검증 현황 보고서."""
        case_files = list(self.verified_dir.glob("*.json"))

        report = {
            "total_cases": len(case_files),
            "fully_verified": 0,
            "legacy_free": 0,
            "by_field": {},
            "legacy_dependent": [],
        }

        field_counts = {}

        for case_file in case_files:
            case = self.verifier.load_case(case_file.stem)
            if not case:
                continue

            progress = case.get_verification_progress()
            if progress["progress_pct"] == 100:
                report["fully_verified"] += 1
            if progress["legacy_free"]:
                report["legacy_free"] += 1
            else:
                report["legacy_dependent"].append(case.case_id)

            # 필드별 통계
            for field_name, val in case.fields.items():
                if field_name not in field_counts:
                    field_counts[field_name] = {
                        "verified": 0, "legacy": 0, "not_found": 0, "unverified": 0
                    }

                if val.status == VerificationStatus.VERIFIED:
                    field_counts[field_name]["verified"] += 1
                elif val.status == VerificationStatus.LEGACY:
                    field_counts[field_name]["legacy"] += 1
                elif val.status == VerificationStatus.NOT_FOUND:
                    field_counts[field_name]["not_found"] += 1
                else:
                    field_counts[field_name]["unverified"] += 1

        report["by_field"] = field_counts

        # 레거시 의존도 계산
        total_fields = sum(
            sum(counts.values())
            for counts in field_counts.values()
        )
        legacy_fields = sum(
            counts.get("legacy", 0)
            for counts in field_counts.values()
        )
        report["legacy_dependency_pct"] = (legacy_fields * 100 // total_fields) if total_fields else 0

        return report


def run_incremental_verification(limit: int = None):
    """점진적 검증 실행 (메인 함수)."""
    import logging
    logging.basicConfig(level=logging.INFO)

    runner = VerificationRunner()

    # 1. 케이스 가져오기
    print("Step 1: Importing cases...")
    runner.import_all_cases()

    # 2. 검증 실행
    print(f"Step 2: Running verification (limit={limit})...")
    results = runner.run_verification(limit=limit)

    # 3. 보고서 출력
    print("\nStep 3: Verification Report")
    print("=" * 60)
    report = runner.get_verification_report()
    print(f"Total Cases: {report['total_cases']}")
    print(f"Fully Verified: {report['fully_verified']}")
    print(f"Legacy-Free: {report['legacy_free']}")
    print(f"Legacy Dependency: {report['legacy_dependency_pct']}%")

    print("\nField-level Status:")
    for field, counts in report["by_field"].items():
        print(f"  {field}: V={counts['verified']} L={counts['legacy']} NF={counts['not_found']}")

    return report


if __name__ == "__main__":
    run_incremental_verification(limit=10)
