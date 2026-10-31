# Tongou TOVTH-216WTTDA — Home Assistant

Community documentation and a Home Assistant YAML integration for the **Tongou TOVTH-216WTTDA** Wi-Fi temperature/humidity switch.

This is not an official Tongou, Tuya, or Home Assistant project.

## What this project adds

The exact Wi-Fi model already has a [merged device profile in tuya-local](https://github.com/make-all/tuya-local/blob/dcb0d40fa39f2dd2763fddbbb20b312683dc3d92/custom_components/tuya_local/devices/tongou_tovth216wttda_switch.yaml). That profile provides temperature, humidity, and two switch entities.

This project focuses on additional functionality observed and tested on one physical device:

- S1 lower and upper temperature threshold sensors.
- Independent lower and upper S1 threshold controls.
- A combined threshold control that preserves the current gap between lower and upper thresholds.
- Readback verification after writes.
- Safe command ordering to avoid crossing the two thresholds during updates.
- A self-contained Tuya Cloud API client; LocalTuya is optional and is not a dependency.

An **optional custom quirk** is also provided for Home Assistant's built-in Tuya integration. It exposes the device's current temperature and humidity as standard Tuya sensor entities. It does not provide threshold controls; those remain part of `tuya_shower`.

## Project status

The `tuya_shower` integration has been tested on one physical TOVTH-216WTTDA Wi-Fi device and one Home Assistant installation (Core 2026.10.4). Reading, independent threshold writes, combined threshold movement, readback confirmation, restoration of the original thresholds, and dynamic slider-bound updates after hysteresis changes have been tested. The eight offline unit tests also pass.

The optional native-Tuya quirk was also tested on the same Home Assistant Core version with `tuya-device-handlers` 0.0.31. It loaded successfully and the native Tuya integration created temperature and humidity entities that received live readings. This quirk has only been tested on one physical device.

The integration can use its own Tuya Cloud credentials from Home Assistant YAML and secrets.yaml. Existing installations can temporarily continue using credentials stored by LocalTuya.

The implementation is intended for community testing. Hardware behavior and cloud datapoints may vary by firmware, product variant, and Tuya region.

## Installation

- [Installation and configuration for tuya_shower](docs/installation.md)
- [Optional custom quirk for the native Tuya integration](docs/native-tuya-quirk.md)

## Safety

The `tuya_shower` implementation writes only:

- DP 22: temp_set — lower S1 threshold.
- DP 110: temp_set_f_3 — upper S1 threshold.

It does not write relay, channel switch, operating-mode, or automatic-mode datapoints. The optional native Tuya quirk registers only read-only temperature and humidity measurements. Do not copy private device identifiers, Tuya credentials, tokens, or account identifiers into configuration files committed to Git or issue reports.

## Device variants and related projects

- **TOVTH-216WTTDA (Wi-Fi):** this repository's target model. See the [merged tuya-local profile](https://github.com/make-all/tuya-local/pull/4785) for its temperature, humidity, and switch datapoints.
- **TOVTH-216ZTTDA (Zigbee):** a related but different variant discussed in [zha-device-handlers issue #5036](https://github.com/zigpy/zha-device-handlers/issues/5036). Its Zigbee datapoints must not be assumed to match the Wi-Fi model.

## Documentation

- [Installation and configuration](docs/installation.md)
- [Native Tuya custom quirk](docs/native-tuya-quirk.md)
- [Device datapoints, evidence, and implementation notes](docs/device-datapoints.md)

## Disclaimer

This is an independent community project. The cloud property mapping and S1 threshold behavior are based on one physical Wi-Fi device. Verify the datapoints for your own hardware and firmware before enabling writes.
