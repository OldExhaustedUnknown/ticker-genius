"""
NCT ID 수집 - WebSearch 기반 (Task Agent 사용)

배치로 약물 목록을 준비하고 병렬 Task로 수집
"""
import json
import re
from pathlib import Path


def extract_nct_ids(text: str) -> list[str]:
    """텍스트에서 NCT ID 추출"""
    pattern = r'NCT\d{8}'
    matches = re.findall(pattern, text, re.IGNORECASE)
    return list(set([m.upper() for m in matches]))


def prepare_batches():
    """배치 준비 - FDA 지정이 있는 약물 우선"""
    data_dir = Path("data/enriched")

    # 우선순위 분류
    high_priority = []  # FDA 지정 있음
    medium_priority = []  # 지정 없음

    for fpath in data_dir.glob("*.json"):
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)

            if len(data.get("nct_ids", [])) > 0:
                continue  # 이미 있음

            # FDA 지정 확인
            designations = data.get("fda_designations", {})
            has_designation = any([
                designations.get("breakthrough_therapy"),
                designations.get("fast_track"),
                designations.get("priority_review"),
                designations.get("orphan_drug"),
                designations.get("accelerated_approval"),
            ])

            drug_info = {
                "event_id": data.get("event_id"),
                "ticker": data.get("ticker"),
                "drug": data.get("drug_name"),
                "indication": "",
                "file_path": str(fpath),
            }

            # indication 추출
            indication = data.get("indication", {})
            if isinstance(indication, dict):
                drug_info["indication"] = indication.get("value", "")[:100]
            elif isinstance(indication, str):
                drug_info["indication"] = indication[:100]

            if has_designation:
                high_priority.append(drug_info)
            else:
                medium_priority.append(drug_info)

    print(f"High priority (with FDA designation): {len(high_priority)}")
    print(f"Medium priority (no designation): {len(medium_priority)}")

    # 배치 생성 (10개씩)
    all_drugs = high_priority + medium_priority
    batch_size = 10
    batches = [all_drugs[i:i+batch_size] for i in range(0, len(all_drugs), batch_size)]

    # 처음 5개 배치 저장
    for i, batch in enumerate(batches[:5]):
        output_path = Path(f"data/nct_websearch_batch_{i+1}.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(batch, f, indent=2, ensure_ascii=False)
        print(f"Batch {i+1}: {len(batch)} drugs -> {output_path}")

    return batches


def apply_nct_results(batch_num: int, results: list):
    """결과를 enriched 데이터에 적용"""
    for result in results:
        event_id = result.get("event_id")
        nct_ids = result.get("nct_ids", [])

        if not nct_ids:
            continue

        file_path = result.get("file_path")
        if not file_path or not Path(file_path).exists():
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        data["nct_ids"] = nct_ids

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"Updated {result.get('ticker')}/{result.get('drug')}: {nct_ids}")


if __name__ == "__main__":
    batches = prepare_batches()
    print(f"\nTotal batches: {len(batches)}")
