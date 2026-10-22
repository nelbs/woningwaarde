"""Constants and explicitly supported CBS series."""

DOMAIN = "woningwaarde"
REGION_TABLE = "85792NED"
TYPE_TABLE = "85791NED"
INDEX = "PrijsindexVerkoopprijzen_1"
SERIES = {"NL01": "Nederland (alle woningen)"}
SERIES.update(
    dict(
        zip(
            [f"PV{i}" for i in range(20, 32)],
            [
                "Groningen",
                "Fryslan",
                "Drenthe",
                "Overijssel",
                "Flevoland",
                "Gelderland",
                "Utrecht (provincie)",
                "Noord-Holland",
                "Zuid-Holland",
                "Zeeland",
                "Noord-Brabant",
                "Limburg",
            ],
            strict=True,
        )
    )
)
SERIES.update(
    {
        "GM0363": "Amsterdam",
        "GM0518": "Den Haag",
        "GM0599": "Rotterdam",
        "GM0344": "Utrecht (gemeente)",
        "ZW10290": "Nederland - eengezinswoning",
        "ZW25805": "Nederland - tussenwoning",
        "ZW25806": "Nederland - hoekwoning",
        "ZW10300": "Nederland - twee onder een kap",
        "ZW10320": "Nederland - vrijstaand",
        "ZW25810": "Nederland - appartement",
    }
)

REGIONS = {key: label for key, label in SERIES.items() if not key.startswith("ZW")}
HOUSE_TYPES = {"T001100": "Alle woningtypen"} | {
    key: label.removeprefix("Nederland - ")
    for key, label in SERIES.items()
    if key.startswith("ZW")
}


def selections(data):
    """Keep old single-series configurations equivalent until reconfigured."""
    old = data.get("series", "NL01")
    return (
        data.get("region", "NL01" if old.startswith("ZW") else old),
        data.get("woningtype", old if old.startswith("ZW") else "T001100"),
    )


CALCULATION_MODES = {
    "quarter": "Kwartaal zonder prognose (oude methode)",
    "daily_forecast": "Datumberekening met prognose",
}

# Shared hard limit for network attempts, independent of local entity updates.
CACHE_TTL_SECONDS = 24 * 60 * 60
