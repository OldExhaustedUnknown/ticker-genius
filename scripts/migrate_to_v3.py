#!/usr/bin/env python
"""
Wave 3: 데이터 마이그레이션 스크립트
====================================
기존 enriched JSON (v2) → 신규 PDUFAEvent 스키마 (v3)

변환 내용:
1. StatusField 구조 유지 (이미 호환)
2. 날짜 포맷 정규화 (YYYYMMDD → ISO date)
3. 12개 신규 필드 초기화 (not_searched)
4. enrollment → Enrollment 객체
5. adcom_info vote 필드 변환
6. 메타데이터 추가 (migrated_at, schema_version)

사용법:
    python scripts/migrate_to_v3.py --dry-run        # 테스트 (10개)
    python scripts/migrate_to_v3.py --limit 50       # 50개만 실행
    python scripts/migrate_to_v3.py                  # 전체 실행
    python scripts/migrate_to_v3.py --validate-only  # 검증만
"""

import argparse
import json
import logging
import shutil
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Any

# src를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# === 경로 설정 ===
DATA_DIR = Path(__file__).parent.parent / "data"
ENRICHED_DIR = DATA_DIR / "enriched"
BACKUP_DIR = DATA_DIR / "enriched_backup_v2"
OUTPUT_DIR = DATA_DIR / "enriched_v3"  # 새 폴더에 출력 (안전)


# === 12개 신규 필드 ===
NEW_FIELDS_WAVE2 = [
    "is_single_arm",
    "trial_region",
    "is_biosimilar",
    "is_first_in_class",
    "crl_reason_type",
    "warning_letter_date",
    "fda_483_date",
    "fda_483_observations",
    "cdmo_name",
    "pai_date",
    "clinical_hold_history",
]


def parse_pdufa_date(date_str: str) -> Optional[str]:
    """다양한 날짜 형식을 ISO 포맷으로 변환."""
    if not date_str:
        return None

    # 이미 ISO 포맷
    if "-" in date_str and len(date_str) == 10:
        return date_str

    # YYYYMMDD 포맷
    if len(date_str) == 8 and date_str.isdigit():
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    # ISO datetime 포맷
    if "T" in date_str:
        return date_str.split("T")[0]

    return date_str


def create_not_searched_field() -> dict:
    """StatusField.not_searched() 딕셔너리 생성."""
    return {
        "status": "not_searched",
        "value": None,
        "source": "",
        "confidence": 0.0,
        "tier": None,
        "evidence": [],
        "searched_sources": [],
        "last_searched": None,
        "error": None,
        "note": None,
    }


def migrate_enrollment(old_enrollment: Any) -> Optional[dict]:
    """enrollment 필드를 Enrollment 객체로 변환."""
    if old_enrollment is None:
        return None

    if isinstance(old_enrollment, int):
        return {
            "count": old_enrollment,
            "type": "ACTUAL",
            "nct_id": None,
            "source": "legacy_migration",
            "fetched_at": None,
        }

    if isinstance(old_enrollment, dict):
        return {
            "count": old_enrollment.get("count", 0),
            "type": old_enrollment.get("type", "ACTUAL"),
            "nct_id": old_enrollment.get("nct_id"),
            "source": old_enrollment.get("source", "legacy_migration"),
            "fetched_at": old_enrollment.get("fetched_at"),
        }

    return None


def migrate_adcom_info(old_adcom: Optional[dict]) -> Optional[dict]:
    """adcom_info vote 필드 변환."""
    if not old_adcom:
        return None

    result = {
        "scheduled": old_adcom.get("scheduled", False),
        "held": old_adcom.get("held", False),
        "date": old_adcom.get("date"),
        "outcome": old_adcom.get("outcome"),
        "vote_for": None,
        "vote_against": None,
    }

    # vote 필드 변환
    vote = old_adcom.get("vote")
    if isinstance(vote, dict):
        result["vote_for"] = vote.get("for")
        result["vote_against"] = vote.get("against")
    elif isinstance(vote, int):
        # 단일 숫자면 vote_for로 가정
        result["vote_for"] = vote

    return result


