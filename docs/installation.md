# Installation and configuration

This integration targets the **Tongou TOVTH-216WTTDA Wi-Fi** temperature/humidity switch. It is not a configuration for the related Zigbee model.

## Requirements

- Home Assistant with YAML platform support.
- A Tuya Cloud project/account with API access to the device.
- The device ID and the four Tuya Cloud credentials listed below.
- No LocalTuya installation is required when credentials are configured directly.

## Install the integration

1. Copy the custom_components/tuya_shower directory from this repository into the Home Assistant configuration directory:

   ~~~text
   <config>/custom_components/tuya_shower/
   ~~~

2. Restart Home Assistant.
3. Add the credentials to secrets.yaml.
4. Add the sensor and number platforms to configuration.yaml.

## Store credentials in secrets.yaml

Use the credentials associated with the Tuya Cloud project and user that can access your device. Do not commit secrets.yaml or paste credential values into issue reports.

~~~yaml
tuya_shower_client_id: "YOUR_TUYA_CLIENT_ID"
tuya_shower_client_secret: "YOUR_TUYA_CLIENT_SECRET"
tuya_shower_user_id: "YOUR_TUYA_USER_ID"
tuya_shower_region: "eu"
~~~

The region must match the Tuya data center where the project/device is registered. Supported region codes in the current client are:

| Region code | Tuya data center |
|---|---|
| cn | China |
| eu | Central Europe |
| ea | Eastern America |
| us | Western America |
| we | Western Europe |
| in | India |
| sg | Singapore |

Do not select a region based only on your physical location; use the data center configured for your Tuya Cloud project.

## Configure configuration.yaml

The device ID is not a secret in the same way as the API secret, but it should still be treated as account/device metadata. The following example uses !secret for the four credentials.

~~~yaml
sensor:
  - platform: tuya_shower
    device_id: YOUR_TUYA_DEVICE_ID
    client_id: !secret tuya_shower_client_id
    client_secret: !secret tuya_shower_client_secret
    user_id: !secret tuya_shower_user_id
    region: !secret tuya_shower_region

number:
  - platform: tuya_shower
    device_id: YOUR_TUYA_DEVICE_ID
    client_id: !secret tuya_shower_client_id
    client_secret: !secret tuya_shower_client_secret
    user_id: !secret tuya_shower_user_id
    region: !secret tuya_shower_region
~~~

Both platforms need the same connection settings because Home Assistant loads them independently.

## Existing LocalTuya installations

For backward compatibility, if none of the four credential keys is supplied in a platform block, the integration can read the existing client_id, client_secret, user_id, and region values from a LocalTuya config entry.

Explicit Tuya Shower YAML credentials always take precedence. If only some of the four values are configured, setup is stopped with an error rather than silently falling back to LocalTuya.

New installations should configure the credentials directly as shown above. LocalTuya is not a manifest dependency.

## Entities and datapoint safety

The integration exposes four sensors and three number controls:

- Current temperature and humidity.
- S1 lower and upper temperature thresholds.
- Independent lower and upper threshold controls.
- A combined slider that preserves the existing positive gap between thresholds.

Only the S1 threshold datapoints are writable:

- DP 22 / temp_set: lower threshold.
- DP 110 / temp_set_f_3: upper threshold.

The integration does not write relay, switch, automatic-mode, or control-mode datapoints. Each threshold write is followed by a cloud readback check. The combined slider orders the two writes to avoid crossing the thresholds. Its lower-bound control range is recalculated from the current hysteresis gap (`0` to `40 - gap`). When either independent threshold control is changed, the integration immediately rereads both cloud values and updates the combined slider's maximum. For example, a 2 °C gap permits a lower threshold up to 38 °C; a 3 °C gap permits up to 37 °C.

See [device datapoints and evidence](device-datapoints.md) for the observed mapping, limitations, and model-variant distinctions.

## Optional native Tuya sensors

If the device is added through Home Assistant's built-in Tuya integration, you can optionally install the custom quirk in [native-tuya-quirk.md](native-tuya-quirk.md). It exposes current temperature and humidity through native Tuya entities; it does not expose S1 threshold controls.

The quirk can be used alongside `tuya_shower`, but both integrations may then create temperature and humidity entities. Disable whichever duplicate entities you do not need.

## Validation

After editing YAML, run the Home Assistant configuration check before restarting. Confirm that the four `tuya_shower` sensors and three number entities receive values from the device. When testing the controls, change one independent threshold and verify that the combined slider's maximum changes to match the new gap.

The datapoint mapping and threshold behavior have been tested on one physical TOVTH-216WTTDA Wi-Fi device. Other firmware revisions and product variants may behave differently.


## S1 automatic-mode switch

A YAML switch platform is available for the S1 automatic temperature mode. Add the following block using the same device ID and credential references as the sensor and number platforms:

~~~yaml
switch:
  - platform: tuya_shower
    device_id: YOUR_TUYA_DEVICE_ID
    client_id: !secret tuya_shower_client_id
    client_secret: !secret tuya_shower_client_secret
    user_id: !secret tuya_shower_user_id
    region: !secret tuya_shower_region
~~~

The switch writes only DP 104 (automatic_mode_switch_1). On the tested physical device, OFF disabled the heating output and ON restored automatic S1 temperature regulation. The switch does not change DP 2, DP 107, S2, or either threshold. It performs one write at most, then up to three read-only checks at two-second intervals. It polls the current value every 30 seconds. An uncertain write is not automatically retried.

The source implementation has not yet been installed or tested in the running Home Assistant instance. Validate the YAML and confirm the entity state before using it. Any physical on/off test must be explicitly initiated by the device owner.
