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
