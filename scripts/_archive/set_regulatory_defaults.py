"""Set default values for regulatory fields based on approval outcome."""
import json
import os
from datetime import datetime

enriched_dir = 'data/enriched'
files = [f for f in os.listdir(enriched_dir) if f.endswith('.json')]

# Known CRL reasons (from historical data)
# Safety-related CRLs
SAFETY_CRL_TICKERS = {
    'FGEN': 'Roxadustat - cardiovascular safety concerns',
    'GILD': 'Filgotinib - testicular toxicity concerns',
    'CYTK': 'Omecamtiv Mecarbil - efficacy/safety balance',
    'TCDA': 'Veverimer - manufacturing + efficacy concerns',
    'BYSI': 'Plinabulin - efficacy concerns',
    'HCM': 'Surufatinib - clinical data concerns',
    'RETA': 'Bardoxolone - cardiovascular safety (BEACON trial)',
    'NERV': 'Roluperidone - efficacy concerns',
    'SRRK': 'Apitegromab - efficacy concerns',
    'ICPT': 'OCA/Ocaliva - liver safety concerns',
}

# Manufacturing-related CRLs
MANUFACTURING_CRL_TICKERS = {
    'OPK': 'Somatrogon - manufacturing issues',
    'EGRX': 'Bivalirudin - manufacturing issues',
    'CAPR': 'Deramiocel - manufacturing issues',
    'RARE': 'ABO-102 - manufacturing/CMC issues',
    'YMAB': 'Omburtamab - manufacturing issues',
    'SESN': 'Vicineum - manufacturing/CMC issues',
    'OTLK': 'ONS-5010 - manufacturing issues',
    'CORT': 'Relacorilant - efficacy concerns',
    'INCY': 'QD Ruxolitinib - formulation issues',
}

