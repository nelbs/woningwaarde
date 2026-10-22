"""Shared, persistent daily CBS cache, including failed-attempt throttling."""

import asyncio
import time

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .const import CACHE_TTL_SECONDS, DOMAIN, INDEX


class CBSClient:
    def __init__(self, hass):
        self.session = async_get_clientsession(hass)
        self.store = Store(hass, 1, f"{DOMAIN}.cbs")
        self.cache = {}
        self.lock = asyncio.Lock()

    async def load(self):
        self.cache = await self.store.async_load() or {}

    async def rows(self, table):
        async with self.lock:
            now = time.time()
            cached = self.cache.get(table, {})
            if now - cached.get("attempt", 0) < CACHE_TTL_SECONDS:
                if cached.get("error"):
                    raise ValueError("CBS unavailable; next attempt after 24 hours")
                return cached["rows"]
            # Save the attempt before I/O, also enforcing the limit after a restart.
            self.cache[table] = {**cached, "attempt": now, "error": True}
            await self.store.async_save(self.cache)
            dimension = "RegioS" if table == "85792NED" else "TypeWoning"
            url = f"https://opendata.cbs.nl/ODataApi/OData/{table}/TypedDataSet"
            params = {
                "$select": f"{dimension},Perioden,{INDEX}",
                "$filter": "substringof('KW',Perioden)",
            }
            rows = []
            async with asyncio.timeout(60):
                while url:
                    async with self.session.get(
                        url, params=params, timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        response.raise_for_status()
                        page = await response.json()
                    rows.extend(page["value"])
                    url = page.get("odata.nextLink")
                    if url and not url.startswith(
                        "https://opendata.cbs.nl/ODataApi/OData/"
                    ):
                        raise ValueError("Unexpected pagination host")
                    params = None
            self.cache[table] = {"attempt": now, "error": False, "rows": rows}
            await self.store.async_save(self.cache)
            return rows
