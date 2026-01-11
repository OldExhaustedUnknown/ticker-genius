"""
Phase 1: 데이터 정직화
=====================
추론으로 채운 필드들을 NOT_SEARCHED로 되돌리고,
레거시 데이터는 source에 'legacy_unverified' 표시.

원칙: 추론 금지. 데이터가 없으면 없다고 기록.
"""
import json
import os
from datetime import datetime

enriched_dir = 'data/enriched'
files = [f for f in os.listdir(enriched_dir) if f.endswith('.json')]

# 추론으로 채워진 source 패턴
INFERRED_SOURCES = [
    'inferred_from_approval',
    'inferred_non_manufacturing_crl',
    'derived_from_approval_type',
    'derived_from_indication',
    'approval_type_anda_dmg',
    'no_prior_crl_in_dataset',
    'this_is_first_crl',
    'computed_from_dataset',
    'brand_to_generic_map',
    'drug_name_is_generic',
    'extracted_from_drug_name',
    'final_mapping',
    'comprehensive_mapping',
    'pending_or_withdrawn',
    'known_manufacturing_crl',
    'known_safety_crl',
    'crl_reason_undetermined',
    'crl_manufacturing_status_undetermined',
    'medical_device',
]

# 레거시 데이터 source (검증 필요)
LEGACY_SOURCES = [
    'legacy_v12',
    'migrated',
]

# 필드별 처리 방식
FIELD_ACTIONS = {
    # 추론 필드 -> NOT_SEARCHED로 리셋
    'phase': 'reset_if_inferred',
    'safety_signal': 'reset_if_inferred',
    'pai_passed': 'reset_if_inferred',
    'warning_letter': 'reset_if_inferred',
    'has_prior_crl': 'reset_if_inferred',
    'therapeutic_area': 'reset_if_inferred',
    'generic_name': 'reset_if_inferred',

    # 레거시 필드 -> UNVERIFIED 태그
    'btd': 'tag_legacy',
    'priority_review': 'tag_legacy',
    'fast_track': 'tag_legacy',
    'orphan_drug': 'tag_legacy',
    'accelerated_approval': 'tag_legacy',

    # 실제 수집된 필드 -> 유지
    'primary_endpoint_met': 'keep',
    'p_value': 'keep',
    'effect_size': 'keep',
    'adcom_held': 'keep',
    'approval_type': 'keep',
    'indication': 'keep',
    'is_resubmission': 'keep',
}

stats = {
    'reset_count': 0,
    'tagged_count': 0,
    'kept_count': 0,
    'files_modified': 0,
}

now = datetime.now().isoformat()

for filename in files:
    filepath = os.path.join(enriched_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        event = json.load(f)

    modified = False

    for field, action in FIELD_ACTIONS.items():
        if field not in event:
            continue

        field_data = event[field]
        if not isinstance(field_data, dict):
            continue

        source = field_data.get('source', '')
        status = field_data.get('status', '')

        if action == 'reset_if_inferred':
            # 추론 source이면 리셋
            if source in INFERRED_SOURCES or 'inferred' in str(source).lower() or 'derived' in str(source).lower():
                event[field] = {
                    'status': 'not_searched',
                    'value': None,
                    'source': None,
                    'confidence': 0.0,
                    'evidence': [],
                    'searched_sources': [],
                    'last_searched': None,
                    'error': None,
                    '_reset_reason': f'Was inferred from: {source}',
                    '_reset_at': now,
                }
                stats['reset_count'] += 1
                modified = True

        elif action == 'tag_legacy':
            # 레거시 source이면 태그 추가
            if source in LEGACY_SOURCES or 'legacy' in str(source).lower():
                if 'needs_verification' not in field_data:
                    field_data['needs_verification'] = True
                    field_data['verification_tier'] = 'tier1_fda'
                    field_data['_legacy_source'] = source
                    stats['tagged_count'] += 1
                    modified = True

        elif action == 'keep':
            stats['kept_count'] += 1

    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(event, f, indent=2, ensure_ascii=False)
        stats['files_modified'] += 1

print("=" * 60)
print("Phase 1: 데이터 정직화 완료")
print("=" * 60)
print(f"리셋된 추론 필드: {stats['reset_count']}")
print(f"검증 필요 태그된 레거시 필드: {stats['tagged_count']}")
print(f"유지된 실제 수집 필드: {stats['kept_count']}")
print(f"수정된 파일: {stats['files_modified']}")
print("=" * 60)