updated = 0
for filename in files:
    filepath = os.path.join(enriched_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        event = json.load(f)

    modified = False
    now = datetime.now().isoformat()
    result = event.get('result', '').lower()
    ticker = event.get('ticker', '')

    # 1. safety_signal
    if event.get('safety_signal', {}).get('status') == 'not_searched':
        if result == 'approved':
            # Most approved drugs don't have significant safety signals
            # (otherwise they wouldn't be approved)
            event['safety_signal'] = {
                'status': 'found',
                'value': False,
                'source': 'inferred_from_approval',
                'confidence': 0.85,
                'evidence': ['FDA approval indicates acceptable safety profile'],
                'searched_sources': ['inferred'],
                'last_searched': now,
                'error': None
            }
            modified = True
        elif result == 'crl':
            # Check if this CRL was due to safety
            if ticker in SAFETY_CRL_TICKERS:
                event['safety_signal'] = {
                    'status': 'found',
                    'value': True,
                    'source': 'known_safety_crl',
                    'confidence': 0.9,
                    'evidence': [SAFETY_CRL_TICKERS[ticker]],
                    'searched_sources': ['historical_data'],
                    'last_searched': now,
                    'error': None
                }
                modified = True
            elif ticker in MANUFACTURING_CRL_TICKERS:
                event['safety_signal'] = {
                    'status': 'found',
                    'value': False,
                    'source': 'known_manufacturing_crl',
                    'confidence': 0.85,
                    'evidence': [f'{MANUFACTURING_CRL_TICKERS[ticker]} - not safety related'],
                    'searched_sources': ['historical_data'],
                    'last_searched': now,
                    'error': None
                }
                modified = True
            else:
                # Unknown CRL reason - mark as not_found for manual review
                event['safety_signal'] = {
                    'status': 'not_found',
                    'value': None,
                    'source': None,
                    'confidence': 0.0,
                    'evidence': ['CRL reason unknown - needs manual review'],
                    'searched_sources': ['inferred'],
                    'last_searched': now,
                    'error': None
                }
                modified = True
        elif result in ('pending', 'withdrawn'):
            event['safety_signal'] = {
                'status': 'not_applicable',
                'value': None,
                'source': 'pending_or_withdrawn',
                'confidence': 1.0,
                'evidence': [f'Result is {result} - safety signal not yet determined'],
                'searched_sources': ['inferred'],
                'last_searched': now,
                'error': None
            }
            modified = True

    # 2. pai_passed (Pre-Approval Inspection)
    if event.get('pai_passed', {}).get('status') == 'not_searched':
        if result == 'approved':
            # Approved drugs must have passed PAI
            event['pai_passed'] = {
                'status': 'found',
                'value': True,
                'source': 'inferred_from_approval',
                'confidence': 0.95,
                'evidence': ['FDA approval requires successful PAI'],
                'searched_sources': ['inferred'],
                'last_searched': now,
                'error': None
            }
            modified = True
        elif result == 'crl':
            # Check if CRL was manufacturing-related
            if ticker in MANUFACTURING_CRL_TICKERS:
                event['pai_passed'] = {
                    'status': 'found',
                    'value': False,
                    'source': 'known_manufacturing_crl',
                    'confidence': 0.9,
                    'evidence': [MANUFACTURING_CRL_TICKERS[ticker]],
                    'searched_sources': ['historical_data'],
                    'last_searched': now,
                    'error': None
                }
                modified = True
            else:
                # Non-manufacturing CRL - PAI likely passed
                event['pai_passed'] = {
                    'status': 'found',
                    'value': True,
                    'source': 'inferred_non_manufacturing_crl',
                    'confidence': 0.7,
                    'evidence': ['CRL not manufacturing-related - PAI likely passed'],
                    'searched_sources': ['inferred'],
                    'last_searched': now,
                    'error': None
                }
                modified = True
        elif result in ('pending', 'withdrawn'):
            event['pai_passed'] = {
                'status': 'not_applicable',
                'value': None,
                'source': 'pending_or_withdrawn',
                'confidence': 1.0,
                'evidence': [f'Result is {result} - PAI status not yet determined'],
                'searched_sources': ['inferred'],
                'last_searched': now,
                'error': None
            }
            modified = True

    # 3. warning_letter
    if event.get('warning_letter', {}).get('status') == 'not_searched':
        if result == 'approved':
            # Most approved drugs don't have active warning letters
            # Warning letters would typically delay approval
            event['warning_letter'] = {
                'status': 'found',
                'value': False,
                'source': 'inferred_from_approval',
                'confidence': 0.85,
                'evidence': ['FDA approval suggests no active warning letters for this product'],
                'searched_sources': ['inferred'],
                'last_searched': now,
                'error': None
            }
            modified = True
        elif result == 'crl':
            if ticker in MANUFACTURING_CRL_TICKERS:
                # Manufacturing CRLs might have warning letters
                event['warning_letter'] = {
                    'status': 'not_found',
                    'value': None,
                    'source': None,
                    'confidence': 0.0,
                    'evidence': ['Manufacturing CRL - warning letter status unknown'],
                    'searched_sources': ['inferred'],
                    'last_searched': now,
                    'error': None
                }
                modified = True
            else:
                event['warning_letter'] = {
                    'status': 'found',
                    'value': False,
                    'source': 'inferred_non_manufacturing_crl',
                    'confidence': 0.75,
                    'evidence': ['Non-manufacturing CRL - warning letter unlikely'],
                    'searched_sources': ['inferred'],
                    'last_searched': now,
                    'error': None
                }
                modified = True
        elif result in ('pending', 'withdrawn'):
            event['warning_letter'] = {
                'status': 'not_applicable',
                'value': None,
                'source': 'pending_or_withdrawn',
                'confidence': 1.0,
                'evidence': [f'Result is {result}'],
                'searched_sources': ['inferred'],
                'last_searched': now,
                'error': None
            }
            modified = True

    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(event, f, indent=2, ensure_ascii=False)
        updated += 1

print(f'Updated {updated} files with regulatory defaults')
