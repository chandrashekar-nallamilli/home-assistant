"""
Support for switching Almond+ binary switches.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.almond_plus/
"""
import logging
from homeassistant.components.switch import SwitchDevice
import custom_components.almond_plus as almond_plus

DOMAIN = "almond_plus"
DATA_ALMONDPLUS = "ALMONDPLUS"

_LOGGER = logging.getLogger(__name__)

#
# PIN_SCHEMA = vol.Schema({
#     vol.Required(CONF_NAME): cv.string,
#     vol.Optional(CONF_INITIAL, default=False): cv.boolean,
#     vol.Optional(CONF_NEGATE, default=False): cv.boolean,
# })
#
# PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
#     vol.Required(CONF_PINS, default={}):
#         vol.Schema({cv.positive_int: PIN_SCHEMA}),
# })


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Arduino platform."""
    return_value = False
    _LOGGER.debug("Started - find me 2")
    my_almond_plus = hass.data[DATA_ALMONDPLUS]
    switches = []
    _LOGGER.debug("looking for devices")
    for almond_entity in my_almond_plus.get_device_list:
        switches.append(AlmondPlusSwitch(almond_entity))
    add_devices(switches)
    return_value = True
    _LOGGER.debug("Setup ended with "+str(return_value))
    return return_value


class AlmondPlusSwitch(SwitchDevice):
    """Representation of an Arduino switch."""

    def __init__(self, device):
        self._id = device.id
        self._device_id = device.device_id
        self._name = device.name + '_' + device.id + '_' +  device.device_id
        self._state = ''
        self.value_value = device.value_value
        self._set_state(device.value_value)


    @property
    def name(self):
        """Get the name of the pin."""
        return self._name

    @property
    def id(self):
        """Get the name of the pin."""
        return self._id

    @property
    def device_id(self):
        """Get the name of the pin."""
        return self._device_id

    @property
    def is_on(self):
        """Return true if pin is high/on."""
        return self._state

    def turn_on(self, **kwargs):
        """Turn the pin to high/on."""
        self._state = 'on'

    def turn_off(self, **kwargs):
        """Turn the pin to low/off."""
        self._state = 'off'

    def _set_state(self, value_value):
        if value_value == "True":
            self._state = 'on'
        elif value_value == "False":
            self._state = 'off'
        else:
            self._state = 'unknown'
