# Woningwaarde
This platform scrapes the actual price of a house from berekenhet.nl. It creates the folowing sensor:

- sensor.woningwaarde

The sensors are updated daily since the data is based on daily gas consumption.

## HACS Installation
1. Make sure you've installed [HACS](https://hacs.xyz/docs/installation/prerequisites)
2. In the integrations tab, search for woningwaarde.
3. Install the Integration.
4. Add woningwaarde entry to configuration (see below and https://www.berekenhet.nl/wonen-en-hypotheek/woning-waarde-huizenprijzen.html)


## Configuration
```yaml
sensor:
  - platform: woningwaarde
    name: <<NAME OF SENSOR>>
    type: <<SOORT WONING>>
    region: <<PROVINCIE OF GEMEENTE>>
    waarde: <<BEKENDE PRIJS OF WAARDE>>
    datum: <<DATUM BEKENDE PRIJS OF WAARDE>>
```
