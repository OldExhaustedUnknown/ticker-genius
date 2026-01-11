"""
NCT ID 수집 스크립트 - ClinicalTrials.gov API 사용
"""
import json
import os
import sys
import time
import httpx
from pathlib import Path

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def search_clinicaltrials(drug_name: str, indication: str = "") -> list[str]:
    """ClinicalTrials.gov API로 NCT ID 검색"""
    base_url = "https://clinicaltrials.gov/api/v2/studies"

    # 약물명 정제 - 여러 변형 시도
    original = drug_name
    clean_drug = drug_name.split("/")[0].split("(")[0].strip()

    # 특수문자 제거
    for char in ["-", "‐", "–", "—", "_"]:
        clean_drug = clean_drug.replace(char, " ")

    clean_drug = clean_drug.strip()

    # 검색 쿼리 후보들
    queries = []

    # 1. 약물명 + indication
    if indication:
        clean_indication = indication.split("(")[0].strip()[:50]
        queries.append(f"{clean_drug} {clean_indication}")

    # 2. 약물명만
    queries.append(clean_drug)

    # 3. 약물명 (소문자)
    queries.append(clean_drug.lower())

    # 4. 원본 이름
    if original != clean_drug:
        queries.append(original)

    nct_ids = set()

    for query in queries:
        try:
            params = {
                "query.term": query,
                "pageSize": 50,
            }

            with httpx.Client(timeout=30) as client:
                resp = client.get(base_url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    studies = data.get("studies", [])

                    for study in studies:
                        protocol = study.get("protocolSection", {})
                        id_module = protocol.get("identificationModule", {})
                        nct_id = id_module.get("nctId", "")

                        # Phase 확인
                        design = protocol.get("designModule", {})
                        phases = design.get("phases", [])

                        # Phase 2 또는 3 포함
                        is_late_phase = any(p in phases for p in ["PHASE2", "PHASE3", "PHASE2/PHASE3"])

                        if nct_id and nct_id.startswith("NCT"):
                            # Phase 필터 적용
                            if is_late_phase or not phases:
                                nct_ids.add(nct_id)

                    if nct_ids:
                        break  # 찾으면 중단

        except Exception as e:
            continue

        time.sleep(0.2)  # Rate limiting

    return list(nct_ids)[:5]  # 최대 5개


def main():
    data_dir = Path("data/enriched")

    # NCT ID 없는 파일 수집
    files_to_update = []
    for fpath in data_dir.glob("*.json"):
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if len(data.get("nct_ids", [])) == 0:
                files_to_update.append((fpath, data))

    print(f"Total files to update: {len(files_to_update)}")

    # 진행 상황 파일
    progress_file = Path("data/nct_collection_progress.json")
    if progress_file.exists():
        with open(progress_file, 'r', encoding='utf-8') as f:
            progress = json.load(f)
    else:
        progress = {"completed": [], "found": 0, "not_found": 0}

    completed_ids = set(progress["completed"])

    for idx, (fpath, data) in enumerate(files_to_update):
        event_id = data.get("event_id", "")

        if event_id in completed_ids:
            continue

        drug_name = data.get("drug_name", "")
        ticker = data.get("ticker", "")

        indication_data = data.get("indication", {})
        indication = ""
        if isinstance(indication_data, dict):
            indication = indication_data.get("value", "")
        elif isinstance(indication_data, str):
            indication = indication_data

        # ASCII 안전 출력
        safe_drug = drug_name.encode('ascii', 'replace').decode('ascii')
        print(f"[{idx+1}/{len(files_to_update)}] {ticker} - {safe_drug}")

        nct_ids = search_clinicaltrials(drug_name, indication)

        if nct_ids:
            data["nct_ids"] = nct_ids
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"  Found: {nct_ids}")
            progress["found"] += 1
        else:
            print(f"  Not found")
            progress["not_found"] += 1

        progress["completed"].append(event_id)

        # 진행 상황 저장 (10개마다)
        if (idx + 1) % 10 == 0:
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress, f, indent=2)
            print(f"  Progress: {progress['found']} found, {progress['not_found']} not found")

    # 최종 저장
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2)

    print(f"\nComplete! Found: {progress['found']}, Not found: {progress['not_found']}")


if __name__ == "__main__":
    main()