def migrate_record(old_data: dict) -> dict:
    """단일 레코드 마이그레이션."""
    new_data = {}

    # === A. 식별자 (직접 복사) ===
    new_data["event_id"] = old_data.get("event_id", "")
    new_data["ticker"] = old_data.get("ticker", "")
    new_data["company_name"] = old_data.get("company_name", "")
    new_data["drug_name"] = old_data.get("drug_name", "")
    new_data["result"] = old_data.get("result", "pending")

    # 날짜 변환
    pdufa_date = old_data.get("pdufa_date", "")
    new_data["pdufa_date"] = parse_pdufa_date(pdufa_date)

    # === B. 기존 StatusField (직접 복사) ===
    status_fields = [
        "approval_type", "indication", "generic_name", "therapeutic_area",
        "mechanism_of_action", "phase", "primary_endpoint_met", "p_value",
        "effect_size", "has_prior_crl", "is_resubmission", "pai_passed",
        "warning_letter", "safety_signal"
    ]

    for field in status_fields:
        if field in old_data:
            value = old_data[field]
            if isinstance(value, dict) and "status" in value:
                new_data[field] = value
            elif value is not None:
                # 문자열 등 단순값 → StatusField 래핑
                new_data[field] = {
                    "status": "found",
                    "value": value,
                    "source": "legacy_migration",
                    "confidence": 0.75,
                    "tier": 3,
                    "evidence": [],
                    "searched_sources": ["legacy_v12"],
                    "last_searched": datetime.utcnow().isoformat(),
                    "error": None,
                    "note": None,
                }
            else:
                new_data[field] = create_not_searched_field()
        else:
            new_data[field] = create_not_searched_field()

    # === C. 단순 값 (직접 복사) ===
    new_data["p_value_numeric"] = old_data.get("p_value_numeric")
    new_data["nct_ids"] = old_data.get("nct_ids", [])
    new_data["phase3_study_names"] = old_data.get("phase3_study_names", [])
    new_data["prior_crl_reason"] = old_data.get("prior_crl_reason")

    # === D. 중첩 객체 ===
    new_data["enrollment"] = migrate_enrollment(old_data.get("enrollment"))
    new_data["fda_designations"] = old_data.get("fda_designations")
    new_data["adcom_info"] = migrate_adcom_info(old_data.get("adcom_info"))

    # === E. 12개 신규 필드 초기화 ===
    for field in NEW_FIELDS_WAVE2:
        if field not in new_data:
            new_data[field] = create_not_searched_field()

    # === F. 파생 필드 ===
    new_data["days_to_pdufa"] = old_data.get("days_to_pdufa")
    new_data["pdufa_status"] = old_data.get("pdufa_status")
    new_data["risk_tier"] = old_data.get("risk_tier")
    new_data["days_calculated_at"] = old_data.get("days_calculated_at")

    # === G. 메타데이터 ===
    new_data["original_case_id"] = old_data.get("original_case_id", old_data.get("event_id"))
    new_data["data_quality_score"] = old_data.get("data_quality_score", 0.0)
    new_data["collected_at"] = old_data.get("collected_at")
    new_data["enriched_at"] = old_data.get("enriched_at")
    new_data["needs_manual_review"] = old_data.get("needs_manual_review", False)
    new_data["review_reasons"] = old_data.get("review_reasons", [])

    # 마이그레이션 메타데이터
    new_data["migrated_at"] = datetime.utcnow().isoformat()
    new_data["schema_version"] = "3.0"

    return new_data


def validate_record(data: dict, filename: str) -> list[str]:
    """레코드 검증."""
    errors = []

    # 필수 필드 확인
    required = ["event_id", "ticker", "drug_name", "pdufa_date"]
    for field in required:
        if not data.get(field):
            errors.append(f"{filename}: Missing required field '{field}'")

    # 12개 신규 필드 확인
    for field in NEW_FIELDS_WAVE2:
        if field not in data:
            errors.append(f"{filename}: Missing new field '{field}'")
        elif not isinstance(data[field], dict) or "status" not in data[field]:
            errors.append(f"{filename}: Field '{field}' is not a valid StatusField")

    # 날짜 형식 확인
    pdufa_date = data.get("pdufa_date")
    if pdufa_date and not (isinstance(pdufa_date, str) and len(pdufa_date) == 10 and "-" in pdufa_date):
        errors.append(f"{filename}: Invalid pdufa_date format: {pdufa_date}")

    return errors


