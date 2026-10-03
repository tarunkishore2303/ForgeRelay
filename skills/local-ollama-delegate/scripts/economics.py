"""Conditional estimates and entered measurements, not subscription telemetry."""
import argparse
import json
import math
from pathlib import Path

def number(value, name, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(name + ' must be finite and nonnegative')
    if maximum is not None and value > maximum: raise ValueError(name + ' exceeds ' + str(maximum))
    return value

def energy_cost(power_watts, seconds, price_per_kwh):
    return number(power_watts, 'power_watts') * number(seconds, 'local_seconds') / 3_600_000 * number(price_per_kwh, 'price_per_kwh')

def estimate(scenario):
    share = number(scenario['delegatable_share'], 'delegatable_share', 1)
    success = number(scenario['success_rate'], 'success_rate', 1)
    overhead = number(scenario['overhead_ratio'], 'overhead_ratio')
    baseline = number(scenario['baseline_usage_units'], 'baseline_usage_units')
    if baseline == 0: raise ValueError('A positive baseline is needed')
    saving = share * (success - overhead)
    energy = energy_cost(scenario.get('power_watts', 0), scenario.get('local_seconds', 0), scenario.get('price_per_kwh', 0))
    return {'basis': 'hypothetical assumptions; not observed savings', 'usage_unit': scenario.get('usage_unit', 'arbitrary consistent units'),
            'baseline_primary_usage_units': baseline,
            'expected_hybrid_primary_usage_units': round(baseline*(1-saving), 6),
            'expected_usage_reduction_percent': round(saving*100, 3),
            'fixed_subscription_fee_reduction': 0,
            'estimated_local_electricity_cost': round(energy, 6), 'currency': scenario.get('currency', 'unspecified'),
            'break_even_success_rate': overhead,
            'limitations': 'No guarantee; ignores hardware amortization and human-time valuation. Subscription usage is not inferred from local tokens.'}

def compare(measurement):
    if measurement.get('same_task_and_acceptance') is not True or measurement.get('both_builds_passed') is not True:
        raise ValueError('Both builds must meet the same acceptance contract before reporting savings')
    if measurement.get('comparable_usage_conditions') is not True:
        raise ValueError('Match model, speed, context/reset conditions and usage units')
    baseline = number(measurement['primary_only_usage_units'], 'primary_only_usage_units')
    hybrid = number(measurement['hybrid_primary_usage_units'], 'hybrid_primary_usage_units')
    if not baseline: raise ValueError('Primary-only baseline must be nonzero')
    energy = energy_cost(measurement.get('power_watts', 0), measurement.get('local_seconds', 0), measurement.get('price_per_kwh', 0))
    extra_saved = number(measurement.get('primary_only_extra_spend', 0), 'primary_only_extra_spend') - number(measurement.get('hybrid_extra_spend', 0), 'hybrid_extra_spend')
    return {'basis': 'user-entered matched measurements; conditions not independently verified',
            'usage_unit': measurement['usage_unit'],
            'primary_usage_units_saved': round(baseline-hybrid, 6),
            'primary_usage_reduction_percent': round((baseline-hybrid)/baseline*100, 3),
            'fixed_subscription_fee_reduction': 0,
            'additional_spend_reduction': extra_saved,
            'estimated_local_electricity_cost': round(energy, 6),
            'cash_difference_after_estimated_electricity': round(extra_saved-energy, 6),
            'currency': measurement.get('currency', 'unspecified'),
            'wall_minutes_difference': number(measurement['primary_only_wall_minutes'], 'primary_only_wall_minutes')-number(measurement['hybrid_wall_minutes'], 'hybrid_wall_minutes')}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    p = commands.add_parser('estimate'); p.add_argument('--scenario', type=Path, required=True)
    p = commands.add_parser('compare'); p.add_argument('--measurement', type=Path, required=True)
    args = parser.parse_args()
    path = args.scenario if args.command == 'estimate' else args.measurement
    data = json.loads(path.read_text(encoding='utf-8'))
    result = estimate(data) if args.command == 'estimate' else compare(data)
    print(json.dumps(result, indent=2))

if __name__ == '__main__': main()
