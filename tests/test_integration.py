"""Isolated unit tests. HA boundary is stubbed; this is not a live HA test."""

import asyncio
import importlib.util
import json
import sys
import types
import unittest
from datetime import UTC, datetime
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
sys.modules["homeassistant.util"] = types.ModuleType("homeassistant.util")
sys.modules["homeassistant.util"].dt = types.SimpleNamespace(
    now=lambda: datetime.now(UTC)
)

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
        a = await first.async_step_user(
            {**DATA, "region": "NL01", "woningtype": "T001100"}
        )
        b = await second.async_step_user(
            {**DATA, "house_id": "vakantie", "region": "PV25", "woningtype": "T001100"}
        )
        self.assertEqual(a["type"], "create_entry")
        self.assertEqual(b["type"], "create_entry")
        self.assertNotEqual(first.unique_id, second.unique_id)

    async def test_duplicate_id_normalization(self):
        flow = flow_module.WoningwaardeConfigFlow()
        flow.configured = {"thuis"}
        with self.assertRaises(AbortFlow):
            await flow.async_step_user(
                {
                    **DATA,
                    "house_id": " THUIS ",
                    "region": "NL01",
                    "woningtype": "T001100",
                }
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
            flow_module.schema()(
                {**DATA, "region": "imaginary", "woningtype": "T001100"}
            )


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


class CombinedTests(unittest.TestCase):
    def series(self, growth, latest="2025KW01"):
        return [row("2020KW01", 100), row(latest, 100 * growth)]

    def test_multiplicative_correction(self):
        result = calc.calculate_combined(
            self.series(1.4), self.series(1.3), self.series(1.2), DATA
        )
        self.assertEqual(result["value"], round(250000 * 1.3 * 1.4 / 1.2, 2))

    def test_all_types_equals_region(self):
        result = calc.calculate_combined(
            self.series(1.4), self.series(1.2), self.series(1.2), DATA
        )
        self.assertEqual(result["value"], 350000)

    def test_national_region_equals_type(self):
        result = calc.calculate_combined(
            self.series(1.2), self.series(1.3), self.series(1.2), DATA
        )
        self.assertEqual(result["value"], 325000)

    def test_uses_latest_common_quarter(self):
        regional = self.series(1.4) + [row("2025KW02", 200)]
        result = calc.calculate_combined(
            regional, self.series(1.3), self.series(1.2), DATA
        )
        self.assertEqual(result["latest_period"], "2025KW01")
        self.assertEqual(result["indices"]["region"]["latest"], 140)

    def test_missing_base_in_one_series_is_error(self):
        with self.assertRaises(ValueError):
            calc.calculate_combined(
                self.series(1.4), [row("2025KW01", 130)], self.series(1.2), DATA
            )

    def test_real_cbs_combination(self):
        fixture = json.loads((ROOT / "tests/fixtures/combined_cbs.json").read_text())
        result = calc.calculate_combined(
            fixture["PV25"], fixture["ZW10300"], fixture["NL01"], DATA
        )
        growth = [
            fixture[k][-1]["PrijsindexVerkoopprijzen_1"]
            / fixture[k][0]["PrijsindexVerkoopprijzen_1"]
            for k in ["PV25", "ZW10300", "NL01"]
        ]
        self.assertEqual(
            result["value"], round(250000 * growth[1] * growth[0] / growth[2], 2)
        )
        self.assertEqual(result["latest_period"], "2026KW02")

    def test_berekenhet_displayed_example(self):
        # Rounded displayed component values from a single fictitious calculator run.
        # This checks the inferred correction rule, not BerekenHet's date interpolation.
        result = calc.calculate_combined(
            self.series(435500 / 250000),
            self.series(413200 / 250000),
            self.series(408200 / 250000),
            DATA,
        )
        self.assertEqual(round(result["value"], -2), 440800)

    def test_legacy_selection_preserved(self):
        const = sys.modules["woningwaarde.const"]
        self.assertEqual(const.selections({"series": "PV25"}), ("PV25", "T001100"))
        self.assertEqual(const.selections({"series": "ZW10300"}), ("NL01", "ZW10300"))
        self.assertEqual(
            const.selections(
                {"series": "PV25", "region": "PV31", "woningtype": "ZW10300"}
            ),
            ("PV31", "ZW10300"),
        )


class FakeDataCoordinator:
    def __init__(self, *args, **kwargs):
        self.update_interval = kwargs.get("update_interval")


class FakeUpdateFailed(Exception):
    pass


coordinator_boundary.DataUpdateCoordinator = FakeDataCoordinator
coordinator_boundary.UpdateFailed = FakeUpdateFailed
coordinator_module = load("coordinator")


class CoordinatorTests(unittest.IsolatedAsyncioTestCase):
    def make_coordinator(self, data, missing_type=False):
        fixture = json.loads((ROOT / "tests/fixtures/combined_cbs.json").read_text())
        calls = []

        async def rows(table):
            calls.append(table)
            if table == "85792NED":
                return fixture["PV25"] + fixture["NL01"]
            return [] if missing_type else fixture["ZW10300"]

        entry = types.SimpleNamespace(data={**DATA, **data})
        return coordinator_module.WoningCoordinator(
            None, entry, types.SimpleNamespace(rows=rows, cache={})
        ), calls

    async def test_combined_fetches_both_tables(self):
        coordinator, calls = self.make_coordinator(
            {"region": "PV25", "woningtype": "ZW10300"}
        )
        result = await coordinator._async_update_data()
        self.assertEqual(calls, ["85792NED", "85791NED"])
        self.assertEqual(result["region"], "PV25")
        sensor = sensor_module.WoningwaardeSensor(
            types.SimpleNamespace(data=result),
            types.SimpleNamespace(entry_id="test", data=DATA),
        )
        self.assertEqual(
            sensor.extra_state_attributes["house_type_name"], "twee onder een kap"
        )
        self.assertIn("national_growth", sensor.extra_state_attributes["method"])

    async def test_legacy_region_fetches_one_table(self):
        coordinator, calls = self.make_coordinator({"series": "PV25"})
        result = await coordinator._async_update_data()
        self.assertEqual(calls, ["85792NED"])
        self.assertEqual(result["woningtype"], "T001100")

    async def test_legacy_type_keeps_national_region(self):
        coordinator, _ = self.make_coordinator({"series": "ZW10300"})
        result = await coordinator._async_update_data()
        self.assertEqual(result["region"], "NL01")
        fixture = json.loads((ROOT / "tests/fixtures/combined_cbs.json").read_text())
        self.assertEqual(
            result["value"], calc.calculate(fixture["ZW10300"], DATA)["value"]
        )

    async def test_missing_series_reports_unavailable(self):
        coordinator, _ = self.make_coordinator(
            {"region": "PV25", "woningtype": "ZW10300"}, missing_type=True
        )
        with self.assertRaises(FakeUpdateFailed):
            await coordinator._async_update_data()


class DatedCalculationTests(unittest.TestCase):
    def fixture(self):
        return json.loads((ROOT / "tests/fixtures/limburg_20261022.json").read_text())

    def run_example(self, target):
        from datetime import date

        f = self.fixture()
        v = f["series"]
        return calc.calculate_dated(
            v["PV31"], v["ZW10300"], v["NL01"], f["input"], date.fromisoformat(target)
        )

    def test_website_history_matches_archived_series_with_normal_rounding(self):
        evidence = json.loads(
            (ROOT / "tests/fixtures/berekenhet_archived_comparison.json").read_text()
        )
        for series in evidence["series"].values():
            self.assertEqual(len(series["points"]), 31)
            for point in series["points"]:
                price = (
                    evidence["reference_value"]
                    * point["archived_index"]
                    / series["reference_index"]
                )
                self.assertEqual(round(price, -2), point["website_value"])

    def test_archived_and_current_price_ratios_differ(self):
        # Rebasing alone would preserve this ratio. Here the revised history differs.
        evidence = json.loads(
            (ROOT / "tests/fixtures/berekenhet_archived_comparison.json").read_text()
        )
        national = evidence["series"]["NL01"]
        old_q3 = next(
            p["archived_index"] for p in national["points"] if p["period"] == "2016KW03"
        )
        self.assertNotAlmostEqual(
            old_q3 / national["reference_index"], 74.3 / 72.4, places=4
        )

    def test_user_example_with_current_source(self):
        result = self.run_example("2026-10-22")
        # Independently written from actual source indices and 21/92 elapsed days.
        region = (155.6 + (155.6 - 154.0) * 21 / 92) / 76.1
        typed = (158.7 + (158.7 - 157.0) * 21 / 92) / 75.3
        national = (156.4 + (156.4 - 154.9) * 21 / 92) / 72.4
        self.assertEqual(result["value"], round(309000 * typed * region / national, 2))
        self.assertEqual(result["value"], 618011.05)
        self.assertEqual(result["indexed_value"], 616406.46)
        self.assertEqual(result["forecast_days"], 21)
        self.assertTrue(result["is_forecast"])
        self.assertEqual(result["published_date"], "2026-10-01")
        # Do not assert equality with the website's different historical source.
        self.assertNotEqual(
            round(result["value"], -2), self.fixture()["website"]["forecast_value"]
        )

    def test_first_day_of_quarter_uses_previous_quarter(self):
        result = self.run_example("2026-10-01")
        self.assertEqual(result["indices"]["region"]["reference_date"], 76.1)
        self.assertEqual(result["value"], 616406.46)
        self.assertFalse(result["is_forecast"])

    def test_same_reference_and_target_date_returns_known_price(self):
        result = self.run_example("2016-07-01")
        self.assertEqual(result["value"], 309000)
        self.assertFalse(result["is_forecast"])

    def test_old_quarter_mode_remains_reproducible(self):
        f = self.fixture()
        v = f["series"]
        result = calc.calculate_combined(v["PV31"], v["ZW10300"], v["NL01"], f["input"])
        self.assertEqual(result["value"], 607441.75)

    def test_midquarter_reference_interpolates_actual_calendar_days(self):
        from datetime import date

        f = self.fixture()
        v = f["series"]
        result = calc.calculate_dated(
            v["PV31"],
            v["ZW10300"],
            v["NL01"],
            {**f["input"], "datum": "2016-08-01"},
            date(2026, 10, 1),
        )
        self.assertAlmostEqual(
            result["indices"]["region"]["reference_date"],
            76.1 + (77.5 - 76.1) * 31 / 92,
        )

    def test_before_first_boundary_is_error(self):
        from datetime import date

        with self.assertRaises(ValueError):
            calc._dated_index(
                {date(2025, 4, 1): 100, date(2025, 7, 1): 105}, date(2025, 1, 1)
            )

    def test_missing_quarter_does_not_bridge_gap(self):
        from datetime import date

        with self.assertRaises(ValueError):
            calc._dated_index(
                {date(2025, 4, 1): 100, date(2025, 10, 1): 105}, date(2025, 7, 1)
            )

    def test_forecast_requires_two_consecutive_quarters(self):
        from datetime import date

        with self.assertRaises(ValueError):
            calc._dated_index({date(2025, 10, 1): 105}, date(2025, 10, 22))
        with self.assertRaises(ValueError):
            calc._dated_index(
                {date(2025, 4, 1): 100, date(2025, 10, 1): 105}, date(2025, 10, 22)
            )

    def test_four_calendar_month_limit(self):
        from datetime import date

        points = {date(2025, 7, 1): 100, date(2025, 10, 1): 101}
        self.assertGreater(calc._dated_index(points, date(2026, 2, 1)), 101)
        with self.assertRaises(ValueError):
            calc._dated_index(points, date(2026, 2, 2))

    def test_falling_index_and_leap_year_interpolation(self):
        from datetime import date

        points = {date(2024, 1, 1): 100, date(2024, 4, 1): 91}
        self.assertAlmostEqual(
            calc._dated_index(points, date(2024, 3, 1)), 100 - 9 * 60 / 91
        )
        self.assertAlmostEqual(
            calc._dated_index(points, date(2024, 4, 11)), 91 - 9 * 10 / 91
        )

    def test_reference_after_last_publication_is_labelled(self):
        from datetime import date

        f = self.fixture()
        v = f["series"]
        result = calc.calculate_dated(
            v["PV31"],
            v["ZW10300"],
            v["NL01"],
            {**f["input"], "datum": "2026-10-10"},
            date(2026, 10, 22),
        )
        self.assertTrue(result["reference_is_forecast"])
        self.assertGreater(result["value"], 309000)

    def test_default_keeps_existing_entries_explicit(self):
        def default_mode(defaults):
            return next(
                key.default()
                for key in flow_module.schema(defaults).schema
                if key.schema == "calculation_mode"
            )

        self.assertEqual(default_mode(DATA), "quarter")
        self.assertEqual(default_mode({}), "daily_forecast")
        self.assertEqual(
            default_mode({**DATA, "calculation_mode": "daily_forecast"}),
            "daily_forecast",
        )

    def test_future_valuation_before_reference_rejected(self):
        with self.assertRaises(ValueError):
            self.run_example("2016-06-30")


class DatedCoordinatorTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_mode_and_preserved_daily_cache(self):
        from datetime import date

        f = json.loads((ROOT / "tests/fixtures/limburg_20261022.json").read_text())
        calls = []

        async def rows(table):
            calls.append(table)
            if table == "85792NED":
                return f["series"]["PV31"] + f["series"]["NL01"]
            return f["series"]["ZW10300"]

        entry = types.SimpleNamespace(
            data={
                **f["input"],
                "region": "PV31",
                "woningtype": "ZW10300",
                "calculation_mode": "daily_forecast",
            }
        )
        coordinator = coordinator_module.WoningCoordinator(
            None, entry, types.SimpleNamespace(rows=rows, cache={})
        )
        # Freeze only the default target date; keep the implementation under test.
        original = calc.calculate_dated

        def calculate_at_fixed_date(*args, **kwargs):
            return original(*args, **{**kwargs, "target_date": date(2026, 10, 22)})

        with patch.object(
            coordinator_module, "calculate_dated", side_effect=calculate_at_fixed_date
        ):
            result = await coordinator._async_update_data()
        self.assertEqual(result["value"], 618011.05)
        self.assertEqual(calls, ["85792NED", "85791NED"])
        self.assertEqual(result["calculation_mode"], "daily_forecast")


class RefreshTimingTests(unittest.IsolatedAsyncioTestCase):
    async def test_early_daily_callback_does_not_delay_fetch_another_day(self):
        from datetime import timedelta

        fixture = json.loads(
            (ROOT / "tests/fixtures/limburg_20261022.json").read_text()
        )
        new_rows = fixture["series"]["PV31"] + fixture["series"]["NL01"]
        old_rows = [r for r in new_rows if r["Perioden"] != "2026KW03"]
        session = Session([{"value": old_rows}, {"value": new_rows}])
        client = api.CBSClient(session)
        entry = types.SimpleNamespace(
            data={**fixture["input"], "region": "PV31", "woningtype": "T001100"}
        )
        coordinator = coordinator_module.WoningCoordinator(None, entry, client)
        self.assertEqual(coordinator.update_interval, timedelta(hours=1))
        start = 1800000000
        with patch.object(api.time, "time", return_value=start):
            first = await coordinator._async_update_data()
        self.assertEqual(first["latest_period"], "2026KW02")
        self.assertEqual(session.calls, 1)
        # The original daily HA callback can run a fraction of a second early.
        with patch.object(api.time, "time", return_value=start + 86400 - 0.5):
            still_cached = await coordinator._async_update_data()
        self.assertEqual(still_cached["latest_period"], "2026KW02")
        self.assertEqual(session.calls, 1)
        # The next local hourly check fetches after expiry, rather than waiting a day.
        with patch.object(api.time, "time", return_value=start + 86400 - 0.5 + 3600):
            fresh = await coordinator._async_update_data()
        self.assertEqual(fresh["latest_period"], "2026KW03")
        self.assertEqual(session.calls, 2)

    async def test_hourly_checks_keep_hard_network_limit(self):
        session = Session()
        client = api.CBSClient(session)
        for hour in range(24):
            with patch.object(api.time, "time", return_value=1800000000 + hour * 3600):
                await client.rows("85792NED")
        self.assertEqual(session.calls, 1)
        with patch.object(api.time, "time", return_value=1800000000 + 86400):
            await client.rows("85792NED")
        self.assertEqual(session.calls, 2)

    async def test_cache_diagnostics_show_eligibility_without_claiming_a_fetch(self):
        from datetime import datetime

        fixture = json.loads(
            (ROOT / "tests/fixtures/limburg_20261022.json").read_text()
        )
        rows = fixture["series"]["PV31"] + fixture["series"]["NL01"]
        session = Session([{"value": rows}])
        client = api.CBSClient(session)
        entry = types.SimpleNamespace(
            data={**fixture["input"], "region": "PV31", "woningtype": "T001100"}
        )
        coordinator = coordinator_module.WoningCoordinator(None, entry, client)
        start = 1800000000
        with patch.object(api.time, "time", return_value=start):
            first = await coordinator._async_update_data()
        with patch.object(api.time, "time", return_value=start + 3600):
            cached = await coordinator._async_update_data()
        self.assertEqual(first["source_cache"], cached["source_cache"])
        info = cached["source_cache"]["85792NED"]
        self.assertEqual(
            datetime.fromisoformat(info["last_attempt"]).timestamp(), start
        )
        self.assertEqual(
            datetime.fromisoformat(info["next_attempt_eligible"]).timestamp(),
            start + 86400,
        )
        self.assertIsNotNone(datetime.fromisoformat(cached["last_checked"]).tzinfo)
        self.assertEqual(session.calls, 1)


class LocalDateTests(unittest.IsolatedAsyncioTestCase):
    async def calculate_at(self, local_now):
        fixture = json.loads(
            (ROOT / "tests/fixtures/limburg_20261022.json").read_text()
        )

        async def rows(table):
            if table == "85792NED":
                return fixture["series"]["PV31"] + fixture["series"]["NL01"]
            return fixture["series"]["ZW10300"]

        entry = types.SimpleNamespace(
            data={
                **fixture["input"],
                "region": "PV31",
                "woningtype": "ZW10300",
                "calculation_mode": "daily_forecast",
            }
        )
        coordinator = coordinator_module.WoningCoordinator(
            None, entry, types.SimpleNamespace(rows=rows, cache={})
        )
        with patch.object(coordinator_module.dt_util, "now", return_value=local_now):
            return await coordinator._async_update_data()

    async def test_dutch_midnight_uses_configured_day(self):
        from datetime import timedelta, timezone

        local_now = datetime(2026, 10, 23, 0, 9, tzinfo=timezone(timedelta(hours=2)))
        self.assertEqual(local_now.astimezone(UTC).day, 22)
        result = await self.calculate_at(local_now)
        self.assertEqual(result["valuation_date"], "2026-10-23")
        self.assertEqual(result["forecast_days"], 22)
        self.assertEqual(result["value"], 618087.46)

    async def test_western_timezone_keeps_previous_local_day(self):
        from datetime import timedelta, timezone

        local_now = datetime(2026, 10, 22, 20, 9, tzinfo=timezone(timedelta(hours=-4)))
        self.assertEqual(local_now.astimezone(UTC).day, 23)
        result = await self.calculate_at(local_now)
        self.assertEqual(result["valuation_date"], "2026-10-22")
        self.assertEqual(result["value"], 618011.05)

    async def test_winter_offset_is_not_hard_coded_to_summer(self):
        from datetime import timedelta, timezone

        local_now = datetime(2026, 11, 1, 0, 9, tzinfo=timezone(timedelta(hours=1)))
        self.assertEqual(local_now.astimezone(UTC).day, 31)
        result = await self.calculate_at(local_now)
        self.assertEqual(result["valuation_date"], "2026-11-01")
        self.assertEqual(result["forecast_days"], 31)

    async def test_reference_date_validation_uses_same_local_day(self):
        from datetime import date, timedelta, timezone

        local_now = datetime(2026, 10, 23, 0, 9, tzinfo=timezone(timedelta(hours=2)))
        flow = flow_module.WoningwaardeConfigFlow()
        with patch.object(flow_module.dt_util, "now", return_value=local_now):
            result = await flow.async_step_user(
                {
                    **DATA,
                    "datum": "2026-10-23",
                    "region": "PV31",
                    "woningtype": "ZW10300",
                }
            )
            invalid = await flow.async_step_user(
                {
                    **DATA,
                    "datum": "2026-10-24",
                    "region": "PV31",
                    "woningtype": "ZW10300",
                }
            )
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(invalid["errors"], {"base": "invalid_input"})
        self.assertEqual(
            calc.validate({**DATA, "datum": "2026-10-23"}, today=date(2026, 10, 23)),
            date(2026, 10, 23),
        )


if __name__ == "__main__":
    unittest.main()
