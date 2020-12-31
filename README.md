# Weather ratings
This platform scrapes the weather ratings of a few activities from weeronline.nl. It creates the folowing sensors:

- sensor.weatherratings 

The sensors are updated daily since the data is based on daily gas consumption.

## HACS Installation
1. Make sure you've installed [HACS](https://hacs.xyz/docs/installation/prerequisites)
2. In the integrations tab, search for weatherratings.
3. Install the Integration.
4. Add weatherratings entry to configuration (see below)


## Configuration
```yaml
sensor:
  - platform: weatherratings
    url: url
    name: name
```
