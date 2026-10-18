"""Numeric monetary sensor per config entry."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SERIES


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([WoningwaardeSensor(entry.runtime_data, entry)])


class WoningwaardeSensor(CoordinatorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "EUR"
    _attr_icon = "mdi:home-outline"
    _attr_attribution = (
        "Bron: CBS/Kadaster, Prijsindex Bestaande Koopwoningen (2020=100)"
    )
    _attr_has_entity_name = False
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self.entry = entry
        self._attr_name = entry.data["name"].strip()
        self._attr_unique_id = f"{entry.entry_id}_value"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": self._attr_name,
            "manufacturer": "CBS/Kadaster",
            "model": "Geindexeerde woningwaarde",
        }

    @property
    def native_value(self):
        return self.coordinator.data["value"]

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        return {k: v for k, v in data.items() if k != "value"} | {
            "series_name": SERIES[data["series"]],
            "reference_value": self.entry.data["waarde"],
            "reference_date": self.entry.data["datum"],
            "method": "reference_value * latest_index / base_index",
        }
