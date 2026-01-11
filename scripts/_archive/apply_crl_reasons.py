"""CRL 사유 및 PAI/Safety 정보 적용"""
import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# CRL 사유 데이터 (검색 결과 기반)
CRL_DATA = {
    # Batch 1
    'ADX-2191': {
        'reason': 'CLINICAL_DATA',
        'detail': 'Lack of adequate and well-controlled investigations (literature-based NDA)',
        'pai_issue': False,
        'safety_issue': False,
    },
    'AVT05': {
        'reason': 'CMC_ISSUE',
        'detail': 'Manufacturing facility inspection deficiencies at Reykjavik',
        'pai_issue': True,
        'safety_issue': False,
    },
    'OLEOGEL': {
        'reason': 'CLINICAL_DATA',
        'detail': 'Additional confirmatory evidence of effectiveness required',
        'pai_issue': False,
        'safety_issue': False,
    },
    'GOVORESTAT': {
        'reason': 'CLINICAL_DATA',
        'detail': 'Primary endpoint not statistically significant (P=0.1030)',
        'pai_issue': False,
        'safety_issue': False,
    },
    'VYGLXIA': {
        'reason': 'CLINICAL_DATA',
        'detail': 'Real-world evidence/external control study design issues',
        'pai_issue': False,
        'safety_issue': False,
    },
    'TRORILUZOLE': {
        'reason': 'CLINICAL_DATA',
        'detail': 'Real-world evidence/external control study design issues',
        'pai_issue': False,
        'safety_issue': False,
    },
    'AVAPRITINIB': {
        'reason': 'CLINICAL_DATA',
        'detail': 'Phase III VOYAGER trial failed to meet primary endpoint (PFS)',
        'pai_issue': False,
        'safety_issue': False,
    },
    'PLINABULIN': {
        'reason': 'CLINICAL_DATA',
        'detail': 'Single trial insufficient, second confirmatory trial required',
        'pai_issue': False,
        'safety_issue': False,
    },
    'DERAMIOCEL': {
        'reason': 'CLINICAL_DATA',
        'detail': 'Insufficient evidence of effectiveness + CMC items',
        'pai_issue': True,
        'safety_issue': False,
    },
    'CAP-1002': {
        'reason': 'CLINICAL_DATA',
        'detail': 'Insufficient evidence of effectiveness + CMC items',
        'pai_issue': True,
        'safety_issue': False,
    },
    'RELACORILANT': {
        'reason': 'CLINICAL_DATA',
        'detail': 'Additional evidence needed despite trials meeting endpoints',
        'pai_issue': False,
        'safety_issue': False,
    },
    # Batch 2
    'OMECAMTIV': {
        'reason': 'CLINICAL_DATA',
        'detail': 'Single trial insufficient, small effect, no mortality benefit',
        'pai_issue': False,
        'safety_issue': False,
    },
    'ROLUPERIDONE': {
        'reason': 'CLINICAL_DATA',
        'detail': 'Single study insufficient, no concomitant antipsychotic data',
        'pai_issue': False,
        'safety_issue': False,
    },
    'SOMATROGON': {
        'reason': 'OTHER',
        'detail': 'Reasons not publicly disclosed',
        'pai_issue': None,
        'safety_issue': None,
    },
    'ONS-5010': {
        'reason': 'CLINICAL_DATA',
        'detail': 'Failed primary endpoint, CMC issues from PAI',
        'pai_issue': True,
        'safety_issue': False,
    },
    'LYTENAVA': {
        'reason': 'CLINICAL_DATA',
        'detail': 'Failed primary endpoint, CMC issues from PAI',
        'pai_issue': True,
        'safety_issue': False,
    },
    'UX111': {
        'reason': 'CMC_ISSUE',
        'detail': 'Manufacturing facility observations, process concerns',
        'pai_issue': True,
        'safety_issue': False,
    },
    'MARNETEGRAGENE': {
        'reason': 'CMC_ISSUE',
        'detail': 'Additional CMC information needed',
        'pai_issue': False,
        'safety_issue': False,
    },
    # Batch 3
    'BARDOXOLONE': {
        'reason': 'CLINICAL_DATA',
        'detail': 'ADCOM voted 13-0 against, efficacy concerns',
        'pai_issue': False,
        'safety_issue': False,
    },
    'VICINEUM': {
        'reason': 'CMC_ISSUE',
        'detail': 'CMC issues from PAI + clinical data concerns',
        'pai_issue': True,
        'safety_issue': False,
    },
    'POZIOTINIB': {
        'reason': 'CLINICAL_DATA',
        'detail': 'ODAC voted 9-4 against, high adverse event rates (97.8%)',
        'pai_issue': False,
        'safety_issue': True,
    },
    'APITEGROMAB': {
        'reason': 'CMC_ISSUE',
        'detail': 'Third-party fill-finish facility (Catalent) inspection issues',
        'pai_issue': True,
        'safety_issue': False,
    },
    'SRK-015': {
        'reason': 'CMC_ISSUE',
        'detail': 'Third-party fill-finish facility (Catalent) inspection issues',
        'pai_issue': True,
        'safety_issue': False,
    },
    'VEVERIMER': {
        'reason': 'CLINICAL_DATA',
        'detail': 'Insufficient treatment effect on surrogate marker',
        'pai_issue': False,
        'safety_issue': False,
    },
    'OXYLANTHANUM': {
        'reason': 'CMC_ISSUE',
        'detail': 'Third-party manufacturing vendor inspection deficiencies',
        'pai_issue': True,
        'safety_issue': False,
    },
    'OLC': {
        'reason': 'CMC_ISSUE',
        'detail': 'Third-party manufacturing vendor inspection deficiencies',
        'pai_issue': True,
        'safety_issue': False,
    },
    'OMBURTAMAB': {
        'reason': 'CLINICAL_DATA',
        'detail': 'ODAC voted 16-0, external control inadequate',
        'pai_issue': False,
        'safety_issue': False,
    },
    'DASIGLUCAGON': {
        'reason': 'CMC_ISSUE',
        'detail': 'Third-party contract manufacturing facility inspection issues',
        'pai_issue': True,
        'safety_issue': False,
    },
}

