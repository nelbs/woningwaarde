"""Configure any number of independently identified houses in the UI."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .calculate import validate
from .const import DOMAIN, HOUSE_TYPES, REGIONS, selections


def schema(defaults=None):
    defaults = defaults or {}
    region, woningtype = selections(defaults)
    return vol.Schema(
        {
            vol.Required("house_id", default=defaults.get("house_id", "")): str,
            vol.Required("name", default=defaults.get("name", "Woning")): str,
            vol.Required("region", default=region): vol.In(REGIONS),
            vol.Required("woningtype", default=woningtype): vol.In(HOUSE_TYPES),
            vol.Required("waarde", default=defaults.get("waarde", 250000)): vol.Coerce(
                float
            ),
            vol.Required(
                "datum", default=defaults.get("datum", "2020-01-01")
            ): selector.DateSelector(),
        }
    )


class WoningwaardeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                validate(user_input)
            except (ValueError, TypeError, OverflowError):
                errors["base"] = "invalid_input"
            else:
                user_input = {
                    **user_input,
                    "house_id": user_input["house_id"].strip().casefold(),
                    "name": user_input["name"].strip(),
                }
                await self.async_set_unique_id(user_input["house_id"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input["name"], data=user_input
                )
        return self.async_show_form(
            step_id="user", data_schema=schema(user_input), errors=errors
        )

    async def async_step_reconfigure(self, user_input=None):
        entry = self._get_reconfigure_entry()
        errors = {}
        if user_input is not None:
            try:
                validate(user_input)
            except (ValueError, TypeError, OverflowError):
                errors["base"] = "invalid_input"
            else:
                if user_input["house_id"].strip().casefold() != entry.unique_id:
                    errors["base"] = "identifier_changed"
                else:
                    return self.async_update_reload_and_abort(
                        entry, data_updates=user_input, title=user_input["name"]
                    )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema(user_input or entry.data),
            errors=errors,
        )
