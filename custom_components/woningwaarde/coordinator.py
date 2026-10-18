"""One coordinator per house; all houses share the CBS cache."""

import logging
from datetime import timedelta

import aiohttp
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .calculate import calculate
from .const import DOMAIN, REGION_TABLE, TYPE_TABLE


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
        series = data["series"]
        table = TYPE_TABLE if series.startswith("ZW") else REGION_TABLE
        dimension = "TypeWoning" if table == TYPE_TABLE else "RegioS"
        try:
            rows = await self.client.rows(table)
            result = calculate(
                [r for r in rows if r[dimension].strip() == series], data
            )
        except (
            aiohttp.ClientError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
        ) as err:
            raise UpdateFailed(f"CBS index could not be updated: {err}") from err
        return {**result, "series": series, "table": table}
