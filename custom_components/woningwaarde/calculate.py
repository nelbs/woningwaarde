"""Pure price-index calculation; explicit regional correction, without extrapolation."""

import math
from datetime import UTC, date, datetime


def validate(data):
    """Validate price, date and user-supplied house identifier."""
    value = float(data["waarde"])
    known = date.fromisoformat(str(data["datum"]))
    if not math.isfinite(value) or value <= 0:
        raise ValueError("invalid value")
    if not date(1995, 1, 1) <= known <= datetime.now(UTC).date():
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


def calculate_combined(region_rows, type_rows, national_rows, data):
    """Type growth corrected by regional/national growth, at a common quarter."""
    known = validate(data)
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
