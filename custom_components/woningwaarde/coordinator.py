"""One coordinator per house; all houses share the CBS cache."""

import logging
from datetime import UTC, datetime, timedelta

import aiohttp
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .calculate import calculate_combined, calculate_dated
from .const import CACHE_TTL_SECONDS, DOMAIN, REGION_TABLE, TYPE_TABLE, selections


class WoningCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry, client):
        super().__init__(
            hass,
            logging.getLogger(__name__),
            name=DOMAIN,
            config_entry=entry,
            # HA rounds scheduled deadlines; a daily job may run just before the
            # independent 24-hour cache expires. Check locally each hour so a
            # cache hit cannot defer the next network attempt by a whole day.
            update_interval=timedelta(hours=1),
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
            local_date = dt_util.now().date()
            mode = data.get("calculation_mode", "quarter")
            if mode == "daily_forecast":
                result = calculate_dated(
                    regional, typed, national, data, target_date=local_date
                )
            elif mode == "quarter":
                result = calculate_combined(
                    regional, typed, national, data, today=local_date
                )
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
        tables = (
            [REGION_TABLE] if woningtype == "T001100" else [REGION_TABLE, TYPE_TABLE]
        )
        cache_times = {}
        for table in tables:
            cached = self.client.cache.get(table)
            if cached is not None:
                attempt = cached["attempt"]
                cache_times[table] = {
                    "last_attempt": datetime.fromtimestamp(attempt, UTC).isoformat(),
                    "next_attempt_eligible": datetime.fromtimestamp(
                        attempt + CACHE_TTL_SECONDS, UTC
                    ).isoformat(),
                }
        return {
            **result,
            "region": region,
            "woningtype": woningtype,
            "tables": tables,
            "last_checked": datetime.now(UTC).isoformat(),
            "source_cache": cache_times,
        }
