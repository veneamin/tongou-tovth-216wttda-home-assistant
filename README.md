# Tongou TOVTH-216WTTDA — Home Assistant

Work in progress: community documentation and Home Assistant integration notes for the **Tongou TOVTH-216WTTDA** Wi-Fi temperature/humidity switch.

This repository documents a tested Home Assistant setup using Tuya Cloud. It is not an official Tongou, Tuya, or Home Assistant project.

## Project status

The initial implementation has been tested on one device and one Home Assistant installation. The current working setup provides:

- Temperature and humidity sensors from Tuya Cloud.
- Independent lower and upper S1 temperature threshold controls.
- A combined threshold control that preserves the current gap between lower and upper thresholds.
- Readback verification after writes.
- Safe command ordering to avoid crossing the two thresholds during updates.

The integration is being prepared for public, reusable installation. Installation instructions and compatibility details are still being expanded.

## Safety

The controller exposes multiple datapoints. The documented implementation writes only:

- DP 22: `temp_set` — lower S1 threshold.
- DP 110: `temp_set_f_3` — upper S1 threshold.

It must not write relay, channel switch, operating mode, or automatic-mode datapoints. Do not copy private device identifiers, Tuya credentials, tokens, or account identifiers into configuration files or issue reports.

## Documentation

- [Device datapoints and implementation notes](docs/device-datapoints.md)
- [Installation](docs/installation.md) — planned
- [Troubleshooting](docs/troubleshooting.md) — planned

## Disclaimer

This is an independent community project. Hardware behavior and datapoint mappings may vary by firmware, product variant, Tuya region, and cloud API behavior. Verify the datapoints for your own device before enabling writes.
