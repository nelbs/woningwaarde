# Sensor for scrape berekenhet.nl
import logging
import datetime
import json
import voluptuous as vol

from homeassistant.util import dt
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    ATTR_ATTRIBUTION, CONF_NAME, CONF_SCAN_INTERVAL, CONF_REGION, CONF_TYPE)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.restore_state import RestoreEntity

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = 'Information provided by berekenhet.nl'

SCAN_INTERVAL = datetime.timedelta(seconds=300)

CONF_DATE = 'datum'
CONF_VALUE = 'waarde'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_TYPE, default="2onder1kap"): cv.string,
    vol.Required(CONF_REGION, default="LB"): cv.string,
    vol.Required(CONF_VALUE, default="250000"): cv.string,
    vol.Required(CONF_DATE, default="01-01-2000"): cv.string,
    vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.time_period,
    vol.Optional(CONF_NAME, default='woningwaarde'): cv.string,
})

def setup_platform(hass, config, add_entities, discovery_info=None):
    name = config.get(CONF_NAME)
    woningtype = config.get(CONF_TYPE)
    regio = config.get(CONF_REGION)
    datum_bekend = config.get(CONF_DATE)
    prijs_bekend = config.get(CONF_VALUE)
    add_entities([Woningwaarde(name, woningtype, regio, prijs_bekend, datum_bekend)], True)

class Woningwaarde(RestoreEntity):
    def __init__(self, name, woningtype, regio, prijs_bekend, datum_bekend):
        # initialiseren sensor
        self._name = name
        self._woningtype = woningtype
        self._regio = regio
        self._prijs_bekend = prijs_bekend
        self._datum_bekend = datum_bekend
        self._state = None
        self._attributes = {'last_update': None}
        self.update()

    @property
    def name(self):
        return self._name

    @property
    def unit_of_measurement(self):
        # Return the unit of measurement of this entity, if any.
        return '€'

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        # Return the state attributes.
        return self._attributes

    @property
    def icon(self):
        # Icon to use in the frontend.                            
        return 'mdi:home'

    def update(self):
        import requests
        from bs4 import BeautifulSoup
        import re
        from datetime import date

        url = "https://www.berekenhet.nl/wonen-en-hypotheek/woning-waarde-huizenprijzen.html"
        payload = {
                "tkmFormStep": "1/",
                "tkmsid": "5f9a22d95b50f310b6e82bbda585dd71", 
                "woningtype": self._woningtype,
                "regio": self._regio,
                "bekendPrijs": self._prijs_bekend,
                "bekendDatum": self._datum_bekend,
                "gevraagdDatum": str(date.today().strftime("%d-%m-%Y")),
                "tkmFormNav": "next"}

        response = requests.post(url, data=payload)
        soup = BeautifulSoup(response.content, 'html.parser')
        result = str(soup.findAll("div", {"class": "tkm-result"})[0])
        waarde =  re.sub(r"\<[^<>]*\>", "", result).split()[1]
        self._attributes['last_update'] = dt.now().isoformat('T')
        self._state = waarde

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if not state:
            return
        self._state = state.state

