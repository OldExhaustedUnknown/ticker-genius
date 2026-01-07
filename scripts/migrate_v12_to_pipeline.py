# -*- coding: utf-8 -*-
"""
Migration Script: pdufa_ml_dataset_v12.json -> Pipeline Structure

M1 마이그레이션 스크립트
- 2020년 이후 데이터만 필터링
- null -> StatusField.unknown() 변환
- ticker/drug/indication 별 그룹화
- data/pipelines/by_ticker/{TICKER}.json 출력

Usage:
    python scripts/migrate_v12_to_pipeline.py
    python scripts/migrate_v12_to_pipeline.py --dry-run
    python scripts/migrate_v12_to_pipeline.py --input /path/to/dataset.json
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime, date, timezone
from typing import Any, Optional
from collections import defaultdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tickergenius.schemas.base import StatusField, DataStatus
from tickergenius.schemas.pipeline import (
    Pipeline, PDUFAEvent, CRLDetail, Application,
    FDADesignations, AdComInfo, TickerPipelines,
    CRLHistoryEntry, LegalIssue,
)


# ============================================================================
# Configuration
# ============================================================================

MIN_YEAR = 2020  # 2020 이전 데이터 제외
DEFAULT_INPUT = Path("D:/Stock/data/ml/pdufa_ml_dataset_v12.json")
DEFAULT_OUTPUT = Path(__file__).parent.parent / "data" / "pipelines" / "by_ticker"


# ============================================================================
# Helper Functions
# ============================================================================

def parse_date(date_str: Optional[str]) -> Optional[date]:
    """날짜 문자열 파싱"""
    if not date_str or date_str in ("", "unknown", "null", "N/A"):
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def generate_indication_code(indication: str) -> str:
    """적응증에서 간략 코드 생성"""
    if not indication:
        return "UNKNOWN"
    
    # 일반적인 적응증 매핑
    mappings = {
        "bladder": "BLADDER",
        "lung": "LUNG",
        "breast": "BREAST",
        "liver": "LIVER",
        "kidney": "KIDNEY",
        "leukemia": "LEUKEMIA",
        "lymphoma": "LYMPHOMA",
        "melanoma": "MELANOMA",
        "myeloma": "MYELOMA",
        "prostate": "PROSTATE",
        "colorectal": "COLORECTAL",
        "colon": "COLON",
        "pancreatic": "PANCREATIC",
        "gastric": "GASTRIC",
        "esophageal": "ESOPHAGEAL",
        "ovarian": "OVARIAN",
        "cervical": "CERVICAL",
        "uterine": "UTERINE",
        "thyroid": "THYROID",
        "brain": "BRAIN",
        "glioblastoma": "GBM",
        "nsclc": "NSCLC",
        "sclc": "SCLC",
        "hcc": "HCC",
        "rcc": "RCC",
        "aml": "AML",
        "cll": "CLL",
        "all": "ALL",
        "mds": "MDS",
        "alzheimer": "ALZHEIMER",
        "parkinson": "PARKINSON",
        "depression": "DEPRESSION",
        "schizophrenia": "SCHIZO",
        "migraine": "MIGRAINE",
        "epilepsy": "EPILEPSY",
        "diabetes": "DIABETES",
        "obesity": "OBESITY",
        "nash": "NASH",
        "heart failure": "HF",
        "atrial fibrillation": "AFIB",
        "hypertension": "HTN",
        "covid": "COVID",
        "hiv": "HIV",
        "hepatitis": "HEP",
        "influenza": "FLU",
        "rsv": "RSV",
        "asthma": "ASTHMA",
        "copd": "COPD",
        "psoriasis": "PSORIASIS",
        "eczema": "ECZEMA",
        "lupus": "LUPUS",
        "rheumatoid": "RA",
        "crohn": "CROHN",
        "ulcerative colitis": "UC",
        "hemophilia": "HEMOPHILIA",
        "sickle cell": "SCD",
        "thalassemia": "THALASSEMIA",
        "duchenne": "DMD",
        "sma": "SMA",
        "huntington": "HUNTINGTON",
        "als": "ALS",
        "fabry": "FABRY",
        "gaucher": "GAUCHER",
        "pompe": "POMPE",
    }
    
    indication_lower = indication.lower()
    for keyword, code in mappings.items():
        if keyword in indication_lower:
            return code
    
    # 매핑 없으면 첫 단어 사용 (최대 10자)
    words = re.sub(r'[^a-zA-Z\s]', '', indication).split()
    if words:
        return words[0].upper()[:10]
    return "OTHER"


def to_status_field(value: Any, field_name: str) -> dict:
    """값을 StatusField dict로 변환 (JSON 직렬화용)"""
    if value is None or value == "" or value == "unknown" or value == "null":
        return {
            "value": None,
            "status": "UNKNOWN",
            "reason": f"{field_name} not verified in legacy data"
        }
    return {
        "value": value,
        "status": "CONFIRMED",
        "source": "legacy_data",
        "verified_at": datetime.now(timezone.utc).isoformat()
    }


def to_status_bool(value: Any, field_name: str) -> dict:
    """Boolean 값을 StatusField dict로 변환"""
    if value is None or value == "":
        return {
            "value": None,
            "status": "UNKNOWN",
            "reason": f"{field_name} not verified in legacy data"
        }
    # 0/1도 처리
    bool_val = bool(value) if isinstance(value, (bool, int)) else value
    return {
        "value": bool_val,
        "status": "CONFIRMED",
        "source": "legacy_data",
        "verified_at": datetime.now(timezone.utc).isoformat()
    }


# ============================================================================
# Migration Logic
# ============================================================================

def convert_case_to_pipeline_event(case: dict) -> tuple[dict, dict]:
    """
    레거시 케이스를 Pipeline과 PDUFAEvent로 변환
    
    Returns: (pipeline_data, event_data)
    """
    ticker = case.get("ticker", "UNKNOWN")
    drug_name = case.get("drug_name", "UNKNOWN")
    indication = case.get("indication", "")
    indication_code = generate_indication_code(indication)
    
    pdufa_date = parse_date(case.get("pdufa_date"))
    if not pdufa_date:
        pdufa_date = date(2020, 1, 1)  # fallback
    
    year = pdufa_date.year
    pipeline_id = f"{ticker}_{drug_name.replace(' ', '_')}_{indication_code}"
    event_id = f"{year}_{pipeline_id}_SEQ1"  # 초기값, 나중에 조정
    
    # Application 정보
    app_type = case.get("application_type", "NDA")
    is_bla = case.get("is_bla", 0)
    is_supplement = case.get("is_supplement", 0)
    
    application_data = {
        "application_type": "BLA" if is_bla else app_type,
        "is_supplement": bool(is_supplement),
        "is_biosimilar": bool(case.get("is_biosimilar", 0)),
    }
    
    # FDA Designations
    designations_data = {
        "breakthrough_therapy": to_status_bool(case.get("breakthrough_therapy"), "breakthrough_therapy"),
        "fast_track": to_status_bool(case.get("fast_track"), "fast_track"),
        "priority_review": to_status_bool(case.get("priority_review"), "priority_review"),
        "orphan_drug": to_status_bool(case.get("orphan_drug"), "orphan_drug"),
        "accelerated_approval": to_status_bool(case.get("accelerated_approval"), "accelerated_approval"),
    }
    
    # AdCom
    adcom_held = case.get("adcom_held")
    adcom_vote_ratio = case.get("adcom_vote_ratio")
    adcom_outcome = case.get("adcom_outcome")
    
    # AdCom held가 0이면 vote_ratio는 EMPTY
    if adcom_held == 0 or adcom_held is False:
        adcom_data = {
            "held": {"value": False, "status": "CONFIRMED", "source": "legacy_data"},
            "vote_ratio": {"value": None, "status": "EMPTY", "reason": "AdCom not held"},
            "outcome": {"value": None, "status": "EMPTY", "reason": "AdCom not held"},
        }
    elif adcom_held == 1 or adcom_held is True:
        adcom_data = {
            "held": {"value": True, "status": "CONFIRMED", "source": "legacy_data"},
            "vote_ratio": to_status_field(adcom_vote_ratio, "adcom_vote_ratio"),
            "outcome": to_status_field(adcom_outcome, "adcom_outcome"),
        }
    else:
        adcom_data = {
            "held": {"value": None, "status": "UNKNOWN", "reason": "adcom_held not verified"},
            "vote_ratio": {"value": None, "status": "UNKNOWN", "reason": "adcom status unknown"},
            "outcome": {"value": None, "status": "UNKNOWN", "reason": "adcom status unknown"},
        }
    
    # CRL 정보
    result = case.get("result", "pending")
    crl_data = None
    
    if result == "crl":
        crl_date_str = case.get("crl_date") or case.get("decision_date")
        crl_date = parse_date(crl_date_str)
        
        crl_data = {
            "crl_date": crl_date.isoformat() if crl_date else pdufa_date.isoformat(),
            "crl_class": to_status_field(case.get("crl_class"), "crl_class"),
            "crl_reason": to_status_field(case.get("crl_reason"), "crl_reason"),
            "crl_category": to_status_field(case.get("crl_reason_category"), "crl_category"),
            "is_cmc_only": {"value": None, "status": "UNKNOWN", "reason": "is_cmc_only not in legacy"},
        }
    
    # PDUFAEvent
    is_resubmission = bool(case.get("is_resubmission", 0))
    decision_date = parse_date(case.get("decision_date"))
    
    event_data = {
        "event_id": event_id,
        "sequence": 1,  # 나중에 그룹화 시 조정
        "pdufa_date": pdufa_date.isoformat(),
        "decision_date": to_status_field(
            decision_date.isoformat() if decision_date else None,
            "decision_date"
        ),
        "result": to_status_field(result, "result"),
        "is_resubmission": is_resubmission,
        "crl": crl_data,
        "data_source": case.get("data_source"),
        "source_confidence": case.get("source_confidence"),
    }
    
    # Pipeline
    pipeline_data = {
        "pipeline_id": pipeline_id,
        "ticker": ticker,
        "company": case.get("company", ""),
        "drug_name": drug_name,
        "indication": indication,
        "indication_code": indication_code,
        "application": application_data,
        "fda_designations": designations_data,
        "adcom": adcom_data,
        "phase3_count": to_status_field(case.get("phase3_count"), "phase3_count"),
        "spa_agreed": to_status_bool(case.get("spa_agreed"), "spa_agreed"),
        "primary_endpoint_met": to_status_bool(case.get("primary_endpoint_met"), "primary_endpoint_met"),
        "is_first_in_class": to_status_bool(case.get("is_first_in_class"), "is_first_in_class"),
        "crl_count": case.get("crl_count"),
        "notes": case.get("notes"),
    }
    
    return pipeline_data, event_data


def group_by_pipeline(cases: list[dict]) -> dict[str, dict]:
    """
    케이스들을 pipeline_id로 그룹화
    
    Returns: {pipeline_id: {"pipeline": {...}, "events": [...]}}
    """
    groups = defaultdict(lambda: {"pipeline": None, "events": []})
    
    for case in cases:
        pipeline_data, event_data = convert_case_to_pipeline_event(case)
        pipeline_id = pipeline_data["pipeline_id"]
        
        if groups[pipeline_id]["pipeline"] is None:
            groups[pipeline_id]["pipeline"] = pipeline_data
        
        groups[pipeline_id]["events"].append(event_data)
    
    # 이벤트 정렬 및 sequence 재설정
    for pipeline_id, group in groups.items():
        events = sorted(group["events"], key=lambda e: e["pdufa_date"])
        for i, event in enumerate(events, 1):
            event["sequence"] = i
            event["event_id"] = f"{event['pdufa_date'][:4]}_{pipeline_id}_SEQ{i}"
            if i > 1:
                event["is_resubmission"] = True
        group["events"] = events
        group["pipeline"]["pdufa_events"] = events
    
    return dict(groups)


def group_by_ticker(pipeline_groups: dict[str, dict]) -> dict[str, list]:
    """
    Pipeline 그룹을 ticker별로 재그룹화
    
    Returns: {ticker: [pipeline1, pipeline2, ...]}
    """
    ticker_groups = defaultdict(list)
    
    for pipeline_id, group in pipeline_groups.items():
        pipeline = group["pipeline"]
        ticker = pipeline["ticker"]
        ticker_groups[ticker].append(pipeline)
    
    return dict(ticker_groups)


# ============================================================================
# Main Migration
# ============================================================================

def migrate(
    input_path: Path = DEFAULT_INPUT,
    output_dir: Path = DEFAULT_OUTPUT,
    dry_run: bool = False
) -> dict:
    """
    메인 마이그레이션 함수
    
    Returns: 통계 정보
    """
    print(f"[M1] Migration Script")
    print(f"  Input:  {input_path}")
    print(f"  Output: {output_dir}")
    print(f"  Min Year: {MIN_YEAR}")
    print(f"  Dry Run: {dry_run}")
    print()
    
    # 1. 데이터 로드
    print("[1/5] Loading legacy dataset...")
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    cases = data.get("cases", [])
    print(f"  Total cases: {len(cases)}")
    
    # 2. 2020년 이후 필터링
    print(f"[2/5] Filtering cases (>= {MIN_YEAR})...")
    filtered_cases = []
    for case in cases:
        pdufa_date = parse_date(case.get("pdufa_date"))
        if pdufa_date and pdufa_date.year >= MIN_YEAR:
            filtered_cases.append(case)
    
    print(f"  Filtered cases: {len(filtered_cases)} (removed {len(cases) - len(filtered_cases)})")
    
    # 3. Pipeline별 그룹화
    print("[3/5] Grouping by pipeline...")
    pipeline_groups = group_by_pipeline(filtered_cases)
    print(f"  Unique pipelines: {len(pipeline_groups)}")
    
    # 4. Ticker별 그룹화
    print("[4/5] Grouping by ticker...")
    ticker_groups = group_by_ticker(pipeline_groups)
    print(f"  Unique tickers: {len(ticker_groups)}")
    
    # 5. 파일 저장
    print("[5/5] Saving files...")
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    stats = {
        "total_cases": len(cases),
        "filtered_cases": len(filtered_cases),
        "unique_pipelines": len(pipeline_groups),
        "unique_tickers": len(ticker_groups),
        "files_created": 0,
        "tickers": [],
    }
    
    for ticker, pipelines in ticker_groups.items():
        # TickerPipelines 구조
        ticker_data = {
            "ticker": ticker,
            "company": pipelines[0].get("company", "") if pipelines else "",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "pipelines": pipelines,
        }
        
        output_file = output_dir / f"{ticker}.json"
        
        if dry_run:
            print(f"  [DRY] Would create: {output_file} ({len(pipelines)} pipelines)")
        else:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(ticker_data, f, indent=2, ensure_ascii=False)
            print(f"  Created: {output_file} ({len(pipelines)} pipelines)")
        
        stats["files_created"] += 1
        stats["tickers"].append({
            "ticker": ticker,
            "pipeline_count": len(pipelines),
            "event_count": sum(len(p.get("pdufa_events", [])) for p in pipelines),
        })
    
    # 통계 파일 저장
    stats_file = output_dir / "_migration_stats.json"
    if not dry_run:
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
        print(f"\n  Stats saved: {stats_file}")
    
    print("\n[DONE]")
    print(f"  Total tickers: {stats['unique_tickers']}")
    print(f"  Total pipelines: {stats['unique_pipelines']}")
    print(f"  Total events: {stats['filtered_cases']}")
    
    return stats


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate v12 dataset to Pipeline structure")
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input JSON file (default: {DEFAULT_INPUT})"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output directory (default: {DEFAULT_OUTPUT})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't write files, just show what would happen"
    )
    
    args = parser.parse_args()
    
    migrate(
        input_path=args.input,
        output_dir=args.output,
        dry_run=args.dry_run
    )
