# Woningwaarde

Woningwaarde is a Home Assistant integration that estimates the value of your home from the public CBS/Kadaster house price index (Prijsindex Bestaande Koopwoningen). No API key is needed.

## Installation

1. Install **Woningwaarde** from the Home Assistant marketplace.
2. Restart Home Assistant.
3. Go to **Settings > Devices & services > Add integration** and choose **Woningwaarde**.
4. Enter a name, region, home type, a known value in euros and the date of that value.
5. Add the integration again for every additional home.

Use **Reconfigure** in the integration menu to change the name, region, home type, value or date later.

## How it works

The estimate is the known value multiplied by the price growth of the home type and the region (corrected for national growth) since the known date. Dates between quarterly index values are interpolated; after the latest publication the last observed trend is extended for at most four months, and the sensor attributes mark such values as a forecast.

The result is an indicative estimate, not an appraisal or an official WOZ value. Source data is cached for 24 hours.

See the [changelog](CHANGELOG.md) for release history.
