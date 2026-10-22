"""CBS calculations with explicit quarter and date-based forecast modes."""

import math
from datetime import UTC, date, datetime


def validate(data, today=None):
    """Validate price, date and user-supplied house identifier."""
    value = float(data["waarde"])
    known = date.fromisoformat(str(data["datum"]))
    if not math.isfinite(value) or value <= 0:
        raise ValueError("invalid value")
    if not date(1995, 1, 1) <= known <= (today or datetime.now(UTC).date()):
        raise ValueError("invalid date")
    if not data["name"].strip() or not data["house_id"].strip():
        raise ValueError("empty identifier")
    return known


def calculate(rows, data):
    """Use the quarter containing the known date and latest published quarter."""
    known = validate(data)
    base_period = f"{known.year}KW{(known.month - 1) // 3 + 1:02}"
    indices = index_map(rows)
    if base_period not in indices:
        raise ValueError("No published index for the reference quarter")
    latest = max(indices)
    return {
        "value": round(
            float(data["waarde"]) * indices[latest] / indices[base_period], 2
        ),
        "base_period": base_period,
        "latest_period": latest,
        "base_index": indices[base_period],
        "latest_index": indices[latest],
    }


def index_map(rows):
    """Valid positive quarter indices only; exclude annual and future rows."""
    current = datetime.now(UTC).date()
    last_period = f"{current.year}KW{(current.month - 1) // 3 + 1:02}"
    indices = {}
    for row in rows:
        period = row["Perioden"]
        value = row.get("PrijsindexVerkoopprijzen_1")
        if (
            len(period) == 8
            and period[4:6] == "KW"
            and period[6:] in {"01", "02", "03", "04"}
            and period <= last_period
            and isinstance(value, (int, float))
            and math.isfinite(value)
            and value > 0
        ):
            indices[period] = value
    return indices


def calculate_combined(region_rows, type_rows, national_rows, data, today=None):
    """Type growth corrected by regional/national growth, at a common quarter."""
    known = validate(data, today=today)
    base = f"{known.year}KW{(known.month - 1) // 3 + 1:02}"
    indices = {
        "region": index_map(region_rows),
        "woningtype": index_map(type_rows),
        "national": index_map(national_rows),
    }
    common = set.intersection(*(set(values) for values in indices.values()))
    if base not in common:
        raise ValueError("No published reference-quarter index in all required series")
    latest = max(common)
    growth = {key: values[latest] / values[base] for key, values in indices.items()}
    factor = growth["woningtype"] * growth["region"] / growth["national"]
    value = float(data["waarde"]) * factor
    if not math.isfinite(value):
        raise ValueError("Calculated value is not finite")
    return {
        "value": round(value, 2),
        "base_period": base,
        "latest_period": latest,
        "growth_factors": growth,
        "combined_growth_factor": factor,
        "indices": {
            key: {"base": values[base], "latest": values[latest]}
            for key, values in indices.items()
        },
        "method": "reference_value * type_growth * region_growth / national_growth",
    }


def _next_quarter_start(day):
    """Calendar quarter boundary, not a fixed number of days."""
    month = day.month + 3
    return date(day.year + (month > 12), (month - 1) % 12 + 1, 1)


def _quarter_end_date(period):
    """Map a quarterly average to the first day after that quarter by convention."""
    return _next_quarter_start(date(int(period[:4]), 3 * (int(period[6:]) - 1) + 1, 1))


def _dated_index(points, target):
    """Interpolate linearly; extrapolate only the last observed quarterly slope."""
    from bisect import bisect_left

    dates = sorted(points)
    position = bisect_left(dates, target)
    if position < len(dates) and dates[position] == target:
        return points[target]
    if position == 0:
        raise ValueError("Reference date precedes the first available quarter boundary")
    if position == len(dates):
        latest = dates[-1]
        # The calculator documents a four-calendar-month forecast horizon.
        month = latest.month + 4
        limit = date(latest.year + (month - 1) // 12, (month - 1) % 12 + 1, 1)
        if target > limit or len(dates) < 2:
            raise ValueError(
                "Forecast requires two quarters and cannot exceed four months"
            )
        left, right = dates[-2:]
    else:
        left, right = dates[position - 1 : position + 1]
    if right != _next_quarter_start(left):
        raise ValueError("Missing consecutive quarter for interpolation or forecast")
    value = points[left] + (points[right] - points[left]) * (
        (target - left).days / (right - left).days
    )
    if not math.isfinite(value) or value <= 0:
        raise ValueError("Interpolated or forecast index is not positive and finite")
    return value


def calculate_dated(region_rows, type_rows, national_rows, data, target_date=None):
    """Explicit date convention and forecast; keep every series on the same dates.

    A quarter index is anchored at the first day after its quarter. This is a
    modelling convention, not a claim that CBS publishes daily house prices.
    All calculations use the current CBS series without fitted scaling factors.
    """
    target = target_date or datetime.now(UTC).date()
    known = validate(data, today=target)
    if target < known:
        raise ValueError("Valuation date precedes the reference date")
    indices = {
        "region": index_map(region_rows),
        "woningtype": index_map(type_rows),
        "national": index_map(national_rows),
    }
    common = set.intersection(*(set(values) for values in indices.values()))
    if not common:
        raise ValueError("No common published quarters")
    latest = max(common)
    published_date = _quarter_end_date(latest)
    points = {
        key: {_quarter_end_date(period): values[period] for period in common}
        for key, values in indices.items()
    }
    reference = {key: _dated_index(values, known) for key, values in points.items()}
    evaluated = {key: _dated_index(values, target) for key, values in points.items()}
    growth = {key: evaluated[key] / reference[key] for key in indices}
    published_growth = {key: indices[key][latest] / reference[key] for key in indices}
    factor = growth["woningtype"] * growth["region"] / growth["national"]
    published_factor = (
        published_growth["woningtype"]
        * published_growth["region"]
        / published_growth["national"]
    )
    price = float(data["waarde"])
    value = price * factor
    if not math.isfinite(value) or not math.isfinite(price * published_factor):
        raise ValueError("Calculated value is not finite")
    return {
        "value": round(value, 2),
        "indexed_value": round(price * published_factor, 2),
        "latest_period": latest,
        "published_date": published_date.isoformat(),
        "valuation_date": target.isoformat(),
        "reference_date": known.isoformat(),
        "is_forecast": target > published_date,
        "forecast_days": max(0, (target - published_date).days),
        "reference_is_forecast": known > published_date,
        "growth_factors": growth,
        "combined_growth_factor": factor,
        "indices": {
            key: {
                "reference_date": reference[key],
                "published": indices[key][latest],
                "valuation_date": evaluated[key],
            }
            for key in indices
        },
        "method": "reference_value * type_growth * region_growth / national_growth",
        "calculation_mode": "daily_forecast",
        "date_convention": "quarter index at start of next quarter; linear between boundaries",
        "forecast_method": "linear continuation of the last quarterly index change",
        "forecast_limit_months": 4,
    }
