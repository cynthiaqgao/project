"""Shared presentation helpers: formatting, labels and display constants (no metric formulas)."""
import math
import pandas as pd

MIN_N = 30  # Display rule from BUILD_SPEC §5: ranked metrics need their own observed n >= 30.
TOP_N = 15
SNAPSHOT_NOTE = ('Los Angeles listing snapshot; collection date unknown; '
                 'prices and availability may have changed.')
MISSING_GRAY = '#B0B0B0'
NAME_LIMIT = 24


def is_missing(value):
    if value is None or value is pd.NA:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def usd(value, decimals=0):
    return 'N/A' if is_missing(value) else f'${float(value):,.{decimals}f}'


def pct(share):
    """Backend shares are 0-1; display as a percentage with 1 decimal."""
    return 'N/A' if is_missing(share) else f'{float(share) * 100:.1f}%'


def num(value, decimals=0):
    return 'N/A' if is_missing(value) else f'{float(value):,.{decimals}f}'


def count(value):
    return '0' if is_missing(value) else f'{int(value):,}'


def short_name(name, limit=NAME_LIMIT):
    name = str(name)
    return name if len(name) <= limit else name[:limit - 1] + '…'


def unique_short_names(names):
    """Truncated axis labels that stay unique; full names belong in hover text."""
    seen, out = {}, []
    for n in names:
        label = short_name(n)
        seen[label] = seen.get(label, 0) + 1
        out.append(label if seen[label] == 1 else f'{label} ({seen[label]})')
    return out


def room_label(room_types):
    if room_types is None or len(room_types) > 1:
        return 'Mixed room types'
    if len(room_types) == 0:
        return 'No room type selected'
    return room_types[0]


def describe_filters(filters, all_neighbourhoods_n):
    nb = filters.neighbourhoods
    nb_text = ('All neighborhoods' if nb is None else
               'No neighborhoods selected' if len(nb) == 0 else
               f'{len(nb)} of {all_neighbourhoods_n} neighborhoods')
    rooms = 'All room types' if filters.room_types is None else (
        ', '.join(filters.room_types) if filters.room_types else 'No room types selected')
    stay = ('All stay lengths (includes unknown minimum stays)' if filters.trip_nights is None
            else f'{filters.trip_nights} planned nights (minimum nights ≤ {filters.trip_nights}; unknown minimum stay excluded)')
    budget = 'No nightly budget' if filters.budget_usd is None else f'Nightly budget ≤ {usd(filters.budget_usd, 2)}'
    return {'Neighborhoods': nb_text, 'Room types': rooms, 'Stay length': stay, 'Budget': budget,
            'Minimum total reviews': str(filters.min_reviews),
            'Exclude flagged high prices': 'On' if filters.exclude_high_prices else 'Off'}


def finite_max(*series, default=1.0):
    values = [float(v) for s in series for v in pd.Series(s).dropna().tolist()]
    values = [v for v in values if math.isfinite(v)]
    return max(values) if values else default