def create_backup():
    """백업 폴더 생성."""
    if BACKUP_DIR.exists():
        logger.info(f"Backup already exists: {BACKUP_DIR}")
        return

    logger.info(f"Creating backup: {ENRICHED_DIR} → {BACKUP_DIR}")
    shutil.copytree(ENRICHED_DIR, BACKUP_DIR)
    logger.info(f"Backup completed: {len(list(BACKUP_DIR.glob('*.json')))} files")


def run_migration(
    limit: Optional[int] = None,
    dry_run: bool = False,
    validate_only: bool = False,
    in_place: bool = False,
) -> dict:
    """마이그레이션 실행."""
    stats = {
        "total": 0,
        "migrated": 0,
        "errors": 0,
        "skipped": 0,
        "validation_errors": [],
    }

    # 입력 파일 목록
    input_files = sorted(ENRICHED_DIR.glob("*.json"))
    stats["total"] = len(input_files)

    if limit:
        input_files = input_files[:limit]

    logger.info(f"Processing {len(input_files)} files (total: {stats['total']})")

    # 출력 디렉토리
    output_dir = ENRICHED_DIR if in_place else OUTPUT_DIR
    if not in_place:
        output_dir.mkdir(parents=True, exist_ok=True)

    for i, input_file in enumerate(input_files, 1):
        try:
            # 읽기
            with open(input_file, "r", encoding="utf-8") as f:
                old_data = json.load(f)

            # 마이그레이션
            new_data = migrate_record(old_data)

            # 검증
            errors = validate_record(new_data, input_file.name)
            if errors:
                stats["validation_errors"].extend(errors)
                if not dry_run:
                    logger.warning(f"Validation errors in {input_file.name}")

            if validate_only:
                stats["migrated"] += 1
                continue

            # 저장
            if not dry_run:
                output_file = output_dir / input_file.name
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(new_data, f, indent=2, ensure_ascii=False, default=str)

            stats["migrated"] += 1

            if i % 100 == 0:
                logger.info(f"Progress: {i}/{len(input_files)}")

        except Exception as e:
            stats["errors"] += 1
            logger.error(f"Error processing {input_file.name}: {e}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Migrate enriched JSON to v3 schema")
    parser.add_argument("--dry-run", action="store_true", help="Test run (10 files, no write)")
    parser.add_argument("--limit", type=int, help="Limit number of files to process")
    parser.add_argument("--validate-only", action="store_true", help="Only validate, don't write")
    parser.add_argument("--in-place", action="store_true", help="Overwrite original files (dangerous)")
    parser.add_argument("--no-backup", action="store_true", help="Skip backup creation")
    args = parser.parse_args()

    # 입력 확인
    if not ENRICHED_DIR.exists():
        logger.error(f"Input directory not found: {ENRICHED_DIR}")
        sys.exit(1)

    # Dry run 설정
    if args.dry_run:
        args.limit = args.limit or 10
        logger.info("=== DRY RUN MODE (no files written) ===")

    # 백업
    if not args.no_backup and not args.dry_run and not args.validate_only:
        create_backup()

    # 실행
    logger.info("Starting migration...")
    stats = run_migration(
        limit=args.limit,
        dry_run=args.dry_run,
        validate_only=args.validate_only,
        in_place=args.in_place,
    )

    # 결과 출력
    logger.info("=" * 50)
    logger.info("Migration Results:")
    logger.info(f"  Total files: {stats['total']}")
    logger.info(f"  Migrated: {stats['migrated']}")
    logger.info(f"  Errors: {stats['errors']}")
    logger.info(f"  Validation errors: {len(stats['validation_errors'])}")

    if stats["validation_errors"]:
        logger.warning("Validation errors:")
        for err in stats["validation_errors"][:10]:
            logger.warning(f"  {err}")
        if len(stats["validation_errors"]) > 10:
            logger.warning(f"  ... and {len(stats['validation_errors']) - 10} more")

    if not args.dry_run and not args.validate_only:
        logger.info(f"Output directory: {OUTPUT_DIR if not args.in_place else ENRICHED_DIR}")

    logger.info("=" * 50)


if __name__ == "__main__":
    main()
