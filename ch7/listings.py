"""The Chapter 7 listings, exactly as printed, in chapter order.

    python -m ch7.listings

Reusable versions (reading data/horizon_one_tower/carbon) are in ch7/carbon.py.
"""

# --- Code example 1 ---
import math
import pandas as pd

# Illustrative data for demonstrating the workflow.
quantities = pd.DataFrame([
    ('A', 'panels', 10000, 'kg', 'F-ACP', 'DEMO-Q-A-r1'),
    ('A', 'supports', 2000, 'kg', 'F-SUP', 'DEMO-Q-A-r1'),
    ('B', 'panels', 30000, 'kg', 'F-TER', 'DEMO-Q-B-r1'),
    ('B', 'supports', 2600, 'kg', 'F-SUP', 'DEMO-Q-B-r1'),
], columns=['option', 'component', 'quantity', 'unit',
            'factor_id', 'quantity_ref'])

factors = pd.DataFrame([
    ('F-ACP', 'panels', 4.0, 'kgCO2e/kg', 'A1-A3', 'GWP-total',
     'DEMO-F-01-r1'),
    ('F-TER', 'panels', 1.1, 'kgCO2e/kg', 'A1-A3', 'GWP-total',
     'DEMO-F-02-r1'),
    ('F-SUP', 'supports', 5.0, 'kgCO2e/kg', 'A1-A3', 'GWP-total',
     'DEMO-F-03-r1'),
], columns=['factor_id', 'component', 'factor', 'factor_unit',
            'scope', 'indicator', 'factor_ref'])


def calculate_carbon(q: pd.DataFrame,
                     f: pd.DataFrame) -> pd.DataFrame:
    if q.empty or q.duplicated(['option', 'component']).any():
        raise ValueError(
            'Provide unique, non-empty component records.')

    rows = q.merge(f, on=['factor_id', 'component'], how='left',
                   validate='many_to_one')

    for column in ['quantity', 'factor']:
        rows[column] = pd.to_numeric(rows[column],
                                     errors='coerce')

    checks = {
        'invalid quantity': rows['quantity'].map(
            lambda x: pd.notna(x) and math.isfinite(x)
            and x >= 0),
        'missing/invalid factor': rows['factor'].map(
            lambda x: pd.notna(x) and math.isfinite(x)),
        'unit mismatch': rows['unit'].eq('kg')
                         & rows['factor_unit'].eq('kgCO2e/kg'),
        'scope mismatch': rows['scope'].eq('A1-A3'),
        'indicator mismatch': rows['indicator'].eq('GWP-total'),
        'missing quantity reference':
            rows['quantity_ref'].fillna('').str.strip().ne(''),
        'missing factor reference':
            rows['factor_ref'].fillna('').str.strip().ne(''),
    }

    rows['issues'] = [
        '; '.join(name for name, passed in checks.items()
                  if not passed.fillna(False).iloc[i])
        for i in range(len(rows))
    ]

    carbon = rows['quantity'] * rows['factor']
    rows['carbon_kgCO2e'] = carbon.where(rows['issues'].eq(''))
    return rows


rows = calculate_carbon(quantities, factors)
print(rows[['option', 'component', 'carbon_kgCO2e', 'issues']])


# --- Code example 2 ---
# Both options serve the same illustrative 1,000 m2 podium area.
options = pd.DataFrame([
    ('A', 200000, 10, 'assumed', 'pending', 'DEMO-COM-A-r1'),
    ('B', 212000, 16, 'unconfirmed', 'pending', 'DEMO-COM-B-r1'),
], columns=['option', 'cost_GBP', 'lead_weeks', 'availability',
            'technical_review', 'commercial_ref'])


def compare_options(rows: pd.DataFrame) -> pd.DataFrame:
    groups = rows.groupby('option')
    totals = groups['carbon_kgCO2e'].agg(
        lambda values: values.sum(min_count=len(values)))
    coverage = groups['component'].agg(
        lambda values: set(values) == {'panels', 'supports'})
    result = options.merge(
        totals.where(coverage).rename('carbon_kgCO2e'),
        on='option', how='left', validate='one_to_one')
    baseline = result.set_index('option').at['A', 'carbon_kgCO2e']
    result['change_pct'] = (
        100 * (result['carbon_kgCO2e'] / baseline - 1)
        if pd.notna(baseline) and baseline > 0 else float('nan'))
    complete = result['carbon_kgCO2e'].notna()
    result['calculation_status'] = complete.map(
        {True: 'screening_only', False: 'needs_evidence'})
    return result


comparison = compare_options(rows)
print(comparison.to_string(index=False))

# Removing one factor must prevent a complete total for Option B.
missing = factors[factors['factor_id'] != 'F-TER']
incomplete = compare_options(
    calculate_carbon(quantities, missing))
assert pd.isna(
    incomplete.set_index('option').at['B', 'carbon_kgCO2e'])


# --- Code example 3 ---
import json
from datetime import datetime, timezone
from uuid import uuid4

calculation_complete = comparison['carbon_kgCO2e'].notna().all()

review_record = {
    'record_id': str(uuid4()),
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'project': 'Horizon One Tower',
    'change_id': 'DEMO-HOT-POD-01',
    'calculation_version': 'chapter7-demo-v2',
    'area_m2': 1000,
    'scope': 'A1-A3: panels and supports only',
    'evidence_quality':
        'illustrative teaching data; unverified for project use',
    'assumptions': ['Same screened area; common layers excluded'],
    'exclusions': [
        'Other facade components; transport to site; '
        'installation',
        'maintenance; replacement; operational energy; '
        'end-of-life',
    ],
    'line_items': json.loads(rows.to_json(orient='records')),
    'options': json.loads(comparison.to_json(orient='records')),
    'calculation_status': (
        'complete_for_screening' if calculation_complete
        else 'incomplete'),
    'evidence_status': 'illustrative_unverified',
    'review_status': 'pending_multidisciplinary_review',
    'approval_status': 'not_approved',
    'reviewer_role': 'Sustainability consultant',
    'reviewer': None,
    'required_follow_up': [
        'Verify quantities, factors and full assembly scope',
        'Obtain supplier evidence and confirm availability',
        'Complete technical, energy, planning and '
        'commercial reviews',
    ],
}

print(json.dumps(review_record, indent=2, allow_nan=False))
