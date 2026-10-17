# Changelog

## [1.4.1] - 2026-10-18

- HACS validation runs with no checks disabled; the brand images in the integration pass the brands check.

## [1.4.0] - 2026-10-18

- Anonymous daily usage statistics to stats.rnet.se (on by default, switch it off under Configure). Sends the appliance models and their count, never names or rooms.
- Options flow, Swedish translation.
- Manifest: code owner and integration type; HACS minimum Home Assistant 2024.11.
- GitHub Releases: pushing a tag `vX.Y.Z` matching the manifest creates the release HACS installs from.

## [1.3.0] - 2026-10-06

- Last known appliance values are kept across Home Assistant restarts.
- Miele brand icon and logo.

## [1.2.0] - 2026-10-06

- Up to 3 missed gateway polls in a row keep the last data; timeouts are handled.
- An appliance that leaves the powerline bus while off keeps its last values; one that leaves mid-program goes unavailable after 10 minutes.
- -30 °C (no reading) is shown as unknown.

## [1.1.1] - 2026-10-06

- Sensors and buttons are added when appliances and actions appear, not only at setup.

## [1.1.0] - 2026-10-06

- Reads the value names a real XGW 2000 sends (State, Phase, Remaining Time, ...).
- New oven sensors: duration, cooking function, temperature, core temperature.

## [1.0.0] - 2026-09-10

- First release.
