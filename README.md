# Woningwaarde

Woningwaarde is a Home Assistant integration that estimates the value of your home from the public CBS/Kadaster house price index (Prijsindex Bestaande Koopwoningen). No API key is needed.

## Installation

Woningwaarde is a custom component and is installed directly from the Home Assistant marketplace. You do not need to download or copy any files yourself.

1. Open the marketplace in Home Assistant and add `https://github.com/nelbs/woningwaarde` as a custom component (custom repository) of type **Integration**.
2. Search for **Woningwaarde** in the marketplace and install it.
3. Restart Home Assistant.
4. Go to **Settings > Devices & services**, select **Add integration** and search for **Woningwaarde**.
5. Follow the setup steps described under Configuration.

## Configuration

Setup and changes are done in the Home Assistant interface; no YAML is needed. You provide:

| Field | Description |
| --- | --- |
| House ID | A unique and permanent identifier for the home, for example `thuis`. It cannot be changed later. |
| Name | The name of the home. It is used for the device and the sensor. |
| Known value (EUR) | A value of the home you already know, for example a purchase price or WOZ value. It must be positive. |
| Reference date | The date the known value applies to, from 1995 up to and including today. |
| Province or municipality | The Netherlands, one of the twelve provinces, or Amsterdam, Den Haag, Rotterdam or Utrecht. For other municipalities, choose the province. |
| House type | All house types, terraced house (tussenwoning), corner house (hoekwoning), semi-detached (twee onder een kap), detached (vrijstaand), apartment, or family home (eengezinswoning). |

To change these values later, use **Reconfigure** in the integration menu. The house ID stays the same.

### Multiple homes

You can add multiple homes. Select **Add integration > Woningwaarde** again for every home and give each one its own house ID. Every home gets its own device and sensor, and names and values may be identical.

## How it works

The estimate is the known value multiplied by the price growth of the house type and the region (corrected for national growth) since the reference date. Dates between quarterly index values are interpolated. After the latest publication, the last observed trend is extended for at most four months; the sensor attributes mark such values as a forecast.

The result is an indicative estimate, not an appraisal or an official WOZ value.

## Polling

The integration polls cloud data from CBS and keeps the number of requests low:

- Every home recalculates its value locally once per hour from stored data. This does not mean a request is made every hour.
- CBS data is cached on disk for 24 hours and shared by all homes, also across restarts and manual updates. Additional homes do not cause additional requests.
- If a request fails, the same data may be requested again after five minutes. Meanwhile the sensor is unavailable instead of showing an outdated value.
- Requests have a time-out of 30 seconds each and 60 seconds in total. No names, addresses or values are sent to CBS.

The sensor attributes `last_checked` and `source_cache` show the last local calculation and the last and next allowed request per table.

See the [changelog](CHANGELOG.md) for release history.
