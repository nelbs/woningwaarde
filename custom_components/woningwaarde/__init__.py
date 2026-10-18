"""CBS-based indexed house values."""

from homeassistant.const import Platform

from .api import CBSClient
from .const import DOMAIN
from .coordinator import WoningCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup(hass, config):
    client = CBSClient(hass)
    await client.load()
    hass.data[DOMAIN] = client
    return True


async def async_setup_entry(hass, entry):
    coordinator = WoningCoordinator(hass, entry, hass.data[DOMAIN])
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
