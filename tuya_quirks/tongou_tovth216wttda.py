"""Custom quirk for the Tongou TOVTH-216WTTDA Wi-Fi thermostat.

The device reports temperature and humidity using datapoints 27 and 46.
Its Tuya category is overridden to WSDCG so Home Assistant's built-in
Tuya integration exposes the measurements as standard sensor entities.

Only read-only measurement datapoints are defined here. Threshold controls
remain managed separately by the tuya_shower custom integration.
"""

from tuya_device_handlers import TUYA_QUIRKS_REGISTRY
from tuya_device_handlers.builder import DeviceQuirk
from tuya_device_handlers.const import DPMode


(
    DeviceQuirk()
    # Match only this exact Tuya product; do not affect other TDQ devices.
    .applies_to(
        product_id="oj6soirdngp9jijy",
        manufacturer="Tongou",
        model="TOVTH-216WTTDA",
    )
    # Reuse the built-in WSDCG sensor definitions in Home Assistant.
    .override_category("wsdcg")
    # DP27 reports temperature in tenths of a degree Celsius (e.g. 164 = 16.4 °C).
    .add_dpid_integer(
        dpid=27,
        dpcode="temp_current",
        dpmode=DPMode.READ,
        unit="℃",
        min=-400,
        max=1000,
        scale=1,
        step=1,
    )
    # DP46 reports relative humidity as an integer percentage.
    .add_dpid_integer(
        dpid=46,
        dpcode="humidity_value",
        dpmode=DPMode.READ,
        unit="%",
        min=0,
        max=100,
        scale=0,
        step=1,
    )
    .register(TUYA_QUIRKS_REGISTRY)
)
