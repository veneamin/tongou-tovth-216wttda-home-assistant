# Tongou TOVTH-216WTTDA — Home Assistant

Work in progress: community documentation and Home Assistant integration notes for the **Tongou TOVTH-216WTTDA** Wi-Fi temperature/humidity switch.

This repository documents a tested Home Assistant setup using Tuya Cloud. It is not an official Tongou, Tuya, or Home Assistant project.

## What this project adds

The exact Wi-Fi model already has a [merged device profile in tuya-local](https://github.com/make-all/tuya-local/blob/dcb0d40fa39f2dd2763fddbbb20b312683dc3d92/custom_components/tuya_local/devices/tongou_tovth216wttda_switch.yaml). That profile provides temperature, humidity, and two switch entities.

This project focuses on additional functionality observed and tested on one physical device:

- S1 lower and upper temperature threshold sensors.
- Independent lower and upper S1 threshold controls.
- A combined threshold control that preserves the current gap between lower and upper thresholds.
- Readback verification after writes.
- Safe command ordering to avoid crossing the two thresholds during updates.

The goal is to complement existing local integrations, not replace them.

## Project status

The initial implementation has been tested on one device and one Home Assistant installation. The current working setup uses Tuya Cloud for reading properties and writing the two S1 temperature thresholds.

The public integration is being prepared for reusable installation. Installation instructions, compatibility details, and independent Tuya Cloud authentication are still being developed.

## Safety

The documented implementation writes only:

- DP 22: `temp_set` — lower S1 threshold.
- DP 110: `temp_set_f_3` — upper S1 threshold.

It does not write relay, channel switch, operating-mode, or automatic-mode datapoints. Do not copy private device identifiers, Tuya credentials, tokens, or account identifiers into configuration files or issue reports.

## Device variants and related projects

- **TOVTH-216WTTDA (Wi-Fi):** this repository's target model. See the [merged tuya-local profile](https://github.com/make-all/tuya-local/pull/4785) for its temperature, humidity, and switch datapoints.
- **TOVTH-216ZTTDA (Zigbee):** a related but different variant discussed in [zha-device-handlers issue #5036](https://github.com/zigpy/zha-device-handlers/issues/5036). Its Zigbee datapoints must not be assumed to match the Wi-Fi model.

## Documentation

- [Device datapoints, evidence, and implementation notes](docs/device-datapoints.md)
- [Installation](docs/installation.md) — planned
- [Troubleshooting](docs/troubleshooting.md) — planned

## Disclaimer

This is an independent community project. Hardware behavior and datapoint mappings may vary by firmware, product variant, Tuya region, and cloud API behavior. Verify the datapoints for your own device before enabling writes.
