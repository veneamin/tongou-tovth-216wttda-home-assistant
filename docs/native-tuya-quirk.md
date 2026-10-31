# Optional custom quirk for the native Tuya integration

This repository includes an optional custom quirk for the **Tongou TOVTH-216WTTDA Wi-Fi** device. It allows Home Assistant's built-in **Tuya** integration to create standard temperature and humidity sensor entities from the device's datapoints.

The quirk is independent of the `tuya_shower` YAML integration:

- **Native Tuya integration + this quirk:** exposes the current temperature and humidity as standard Tuya sensor entities.
- **`tuya_shower`:** provides cloud-based S1 threshold sensors and guarded threshold controls.
- The quirk does not add threshold controls and does not write to the device.

## Compatibility and tested environment

The quirk was tested on:

- Home Assistant Core 2026.10.4.
- `tuya-device-handlers` 0.0.31, included with that Home Assistant Core version.
- One physical Tongou TOVTH-216WTTDA Wi-Fi device.

Home Assistant logged that custom quirks were loaded, and the native Tuya integration created both measurement entities. The observed readings during verification were approximately 16.0–16.1 °C and 33–34% relative humidity.

Other Home Assistant versions, handler-library versions, firmware revisions, and device variants have not been verified. In particular, this file is **not** for the related TOVTH-216ZTTDA Zigbee model.

## Installation

1. Make sure the device has already been added through Home Assistant's built-in **Tuya** integration.
2. Create the custom quirks directory inside your Home Assistant configuration directory if it does not exist:

   ```text
   <config>/tuya_quirks/
   ```

3. Copy [`tuya_quirks/tongou_tovth216wttda.py`](../tuya_quirks/tongou_tovth216wttda.py) from this repository into that directory, preserving the filename:

   ```text
   <config>/tuya_quirks/tongou_tovth216wttda.py
   ```

4. Restart Home Assistant.
5. Check the Home Assistant log for the custom-quirk loader message, then open the device page and confirm that temperature and humidity entities have been created.

Home Assistant Core 2026.10.4 loads user quirks from the `tuya_quirks` directory under the configuration directory. This is a custom-quirk mechanism of the native Tuya integration; it is not an HACS integration and does not replace the Tuya integration.

## What the quirk changes

The quirk matches the exact product using its Tuya product ID, manufacturer, and model, then overrides its category to `wsdcg`. This reuses Home Assistant's built-in WSDCG sensor definitions.

It registers only these read-only measurement datapoints:

| DP ID | DP code | Meaning | Unit |
|---:|---|---|---|
| 27 | `temp_current` | Current temperature | °C |
| 46 | `humidity_value` | Relative humidity | % |

DP27 is reported in tenths of a degree by the tested device. DP46 is reported as a percentage. No relay, switch, operating-mode, or threshold datapoints are registered as writable by this quirk.

## Using it with tuya_shower

The quirk and `tuya_shower` can be installed together. Both can expose current temperature and humidity, so duplicate measurement entities may appear. Keep whichever pair you prefer and disable the redundant entities in Home Assistant if desired.

Use `tuya_shower` for the S1 lower/upper threshold sensors and controls. The quirk does not replace that functionality.

## Troubleshooting

- **No custom-quirk loader message:** check the directory name and file path. The file must be under `<config>/tuya_quirks/`, not inside `custom_components/`.
- **The device does not match:** verify that it is the Wi-Fi TOVTH-216WTTDA model. The quirk deliberately matches a specific product and should not be broadened to similar-looking models without evidence.
- **The entities exist but show `unknown`:** check whether the native Tuya integration is receiving device updates and inspect the Home Assistant log for Tuya errors. Entity creation alone does not prove that datapoint values are arriving.
- **A different firmware or handler version behaves differently:** report the Home Assistant Core version, handler-library version, device model, and relevant non-sensitive log messages when opening an issue. Never include Tuya client secrets, tokens, user IDs, or private device IDs.

See [device datapoints and evidence](device-datapoints.md) for the observed mapping and model-variant limitations.
