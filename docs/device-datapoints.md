# Tongou TOVTH-216WTTDA datapoints

This mapping is based on observation of one device in a Tuya Cloud account. Verify all mappings against your own hardware and firmware before writing anything.

## Observed datapoints

| DP | Code | Meaning in the tested S1 setup | Notes |
|---:|---|---|---|
| 2 | `switch_1` | Channel 1 switch | Do not write from this project |
| 22 | `temp_set` | S1 lower temperature threshold | The only lower-threshold write target |
| 27 | `temp_current` | Current temperature | Reported in tenths of a degree |
| 46 | `humidity_value` | Humidity | Percent |
| 104 | `automatic_mode_switch_1` | S1 automatic mode | Do not write |
| 105 | `automatic_mode_switch_2` | S2 automatic mode | Do not write |
| 106 | `relay_status` | Relay status | Read-only; do not write |
| 107 | `control_mode_1` | S1 control mode | Do not write |
| 110 | `temp_set_f_3` | S1 upper temperature threshold | The only upper-threshold write target |
| 122 | `temp_low_switch_1` | Lower threshold reached flag | Status only |
| 123 | `temp_high_switch_1` | Upper threshold reached flag | Status only |

The tested device reported DP 27 as an integer in tenths of a degree (for example, 164 = 16.4 °C). The two threshold datapoints use whole degrees Celsius.

## Hysteresis behavior observed

In the tested automatic S1 temperature mode, the relay turns on below the lower threshold, turns off above the upper threshold, and retains its prior state between the thresholds.

`temp_high_switch_1=false` means the upper threshold has not been reached; it does not mean the upper-threshold feature is disabled.

## Write safety rules

- Only DP 22 and DP 110 are write targets for temperature threshold control.
- Never send commands to relay, switch, automatic-mode, or control-mode datapoints.
- When increasing both thresholds, write and confirm DP 110 first, then DP 22.
- When decreasing both thresholds, write and confirm DP 22 first, then DP 110.
- Read back actual values from Tuya Cloud before assuming a write succeeded.
- The combined control preserves the current positive gap between thresholds. Its lower threshold range is 0 through `40 - gap`, keeping the upper threshold at or below 40 °C.

These rules describe the tested implementation, not a guarantee for every firmware revision.