# Withdrawn 케이스
WITHDRAWN_DATA = {
    'AMX0035': {
        'reason': 'CLINICAL_DATA',
        'detail': 'Confirmatory PHOENIX trial failed, voluntarily withdrawn',
        'pai_issue': False,
        'safety_issue': False,
    },
    'RELYVRIO': {
        'reason': 'CLINICAL_DATA',
        'detail': 'Confirmatory PHOENIX trial failed, voluntarily withdrawn',
        'pai_issue': False,
        'safety_issue': False,
    },
    'PATRITUMAB': {
        'reason': 'OTHER',
        'detail': 'Withdrawn by sponsor',
        'pai_issue': None,
        'safety_issue': None,
    },
    'HER3-DXD': {
        'reason': 'OTHER',
        'detail': 'Withdrawn by sponsor',
        'pai_issue': None,
        'safety_issue': None,
    },
}

data_dir = Path('data/enriched')
updated = 0

for fpath in data_dir.glob('*.json'):
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    result = data.get('result', '')
    if result not in ['crl', 'withdrawn']:
        continue

    drug = data.get('drug_name', '').upper()
    ticker = data.get('ticker', '')
    modified = False

    # Find matching CRL/Withdrawn data
    matched = None
    source_data = CRL_DATA if result == 'crl' else WITHDRAWN_DATA

    for key, info in source_data.items():
        if key.upper() in drug:
            matched = info
            break

    if matched:
        # Update prior_crl_reason
        data['prior_crl_reason'] = {
            'status': 'found',
            'value': matched['detail'],
            'source': 'web_search',
            'category': matched['reason'],
            'confidence': 0.90,
            'tier': 2
        }

        # Update pai_passed
        if matched['pai_issue'] is not None:
            data['pai_passed'] = {
                'status': 'found',
                'value': not matched['pai_issue'],  # PAI issue means PAI failed
                'source': 'derived_from_crl_reason',
                'confidence': 0.85,
                'tier': 2
            }

        # Update safety_signal
        if matched['safety_issue'] is not None:
            data['safety_signal'] = {
                'status': 'found',
                'value': matched['safety_issue'],
                'source': 'derived_from_crl_reason',
                'confidence': 0.85,
                'tier': 2
            }

        # Update warning_letter (no warning letter issues found in CRL reasons)
        if matched.get('pai_issue') is not None:
            data['warning_letter'] = {
                'status': 'found',
                'value': False,  # CRL reasons don't mention warning letters
                'source': 'derived_from_crl_reason',
                'confidence': 0.75,
                'tier': 2
            }

        print(f'{ticker}: {drug[:30]} -> {matched["reason"]} | PAI:{not matched["pai_issue"] if matched["pai_issue"] is not None else "?"}')
        modified = True

    if modified:
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        updated += 1

print(f'\n=== 결과 ===')
print(f'CRL/Withdrawn 사유 적용: {updated}건')
