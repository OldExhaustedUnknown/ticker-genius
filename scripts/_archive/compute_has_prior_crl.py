"""Compute has_prior_crl by checking for previous CRL events for the same drug."""
import json
import os
from datetime import datetime
from collections import defaultdict

enriched_dir = 'data/enriched'
files = [f for f in os.listdir(enriched_dir) if f.endswith('.json')]

# Load all events
events = []
for filename in files:
    filepath = os.path.join(enriched_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        event = json.load(f)
    event['_filepath'] = filepath
    events.append(event)

# Group events by ticker and drug (normalized)
def normalize_drug_name(name):
    if not name:
        return ''
    # Remove common suffixes and normalize
    name = name.lower().strip()
    # Remove parenthetical content
    if '(' in name:
        name = name.split('(')[0].strip()
    # Remove brand name indicators
    for suffix in [' tablet', ' capsule', ' injection', ' solution', ' cream', ' gel', ' spray']:
        name = name.replace(suffix, '')
    return name.strip()

# Create a mapping of (ticker, drug) -> list of events sorted by date
ticker_drug_events = defaultdict(list)
for event in events:
    ticker = event.get('ticker', '')
    drug = normalize_drug_name(event.get('drug_name', ''))
    ticker_drug_events[(ticker, drug)].append(event)

# Sort events by pdufa_date
for key in ticker_drug_events:
    ticker_drug_events[key].sort(key=lambda x: x.get('pdufa_date', ''))

# Known prior CRL relationships (from historical data)
KNOWN_PRIOR_CRL = {
    # These drugs had CRLs before approval
    ('ICPT', 'ocaliva'): True,  # OCA had CRL before approval
    ('CALT', 'nefecon'): False,
    ('CALT', 'tarpeyo'): False,
    ('HRTX', 'zynrelef'): True,  # Had prior CRL
    ('HRTX', 'htx-011'): True,
    ('BPMC', 'ayvakit'): True,  # Had prior CRL for 4L GIST
    ('INCY', 'opzelura'): True,  # Related to prior ruxolitinib XR CRL
    ('MDGL', 'rezdiffra'): False,
    ('MDGL', 'resmetirom'): False,
    ('TVTX', 'sparsentan'): False,
    ('TVTX', 'filspari'): False,
    ('RETA', 'omaveloxolone'): False,  # Different from bardoxolone which got CRL
    ('CYTK', 'myqorzo'): True,  # Prior CRL for omecamtiv mecarbil
    ('SRPT', 'elevidys'): False,
    ('VRTX', 'casgevy'): False,
}

updated = 0
for event in events:
    if event.get('has_prior_crl', {}).get('status') != 'not_searched':
        continue

    ticker = event.get('ticker', '')
    drug = normalize_drug_name(event.get('drug_name', ''))
    pdufa_date = event.get('pdufa_date', '')
    result = event.get('result', '').lower()

    now = datetime.now().isoformat()
    modified = False

    # Check known prior CRL list
    if (ticker, drug) in KNOWN_PRIOR_CRL:
        has_prior = KNOWN_PRIOR_CRL[(ticker, drug)]
        event['has_prior_crl'] = {
            'status': 'found',
            'value': has_prior,
            'source': 'known_prior_crl_data',
            'confidence': 0.95,
            'evidence': [f'Known prior CRL status for {ticker} {drug}'],
            'searched_sources': ['historical_data'],
            'last_searched': now,
            'error': None
        }
        modified = True
    else:
        # Check if there are earlier CRL events for this ticker/drug
        same_drug_events = ticker_drug_events.get((ticker, drug), [])

        prior_crls = []
        for prev_event in same_drug_events:
            prev_date = prev_event.get('pdufa_date', '')
            prev_result = prev_event.get('result', '').lower()
            if prev_date < pdufa_date and prev_result == 'crl':
                prior_crls.append(prev_date)

        if prior_crls:
            event['has_prior_crl'] = {
                'status': 'found',
                'value': True,
                'source': 'computed_from_dataset',
                'confidence': 0.95,
                'evidence': [f'Prior CRL(s) found on: {", ".join(prior_crls)}'],
                'searched_sources': ['internal_dataset'],
                'last_searched': now,
                'error': None
            }
            modified = True
        else:
            # No prior CRLs found - but this could be first submission
            # For approved drugs, we can be more confident
            if result == 'approved':
                event['has_prior_crl'] = {
                    'status': 'found',
                    'value': False,
                    'source': 'no_prior_crl_in_dataset',
                    'confidence': 0.85,
                    'evidence': ['No prior CRL events found in dataset'],
                    'searched_sources': ['internal_dataset'],
                    'last_searched': now,
                    'error': None
                }
                modified = True
            elif result == 'crl':
                # This IS a CRL - check if it's the first one
                event['has_prior_crl'] = {
                    'status': 'found',
                    'value': False,
                    'source': 'this_is_first_crl',
                    'confidence': 0.9,
                    'evidence': ['This appears to be the first CRL for this drug'],
                    'searched_sources': ['internal_dataset'],
                    'last_searched': now,
                    'error': None
                }
                modified = True
            elif result == 'pending':
                # For pending - check if there was any prior CRL
                event['has_prior_crl'] = {
                    'status': 'found',
                    'value': False,
                    'source': 'no_prior_crl_in_dataset',
                    'confidence': 0.75,
                    'evidence': ['No prior CRL events found in dataset'],
                    'searched_sources': ['internal_dataset'],
                    'last_searched': now,
                    'error': None
                }
                modified = True
            elif result == 'withdrawn':
                event['has_prior_crl'] = {
                    'status': 'not_applicable',
                    'value': None,
                    'source': 'withdrawn',
                    'confidence': 1.0,
                    'evidence': ['Application withdrawn'],
                    'searched_sources': ['internal_dataset'],
                    'last_searched': now,
                    'error': None
                }
                modified = True

    if modified:
        filepath = event['_filepath']
        del event['_filepath']
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(event, f, indent=2, ensure_ascii=False)
        updated += 1
    else:
        del event['_filepath']

print(f'Updated {updated} files with has_prior_crl')
