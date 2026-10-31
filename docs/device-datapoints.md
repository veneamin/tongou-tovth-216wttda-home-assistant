# Tongou TOVTH-216WTTDA datapoints

This mapping combines three kinds of evidence. They are kept separate because similarly named Tongou devices may use different transports and datapoint layouts:

1. **Observed Tuya Cloud properties and commands** from one TOVTH-216WTTDA device used to develop and test this project.
2. **The merged tuya-local device profile** for the exact Wi-Fi model TOVTH-216WTTDA.
3. **A community Zigbee2MQTT converter** posted in a support discussion for the related Zigbee model TOVTH-216ZTTDA. This is reference material only; its datapoint IDs must not be applied to the Wi-Fi model.

Always verify mappings against your own hardware, firmware, and transport before enabling writes.

## Exact Wi-Fi model: tuya-local profile

The [tuya-local profile](https://github.com/make-all/tuya-local/blob/dcb0d40fa39f2dd2763fddbbb20b312683dc3d92/custom_components/tuya_local/devices/tongou_tovth216wttda_switch.yaml) identifies:

- Manufacturer: Tongou
- Model: TOVTH-216WTTDA
- Product ID: `oj6soirdngp9jijy`

The profile was contributed in [tuya-local PR #4785](https://github.com/make-all/tuya-local/pull/4785), which was merged on 2026-04-01.

| Tuya datapoint ID | Entity in tuya-local | Meaning |
|---:|---|---|
| 27 | Temperature sensor | Current temperature, integer scaled by 10 |
| 46 | Humidity sensor | Current relative humidity, percent |
| 2 | Switch 1 | Channel 1 switch |
| 101 | Switch 2 | Channel 2 switch |

This profile documents two sensors and two switches. It does **not** document the S1 temperature-threshold controls implemented by this project.

The temperature and humidity IDs (27 and 46) agree with the values observed through Tuya Cloud on the device used for this project. The switch mapping is documented by tuya-local; this project does not currently expose or write those switch datapoints.

## Cloud properties observed on the tested device

The following property codes and meanings were observed through Tuya Cloud on one TOVTH-216WTTDA device.

| DP ID | Cloud property code | Meaning in the tested S1 setup | Notes |
|---:|---|---|---|
| 22 | `temp_set` | S1 lower temperature threshold | The only lower-threshold write target |
| 27 | `temp_current` | Current temperature | Integer in tenths of a degree |
| 46 | `humidity_value` | Humidity | Percent |
| 104 | `automatic_mode_switch_1` | S1 automatic mode | Do not write |
| 105 | `automatic_mode_switch_2` | S2 automatic mode | Do not write |
| 106 | `relay_status` | Relay status | Read-only; do not write |
| 107 | `control_mode_1` | S1 control mode | Do not write |
| 110 | `temp_set_f_3` | S1 upper temperature threshold | The only upper-threshold write target |
| 122 | `temp_low_switch_1` | Lower threshold reached flag | Status only |
| 123 | `temp_high_switch_1` | Upper threshold reached flag | Status only |

The tested device reported DP 27 as an integer in tenths of a degree (for example, 164 = 16.4 °C). The two S1 threshold properties use whole degrees Celsius.

The numeric IDs in this table are the IDs associated with the cloud properties observed on this particular device. Do not assume that a numeric ID, a cloud property code, and a Zigbee datapoint number are interchangeable across transports or model variants.

## Hysteresis behavior observed

In the tested automatic S1 temperature mode, the relay turns on below the lower threshold, turns off above the upper threshold, and retains its prior state between the thresholds.

`temp_high_switch_1=false` means the upper threshold has not been reached; it does not mean the upper-threshold feature is disabled.

## Write safety rules

- This project's threshold controls write only DP 22 (`temp_set`) and DP 110 (`temp_set_f_3`).
- Never send commands to relay, switch, automatic-mode, or control-mode datapoints from this project's threshold controls.
- When increasing both thresholds, write and confirm DP 110 first, then DP 22.
- When decreasing both thresholds, write and confirm DP 22 first, then DP 110.
- Read back actual values from Tuya Cloud before assuming a write succeeded.
- The combined control preserves the current positive gap between thresholds. Its lower threshold range is 0 through `40 - gap`, keeping the upper threshold at or below 40 °C.

These rules describe the tested implementation, not a guarantee for every firmware revision.

## Related Zigbee model: TOVTH-216ZTTDA

[zha-device-handlers issue #5036](https://github.com/zigpy/zha-device-handlers/issues/5036) is a support request for **TOVTH-216ZTTDA**, identified as manufacturer `_TZE284_6uyu20xu` and model `TS0601`. The report says ZHA exposed only basic link information and did not expose the two dry contacts or the temperature/humidity sensors.

A commenter posted a community Zigbee2MQTT converter and reported that it worked for their device. The converter describes a much larger set of datapoints, including two switches, temperature and humidity readings, calibration, automatic modes, and temperature/humidity thresholds.

This is a different, Zigbee model variant. Its datapoint IDs and converter are **not** a specification for TOVTH-216WTTDA Wi-Fi devices and are not used by this integration.

## Related Home Assistant projects

- [tuya-local](https://github.com/make-all/tuya-local) — local Tuya device support. Its merged profile for TOVTH-216WTTDA already exposes the two sensors and two switches listed above.
- [zha-device-handlers issue #5036](https://github.com/zigpy/zha-device-handlers/issues/5036) — support discussion for the related TOVTH-216ZTTDA Zigbee variant.

This project focuses on the additional cloud-based S1 threshold monitoring and guarded threshold control documented above. It is not intended to replace tuya-local or Zigbee integrations.

## Evidence and limitations

- The Tuya Cloud property mapping and S1 threshold behavior are based on one physical Wi-Fi device.
- The tuya-local mapping is taken from its merged device profile for the exact Wi-Fi model.
- The Zigbee2MQTT converter is a user-contributed example for a different Zigbee model variant.
- No claim is made that every firmware revision or hardware variant exposes the same properties.
