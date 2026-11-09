# Changelog

All notable tagged releases are listed here, newest first.

## [1.0.1b8] - 2026-11-05

- Added retries for CBS data and long-term statistics.
- Removed the legacy calculation choice and use date-based forecasts for all homes.

## [1.0.1b7] - 2026-10-23

- Use Home Assistant's local calendar date for valuations.
- Validate user-provided input.

## [1.0.1b6] - 2026-10-23

- Separate local refresh frequency from the hard daily CBS cache limit.

## [1.0.1b5] - 2026-10-22

- Add explicit date interpolation and forecasting.

## [1.0.1b4] - 2026-10-18

- Combine regional and national house-price growth by home type.

## [1.0.1b3] - 2026-10-18

- Make property values easier to recognize with a euro symbol and chart.

## [1.0.1b2] - 2026-10-18

- Add local integration branding for light and dark themes.

## [1.0.1b1] - 2026-10-18

- Rebuild the integration with UI setup, support for multiple homes, and a
  daily CBS cache.

## [0.2] - 2022-03-07

- Update sensor state attributes to use Home Assistant's `extra_state_attributes`.

## [0.1] - 2021-03-03

- Add version metadata to the integration manifest.
