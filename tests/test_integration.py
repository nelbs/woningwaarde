"""Isolated unit tests. HA boundary is stubbed; this is not a live HA test."""

import asyncio
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "custom_components" / "woningwaarde"
pkg = types.ModuleType("woningwaarde")
pkg.__path__ = [str(PACKAGE)]
sys.modules["woningwaarde"] = pkg


def load(name):
    spec = importlib.util.spec_from_file_location(
        f"woningwaarde.{name}", PACKAGE / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


calc = load("calculate")
load("const")


class FakeStore:
    saved = None

    def __init__(self, *args):
        pass

    async def async_load(self):
        return self.saved

    async def async_save(self, value):
        self.saved = json.loads(json.dumps(value))


for name in [
    "homeassistant",
    "homeassistant.helpers",
    "homeassistant.helpers.storage",
    "homeassistant.helpers.aiohttp_client",
]:
    sys.modules[name] = types.ModuleType(name)
sys.modules["homeassistant.helpers.storage"].Store = FakeStore
sys.modules["homeassistant.helpers.aiohttp_client"].async_get_clientsession = (
    lambda hass: hass
)
api = load("api")

DATA = {"name": "Thuis", "house_id": "thuis", "waarde": 250000, "datum": "2020-02-20"}


def row(period, index):
    return {"Perioden": period, "PrijsindexVerkoopprijzen_1": index}


class CalculationTests(unittest.TestCase):
    def test_ratio_and_year_exclusion(self):
        result = calc.calculate(
            [row("2020KW01", 100), row("2025KW02", 150), row("2025JJ00", 900)], DATA
        )
        self.assertEqual(result["value"], 375000)
        self.assertEqual(result["latest_period"], "2025KW02")

    def test_reference_quarter_not_published(self):
        with self.assertRaises(ValueError):
            calc.calculate([row("2025KW01", 150)], DATA)

    def test_invalid_prices(self):
        for price in [0, -1, float("nan"), float("inf")]:
            with self.subTest(price=price), self.assertRaises(ValueError):
                calc.validate({**DATA, "waarde": price})

    def test_invalid_dates(self):
        for date in ["1994-12-31", "2999-01-01", "2020-02-30", "bad"]:
            with self.subTest(date=date), self.assertRaises(ValueError):
                calc.validate({**DATA, "datum": date})

    def test_invalid_identifiers(self):
        for key in ["name", "house_id"]:
            with self.assertRaises(ValueError):
                calc.validate({**DATA, key: " "})

    def test_missing_zero_and_invalid_indices(self):
        rows = [
            row("2020KW01", 100),
            row("2025KW01", 120),
            row("2025KW02", None),
            row("2025KW03", 0),
            row("2025KW04", float("nan")),
        ]
        self.assertEqual(calc.calculate(rows, DATA)["value"], 300000)

    def test_same_quarter(self):
        self.assertEqual(calc.calculate([row("2020KW01", 100)], DATA)["value"], 250000)

    def test_real_cbs_fixtures(self):
        fixtures = json.loads((ROOT / "tests/fixtures/cbs.json").read_text())
        for series, rows in fixtures.items():
            with self.subTest(series=series):
                result = calc.calculate(rows, DATA)
                self.assertEqual(result["latest_period"], "2026KW02")
                self.assertEqual(
                    result["value"],
                    round(
                        250000
                        * rows[-1]["PrijsindexVerkoopprijzen_1"]
                        / rows[0]["PrijsindexVerkoopprijzen_1"],
                        2,
                    ),
                )


class Response:
    def __init__(self, page, fail=False):
        self.page, self.fail = page, fail

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def raise_for_status(self):
        if self.fail:
            raise ValueError("HTTP error")

    async def json(self):
        return self.page


class Session:
    def __init__(self, pages=None, fail=False):
        self.calls = 0
        self.pages = pages or [{"value": [row("2020KW01", 100)]}]
        self.fail = fail

    def get(self, *args, **kwargs):
        page = self.pages[min(self.calls, len(self.pages) - 1)]
        self.calls += 1
        return Response(page, self.fail)


class CacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_shared_concurrent_requests(self):
        session = Session()
        client = api.CBSClient(session)
        results = await asyncio.gather(*(client.rows("85792NED") for _ in range(5)))
        self.assertEqual(session.calls, 1)
        self.assertTrue(all(r == results[0] for r in results))

    async def test_restart_uses_saved_cache(self):
        session = Session()
        client = api.CBSClient(session)
        await client.rows("85792NED")
        restarted = api.CBSClient(session)
        restarted.store = client.store
        await restarted.load()
        await restarted.rows("85792NED")
        self.assertEqual(session.calls, 1)

    async def test_failed_attempt_is_throttled_even_after_restart(self):
        session = Session(fail=True)
        client = api.CBSClient(session)
        with self.assertRaises(ValueError):
            await client.rows("85792NED")
        restarted = api.CBSClient(session)
        restarted.store = client.store
        await restarted.load()
        with self.assertRaises(ValueError):
            await restarted.rows("85792NED")
        self.assertEqual(session.calls, 1)

    async def test_expiry_after_24_hours(self):
        session = Session()
        client = api.CBSClient(session)
        with patch.object(api.time, "time", return_value=100000):
            await client.rows("85792NED")
        with patch.object(api.time, "time", return_value=186399):
            await client.rows("85792NED")
        self.assertEqual(session.calls, 1)
        with patch.object(api.time, "time", return_value=186400):
            await client.rows("85792NED")
        self.assertEqual(session.calls, 2)

    async def test_tables_have_separate_cache(self):
        session = Session()
        client = api.CBSClient(session)
        await client.rows("85792NED")
        await client.rows("85791NED")
        self.assertEqual(session.calls, 2)

    async def test_pagination(self):
        session = Session(
            [
                {
                    "value": [1],
                    "odata.nextLink": "https://opendata.cbs.nl/ODataApi/OData/next",
                },
                {"value": [2]},
            ]
        )
        self.assertEqual(await api.CBSClient(session).rows("85792NED"), [1, 2])

    async def test_rejects_unexpected_pagination(self):
        session = Session([{"value": [1], "odata.nextLink": "https://example.org"}])
        with self.assertRaises(ValueError):
            await api.CBSClient(session).rows("85792NED")
        self.assertEqual(session.calls, 1)


# Minimal HA boundary objects let us execute the real flow methods.
class AbortFlow(Exception):
    pass


class FakeFlow:
    configured = frozenset()

    def __init_subclass__(cls, **kwargs):
        pass

    async def async_set_unique_id(self, unique_id):
        self.unique_id = unique_id

    def _abort_if_unique_id_configured(self):
        if self.unique_id in self.configured:
            raise AbortFlow("already_configured")

    def async_create_entry(self, **kwargs):
        return {"type": "create_entry", **kwargs}

    def async_show_form(self, **kwargs):
        return {"type": "form", **kwargs}

    def _get_reconfigure_entry(self):
        return self.entry

    def async_update_reload_and_abort(self, entry, **kwargs):
        return {"type": "abort", **kwargs}


sys.modules["homeassistant"].config_entries = types.SimpleNamespace(ConfigFlow=FakeFlow)
sys.modules["homeassistant.helpers"].selector = types.SimpleNamespace(
    DateSelector=lambda: str
)
flow_module = load("config_flow")


class FlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_two_houses_same_name_different_ids(self):
        first = flow_module.WoningwaardeConfigFlow()
        second = flow_module.WoningwaardeConfigFlow()
        a = await first.async_step_user({**DATA, "series": "NL01"})
        b = await second.async_step_user(
            {**DATA, "house_id": "vakantie", "series": "PV25"}
        )
        self.assertEqual(a["type"], "create_entry")
        self.assertEqual(b["type"], "create_entry")
        self.assertNotEqual(first.unique_id, second.unique_id)

    async def test_duplicate_id_normalization(self):
        flow = flow_module.WoningwaardeConfigFlow()
        flow.configured = {"thuis"}
        with self.assertRaises(AbortFlow):
            await flow.async_step_user(
                {**DATA, "house_id": " THUIS ", "series": "NL01"}
            )

    async def test_bad_input_shows_error(self):
        flow = flow_module.WoningwaardeConfigFlow()
        result = await flow.async_step_user({**DATA, "waarde": -1})
        self.assertEqual(result["errors"], {"base": "invalid_input"})

    async def test_reconfigure_preserves_identity(self):
        flow = flow_module.WoningwaardeConfigFlow()
        flow.entry = types.SimpleNamespace(unique_id="thuis", data=DATA)
        result = await flow.async_step_reconfigure({**DATA, "waarde": 300000})
        self.assertEqual(result["type"], "abort")
        self.assertEqual(result["data_updates"]["waarde"], 300000)
        result = await flow.async_step_reconfigure({**DATA, "house_id": "other"})
        self.assertEqual(result["errors"], {"base": "identifier_changed"})

    async def test_series_schema_rejects_unknown(self):
        import voluptuous

        with self.assertRaises(voluptuous.Invalid):
            flow_module.schema()({**DATA, "series": "imaginary"})


# Exercise the sensor constructor against a minimal coordinator boundary.
class FakeCoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator


sys.modules["homeassistant.components"] = types.ModuleType("homeassistant.components")
sensor_boundary = types.ModuleType("homeassistant.components.sensor")
sensor_boundary.SensorDeviceClass = types.SimpleNamespace(MONETARY="monetary")
sensor_boundary.SensorEntity = type("SensorEntity", (), {})
sys.modules["homeassistant.components.sensor"] = sensor_boundary
coordinator_boundary = types.ModuleType("homeassistant.helpers.update_coordinator")
coordinator_boundary.CoordinatorEntity = FakeCoordinatorEntity
sys.modules["homeassistant.helpers.update_coordinator"] = coordinator_boundary
sensor_module = load("sensor")


class SensorNamingTests(unittest.TestCase):
    def make_sensor(self, name, entry_id="house1"):
        entry = types.SimpleNamespace(
            entry_id=entry_id, title="Woning", data={**DATA, "name": name}
        )
        return sensor_module.WoningwaardeSensor(
            types.SimpleNamespace(data={"value": 300000}), entry
        )

    def test_configured_name_is_sensor_and_device_name(self):
        sensor = self.make_sensor("haviklaan 28")
        self.assertEqual(sensor._attr_name, "haviklaan 28")
        self.assertFalse(sensor._attr_has_entity_name)
        self.assertEqual(sensor._attr_device_info["name"], "haviklaan 28")

    def test_reconfigure_name_keeps_identity(self):
        original = self.make_sensor("haviklaan 28")
        renamed = self.make_sensor("Vakantiehuis")
        self.assertEqual(original._attr_unique_id, renamed._attr_unique_id)
        self.assertEqual(renamed._attr_name, "Vakantiehuis")
        other = self.make_sensor("Vakantiehuis", "house2")
        self.assertNotEqual(renamed._attr_unique_id, other._attr_unique_id)

    def test_standard_house_icon(self):
        self.assertEqual(
            self.make_sensor("haviklaan 28")._attr_icon, "mdi:home-outline"
        )


if __name__ == "__main__":
    unittest.main()
