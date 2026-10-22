"""One coordinator per house; all houses share the CBS cache."""

import logging
from datetime import timedelta

import aiohttp
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .calculate import calculate_combined, calculate_dated
from .const import DOMAIN, REGION_TABLE, TYPE_TABLE, selections


class WoningCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, client):
        super().__init__(
            hass,
            logging.getLogger(__name__),
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(days=1),
        )
        self.entry = entry
        self.client = client

    async def _async_update_data(self):
        data = self.entry.data
        region, woningtype = selections(data)
        try:
            rows = await self.client.rows(REGION_TABLE)
            regional = [r for r in rows if r["RegioS"].strip() == region]
            national = [r for r in rows if r["RegioS"].strip() == "NL01"]
            if woningtype == "T001100":
                typed = national
            else:
                type_rows = await self.client.rows(TYPE_TABLE)
                typed = [r for r in type_rows if r["TypeWoning"].strip() == woningtype]
            mode = data.get("calculation_mode", "quarter")
            if mode == "daily_forecast":
                result = calculate_dated(regional, typed, national, data)
            elif mode == "quarter":
                result = calculate_combined(regional, typed, national, data)
                result["calculation_mode"] = "quarter"
                result["is_forecast"] = False
            else:
                raise ValueError("Unknown calculation mode")
        except (
            aiohttp.ClientError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
        ) as err:
            raise UpdateFailed(f"CBS index could not be updated: {err}") from err
        return {
            **result,
            "region": region,
            "woningtype": woningtype,
            "tables": [REGION_TABLE]
            if woningtype == "T001100"
            else [REGION_TABLE, TYPE_TABLE],
        }
