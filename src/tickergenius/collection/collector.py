"""
Data Collector
===============
Main orchestrator for PDUFA data collection.
"""

import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from tickergenius.collection.models import (
    CollectedCase,
    FieldValue,
    SourceInfo,
    SourceTier,
    ValidationResult,
    ValidationStatus,
)
from tickergenius.collection.api_clients import (
    OpenFDAClient,
    SECEdgarClient,
    ClinicalTrialsClient,
    PubMedClient,
    FDAWarningLettersClient,
)

logger = logging.getLogger(__name__)


class DataCollector:
    """
    Main data collector for PDUFA cases.

    Orchestrates collection from multiple sources:
    - OpenFDA (Tier 1)
    - SEC EDGAR (Tier 2)
    - ClinicalTrials.gov (Tier 2)
    """

    def __init__(
        self,
        output_dir: str = "data/collected",
        legacy_data_path: str = "D:/Stock/data/ml/pdufa_ml_dataset_v12.json",
    ):
        self.output_dir = Path(output_dir)
        self.legacy_data_path = Path(legacy_data_path)

        # API clients
        self.openfda = OpenFDAClient()
        self.sec_edgar = SECEdgarClient()
        self.clinicaltrials = ClinicalTrialsClient()
        self.pubmed = PubMedClient()  # Fallback for NCT IDs
        self.fda_enforcement = FDAWarningLettersClient()  # Warning letters

        # Load legacy data for reference
        self.legacy_cases = self._load_legacy_data()

        # Statistics
        self.stats = {
            "total": 0,
            "collected": 0,
            "validated": 0,
            "needs_review": 0,
            "failed": 0,
            "sources": {
                "openfda_hits": 0,
                "sec_edgar_hits": 0,
                "clinicaltrials_hits": 0,
                "pubmed_hits": 0,
                "enforcement_hits": 0,
                "legacy_only": 0,
            },
        }

    def _load_legacy_data(self) -> dict[str, dict]:
        """Load v12 legacy data as reference."""
        if not self.legacy_data_path.exists():
            logger.warning(f"Legacy data not found: {self.legacy_data_path}")
            return {}

        try:
            with open(self.legacy_data_path, encoding="utf-8") as f:
                data = json.load(f)
            cases = data.get("cases", [])
            # Index by ticker_drugname
            result = {}
            for case in cases:
                key = f"{case.get('ticker', '')}_{case.get('drug_name', '')}".lower()
                result[key] = case
            logger.info(f"Loaded {len(result)} legacy cases")
            return result
        except Exception as e:
            logger.error(f"Failed to load legacy data: {e}")
            return {}

    def collect_case(self, ticker: str, drug_name: str) -> CollectedCase:
        """
        Collect data for a single PDUFA case.

        Args:
            ticker: Company ticker symbol
            drug_name: Drug name

        Returns:
            CollectedCase with data from all sources
        """
        logger.info(f"Collecting data for {ticker} - {drug_name}")

        # Get legacy data for reference
        legacy_key = f"{ticker}_{drug_name}".lower()
        legacy = self.legacy_cases.get(legacy_key)

        # Create case
        case = CollectedCase(
            ticker=ticker,
            drug_name=drug_name,
            legacy_data=legacy,
        )

        # 1. Collect from OpenFDA (Tier 1)
        openfda_hit = self._collect_from_openfda(case, drug_name)

        # 2. Collect from SEC EDGAR (Tier 2)
        sec_hit = self._collect_from_sec_edgar(case, ticker, drug_name)

        # 3. Collect from ClinicalTrials.gov (Tier 2) with PubMed fallback
        ct_hit = self._collect_from_clinicaltrials(case, drug_name)
        pubmed_hit = False
        if not ct_hit or case.nct_id is None:
            # Fallback to PubMed if ClinicalTrials.gov failed
            pubmed_hit = self._collect_nct_from_pubmed(case, drug_name)

        # 4. Check FDA enforcement actions (warning letters)
        enforcement_hit = self._collect_from_fda_enforcement(case, ticker)

        # 5. Merge with legacy data for missing fields
        self._merge_legacy_data(case, legacy)

        # Track if only legacy data was used
        any_api_hit = openfda_hit or sec_hit or ct_hit or pubmed_hit or enforcement_hit
        if not any_api_hit and legacy:
            self.stats["sources"]["legacy_only"] += 1

        return case

    def _collect_from_openfda(self, case: CollectedCase, drug_name: str) -> bool:
        """Collect FDA designation data from OpenFDA. Returns True if data found."""
        try:
            results = self.openfda.search_drug_approvals(drug_name)

            if not results:
                logger.debug(f"No OpenFDA results for {drug_name}")
                return False

            self.stats["sources"]["openfda_hits"] += 1

            # Extract designation info from first matching result
            for result in results:
                products = result.get("products", [])
                submissions = result.get("submissions", [])

                # Check for designations in submissions
                for sub in submissions:
                    sub_type = sub.get("submission_type", "")
                    sub_status = sub.get("submission_status", "")

                    # Check for priority review
                    if "PRIORITY" in sub_type.upper():
                        case.priority_review = FieldValue(
                            value=True,
                            sources=[SourceInfo("openfda", SourceTier.TIER1)],
                            confidence=0.99,
                        )

                    # Check for orphan drug
                    if sub.get("orphan_drug"):
                        case.orphan_drug = FieldValue(
                            value=True,
                            sources=[SourceInfo("openfda", SourceTier.TIER1)],
                            confidence=0.99,
                        )

                    # Check approval date
                    if sub_status == "AP" and sub.get("submission_status_date"):
                        date_str = sub.get("submission_status_date")
                        case.pdufa_date = FieldValue(
                            value=date_str,
                            sources=[SourceInfo("openfda", SourceTier.TIER1)],
                            confidence=0.99,
                        )
                        case.result = FieldValue(
                            value="approved",
                            sources=[SourceInfo("openfda", SourceTier.TIER1)],
                            confidence=0.99,
                        )

                # Check product info for accelerated approval
                for prod in products:
                    if prod.get("te_code"):
                        # TE code might indicate special pathway
                        pass

            return True

        except Exception as e:
            logger.error(f"OpenFDA collection failed for {drug_name}: {e}")
            return False

    def _collect_from_sec_edgar(self, case: CollectedCase, ticker: str, drug_name: str) -> bool:
        """
        Collect PDUFA-related data from SEC EDGAR 8-K filings.

        Searches for 8-K filings mentioning the drug or PDUFA-related keywords.
        Returns True if PDUFA-related data was found.
        """
        try:
            # Get recent 8-K filings for the company
            filings = self.sec_edgar.get_recent_8k_filings(ticker, limit=100)

            if not filings:
                logger.debug(f"No SEC EDGAR filings found for {ticker}")
                return False

            sec_source = SourceInfo("sec_edgar", SourceTier.TIER2)

            # Check each filing for PDUFA-related content
            pdufa_filings = []
            for filing in filings:
                # Extract PDUFA info from filing metadata
                info = self.sec_edgar.extract_pdufa_info(filing)

                if info.get("has_pdufa_mention") or info.get("has_approval") or info.get("has_crl"):
                    pdufa_filings.append({
                        "filing": filing,
                        "info": info,
                    })

            if not pdufa_filings:
                logger.debug(f"No PDUFA-related 8-K filings for {ticker}")
                return False

            self.stats["sources"]["sec_edgar_hits"] += 1
            logger.info(f"Found {len(pdufa_filings)} PDUFA-related 8-K filings for {ticker}")

            # Extract information from PDUFA-related filings
            for pf in pdufa_filings:
                info = pf["info"]
                filing = pf["filing"]
                filing_date = filing.get("filingDate")

                # If we found an approval mention and don't have result yet
                if info.get("has_approval") and case.result is None:
                    case.result = FieldValue(
                        value="approved",
                        sources=[sec_source],
                        confidence=0.85,
                        needs_manual_review=True,
                    )
                    if filing_date and case.pdufa_date is None:
                        case.pdufa_date = FieldValue(
                            value=filing_date,
                            sources=[sec_source],
                            confidence=0.80,
                            needs_manual_review=True,
                        )

                # If we found a CRL mention
                if info.get("has_crl") and case.result is None:
                    case.result = FieldValue(
                        value="crl",
                        sources=[sec_source],
                        confidence=0.85,
                        needs_manual_review=True,
                    )
                    case.has_prior_crl = FieldValue(
                        value=True,
                        sources=[sec_source],
                        confidence=0.85,
                    )

                # If AdCom was held
                if info.get("has_adcom"):
                    case.adcom_held = FieldValue(
                        value=True,
                        sources=[sec_source],
                        confidence=0.90,
                    )
                    if filing_date:
                        case.adcom_date = FieldValue(
                            value=filing_date,
                            sources=[sec_source],
                            confidence=0.80,
                            needs_manual_review=True,
                        )

                # Designation info
                if info.get("has_designation"):
                    keywords = info.get("detected_keywords", [])
                    if "BREAKTHROUGH" in keywords and case.breakthrough_therapy is None:
                        case.breakthrough_therapy = FieldValue(
                            value=True,
                            sources=[sec_source],
                            confidence=0.85,
                        )
                    if "PRIORITY REVIEW" in keywords and case.priority_review is None:
                        case.priority_review = FieldValue(
                            value=True,
                            sources=[sec_source],
                            confidence=0.85,
                        )
                    if "FAST TRACK" in keywords and case.fast_track is None:
                        case.fast_track = FieldValue(
                            value=True,
                            sources=[sec_source],
                            confidence=0.85,
                        )
                    if "ORPHAN DRUG" in keywords and case.orphan_drug is None:
                        case.orphan_drug = FieldValue(
                            value=True,
                            sources=[sec_source],
                            confidence=0.85,
                        )

            return True

        except Exception as e:
            logger.error(f"SEC EDGAR collection failed for {ticker}: {e}")
            return False

    def _collect_from_clinicaltrials(self, case: CollectedCase, drug_name: str) -> bool:
        """Collect clinical trial data from ClinicalTrials.gov. Returns True if data found."""
        try:
            results = self.clinicaltrials.search_by_drug_sponsor(drug_name)

            if not results:
                logger.debug(f"No ClinicalTrials.gov results for {drug_name}")
                return False

            # Find the most relevant Phase 3 trial
            phase3_trials = []
            for study in results:
                protocol = study.get("protocolSection", {})
                design = protocol.get("designModule", {})
                phases = design.get("phases", [])

                if "PHASE3" in phases or "Phase 3" in str(phases):
                    phase3_trials.append(study)

            if phase3_trials:
                self.stats["sources"]["clinicaltrials_hits"] += 1

                # Use first Phase 3 trial
                trial = phase3_trials[0]
                protocol = trial.get("protocolSection", {})
                id_module = protocol.get("identificationModule", {})

                nct_id = id_module.get("nctId")
                if nct_id:
                    case.nct_id = FieldValue(
                        value=nct_id,
                        sources=[SourceInfo("clinicaltrials.gov", SourceTier.TIER2)],
                        confidence=0.90,
                    )

                case.phase = FieldValue(
                    value="phase3",
                    sources=[SourceInfo("clinicaltrials.gov", SourceTier.TIER2)],
                    confidence=0.90,
                )

                return True

            return False

        except Exception as e:
            logger.error(f"ClinicalTrials.gov collection failed for {drug_name}: {e}")
            return False

    def _collect_nct_from_pubmed(self, case: CollectedCase, drug_name: str) -> bool:
        """
        Fallback: Find NCT IDs via PubMed clinical trial publications.

        Used when ClinicalTrials.gov is unavailable (403 errors).
        Returns True if NCT ID found.
        """
        try:
            nct_ids = self.pubmed.find_nct_ids_for_drug(drug_name)

            if not nct_ids:
                logger.debug(f"No NCT IDs found via PubMed for {drug_name}")
                return False

            self.stats["sources"]["pubmed_hits"] += 1

            # Use first NCT ID (most relevant)
            case.nct_id = FieldValue(
                value=nct_ids[0],
                sources=[SourceInfo("pubmed", SourceTier.TIER2)],
                confidence=0.80,
                needs_manual_review=True,
            )

            logger.info(f"Found NCT ID via PubMed for {drug_name}: {nct_ids[0]}")
            return True

        except Exception as e:
            logger.error(f"PubMed NCT search failed for {drug_name}: {e}")
            return False

    def _collect_from_fda_enforcement(self, case: CollectedCase, ticker: str) -> bool:
        """
        Check FDA enforcement actions for the company.

        Looks for recent warning letters or recalls that might affect
        manufacturing reliability (PAI risk factor).
        Returns True if enforcement action found.
        """
        try:
            # Try to get company name from legacy data
            company_name = None
            if case.legacy_data:
                company_name = case.legacy_data.get("company_name")

            # If no company name, try ticker as search term
            if not company_name:
                company_name = ticker

            # Check for recent enforcement actions
            has_enforcement = self.fda_enforcement.has_recent_enforcement(company_name, years=3)

            if has_enforcement:
                self.stats["sources"]["enforcement_hits"] += 1
                case.has_warning_letter = FieldValue(
                    value=True,
                    sources=[SourceInfo("fda_enforcement", SourceTier.TIER1)],
                    confidence=0.90,
                )
                logger.info(f"Found FDA enforcement action for {ticker}")
                return True

            return False

        except Exception as e:
            logger.error(f"FDA enforcement check failed for {ticker}: {e}")
            return False

    def _merge_legacy_data(self, case: CollectedCase, legacy: Optional[dict]):
        """Merge legacy data for fields not collected from APIs."""
        if not legacy:
            return

        legacy_source = SourceInfo("legacy_v12", SourceTier.TIER3)

        # PDUFA date (if not from OpenFDA)
        if case.pdufa_date is None and legacy.get("pdufa_date"):
            case.pdufa_date = FieldValue(
                value=legacy["pdufa_date"],
                sources=[legacy_source],
                confidence=0.75,
                needs_manual_review=True,  # Legacy data needs verification
            )

        # Result (if not from OpenFDA)
        if case.result is None and legacy.get("result"):
            case.result = FieldValue(
                value=legacy["result"],
                sources=[legacy_source],
                confidence=0.75,
                needs_manual_review=True,
            )

        # Breakthrough therapy
        if case.breakthrough_therapy is None and legacy.get("breakthrough_therapy") is not None:
            case.breakthrough_therapy = FieldValue(
                value=legacy["breakthrough_therapy"],
                sources=[legacy_source],
                confidence=0.75,
                needs_manual_review=True,
            )

        # Priority review
        if case.priority_review is None and legacy.get("priority_review") is not None:
            case.priority_review = FieldValue(
                value=legacy["priority_review"],
                sources=[legacy_source],
                confidence=0.75,
                needs_manual_review=True,
            )

        # Fast track
        if case.fast_track is None and legacy.get("fast_track") is not None:
            case.fast_track = FieldValue(
                value=legacy["fast_track"],
                sources=[legacy_source],
                confidence=0.75,
                needs_manual_review=True,
            )

        # Orphan drug
        if case.orphan_drug is None and legacy.get("orphan_drug") is not None:
            case.orphan_drug = FieldValue(
                value=legacy["orphan_drug"],
                sources=[legacy_source],
                confidence=0.75,
                needs_manual_review=True,
            )

        # Accelerated approval
        if case.accelerated_approval is None and legacy.get("accelerated_approval") is not None:
            case.accelerated_approval = FieldValue(
                value=legacy["accelerated_approval"],
                sources=[legacy_source],
                confidence=0.75,
                needs_manual_review=True,
            )

        # CRL info
        if legacy.get("crl_class"):
            case.has_prior_crl = FieldValue(
                value=True,
                sources=[legacy_source],
                confidence=0.75,
            )
            case.crl_class = FieldValue(
                value=legacy["crl_class"],
                sources=[legacy_source],
                confidence=0.75,
            )

        # Is resubmission
        if legacy.get("is_resubmission") is not None:
            case.is_resubmission = FieldValue(
                value=legacy["is_resubmission"],
                sources=[legacy_source],
                confidence=0.75,
            )

    def validate_case(self, case: CollectedCase) -> ValidationResult:
        """
        Validate a collected case.

        Checks:
        1. Required fields present
        2. Date formats valid
        3. Cross-validation between sources
        """
        result = ValidationResult(case_id=case.case_id, status=ValidationStatus.VALID)

        # Check required fields
        required_fields = [
            ("pdufa_date", case.pdufa_date),
        ]

        for name, field in required_fields:
            if field is None or field.value is None:
                result.field_validations[name] = ValidationStatus.MISSING
                result.errors.append(f"Missing required field: {name}")
                result.status = ValidationStatus.NEEDS_REVIEW
            else:
                result.field_validations[name] = ValidationStatus.VALID

        # Check for fields needing manual review
        fields_to_check = [
            ("breakthrough_therapy", case.breakthrough_therapy),
            ("priority_review", case.priority_review),
            ("fast_track", case.fast_track),
            ("orphan_drug", case.orphan_drug),
        ]

        for name, field in fields_to_check:
            if field and field.needs_manual_review:
                result.field_validations[name] = ValidationStatus.NEEDS_REVIEW
                result.warnings.append(f"Field needs manual review: {name}")
                if result.status == ValidationStatus.VALID:
                    result.status = ValidationStatus.NEEDS_REVIEW

        return result

    def save_case(self, case: CollectedCase, validation: ValidationResult):
        """Save collected case to disk."""
        # Save to processed folder
        processed_dir = self.output_dir / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)

        output_path = processed_dir / f"{case.ticker}_{case.case_id}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(case.to_dict(), f, indent=2, ensure_ascii=False)

        # Save validation log
        log_dir = self.output_dir / "validation_log"
        log_dir.mkdir(parents=True, exist_ok=True)

        log_path = log_dir / f"{case.case_id}_validation.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump({
                "case_id": validation.case_id,
                "status": validation.status.value,
                "field_validations": {k: v.value for k, v in validation.field_validations.items()},
                "errors": validation.errors,
                "warnings": validation.warnings,
                "validated_at": datetime.now().isoformat(),
            }, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved case {case.case_id} (status: {validation.status.value})")

    def collect_all(self, limit: int = None) -> dict:
        """
        Collect data for all cases from legacy dataset.

        Args:
            limit: Optional limit for testing

        Returns:
            Collection statistics
        """
        cases_to_process = list(self.legacy_cases.items())
        if limit:
            cases_to_process = cases_to_process[:limit]

        self.stats["total"] = len(cases_to_process)

        for i, (key, legacy) in enumerate(cases_to_process):
            ticker = legacy.get("ticker", "")
            drug_name = legacy.get("drug_name", "")

            if not ticker or not drug_name:
                logger.warning(f"Skipping case with missing ticker/drug_name: {key}")
                self.stats["failed"] += 1
                continue

            try:
                # Collect
                case = self.collect_case(ticker, drug_name)
                self.stats["collected"] += 1

                # Validate
                validation = self.validate_case(case)
                if validation.is_valid:
                    self.stats["validated"] += 1
                elif validation.needs_review:
                    self.stats["needs_review"] += 1

                # Save
                self.save_case(case, validation)

                if (i + 1) % 10 == 0:
                    logger.info(f"Progress: {i+1}/{len(cases_to_process)}")

            except Exception as e:
                logger.error(f"Failed to process {ticker} - {drug_name}: {e}")
                self.stats["failed"] += 1

        return self.stats

    def get_legacy_cases_list(self) -> list[tuple[str, str]]:
        """Get list of (ticker, drug_name) from legacy data."""
        return [
            (legacy.get("ticker", ""), legacy.get("drug_name", ""))
            for legacy in self.legacy_cases.values()
            if legacy.get("ticker") and legacy.get("drug_name")
        ]
