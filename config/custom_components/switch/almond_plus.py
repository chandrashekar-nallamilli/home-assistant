"""
Support for switching Almond+ binary switches.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.almond_plus/
"""
import logging
from homeassistant.components.switch import SwitchDevice
import datetime
import  traceback

DOMAIN = "almond_plus"
DATA_ALMONDPLUS = "ALMONDPLUS"

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices, discovery_info=None):
    return_value = False
    try:
        _LOGGER.debug("Started - find me 2")
        my_almond_plus = hass.data[DATA_ALMONDPLUS]["almondplus_api"]
        switches = []
        _LOGGER.debug("looking for devices")
        for almond_key, almond_entity in my_almond_plus.get_device_list().items():
            if almond_entity.value_type == "1":
                tmp = AlmondPlusSwitch(almond_entity)
                _LOGGER.debug("Device -"+tmp.id+", "+tmp.device_id+", "+tmp.state+", "+tmp.name)
                switches.append(tmp)
            #switches.append(AlmondPlusSwitch(almond_entity))
        if len(switches) > 0:
            add_devices(switches)
            hass.data[DATA_ALMONDPLUS]["almondplus_switch_entities"] = switches

        return_value = True
    except Exception as e:
        _LOGGER.error("Error\n"
                      + "**************************\n"
                      + str(e) + "\n"
                      + traceback.format_exc()
                      + "**************************")
    _LOGGER.debug("Setup ended with " + str(return_value))
    return return_value


class AlmondPlusSwitch(SwitchDevice):
    """Representation of an Almond+ switch."""

    def __init__(self, device):
        self._id = None
        self._device_id = None
        self._name = None
        self._state = None

        """Attributes"""
        self.friendly_device_type = None
        self.type = None
        self.location = None
        self.last_active_epoch = None
        self.model = None
        self.value_name = None
        self.value_value = None
        self.value_type = None
        self._update_properties(device)

    def _update_properties(self, device):
        self._id = device.id
        self._device_id = device.device_id
        self._name = DOMAIN+"_"+device.name + '_' + device.id + '_' + device.device_id
        self._state = ''
        self.set_state(device.value_value)

        """Attributes"""
        self.friendly_device_type = device.friendly_device_type
        self.type = device.type
        self.location = device.location
        self.last_active_epoch = device.last_active_epoch
        self.model = device.model
        self.value_name = device.value_name
        self.value_value = device.value_value
        self.value_type = device.value_type

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
        _LOGGER.debug("is_on "+self.name+"-"+self._state)
        return self._state == "on"

    @property
    def should_poll(self):
        return False

    def turn_on(self, **kwargs):
        """Turn the pin to high/on."""
        _LOGGER.debug("Turn on")
        self._state = 'on'

    def turn_off(self, **kwargs):
        """Turn the pin to low/off."""
        _LOGGER.debug("Turn off")
        self._state = 'off'

    @property
    def device_state_attributes(self):
        """Return the optional state attributes."""
        data = {}
        data["id"] = self._id
        data["device_id"] = self._device_id
        data["friendly_device_type"] = self.friendly_device_type
        data["type"] = self.type
        data["location"] = self.location
        data["last_active_epoch"] = self.last_active_epoch
        data["last_active_datetime"] = datetime.datetime.fromtimestamp(int(self.last_active_epoch))
        data["model"] = self.model
        data["value_name"] = self.value_name
        data["value_value"] = self.value_value
        data["value_type"] = self.value_type
        return data

    def update(self, device):
        _LOGGER.debug("Switch Update -"+self._id+"-"+self.device_id+"-")
        self._update_properties(device)
        self.schedule_update_ha_state()

    def set_state(self, value_value):
        _LOGGER.debug("Setting State -"+value_value+"-"+value_value.lower()+"-")
        if value_value.lower() == "true":
            self._state = 'on'
            self.turn_on()
            _LOGGER.debug("Setting on "+self._state)
        elif value_value.lower() == "false":
            self._state = 'off'
            self.turn_off()
            _LOGGER.debug("Setting off "+self._state)
        else:
            self._state = 'unknown'
            _LOGGER.debug("Setting unknown " + self._state)
        _LOGGER.debug("Setting State Finish "+self._state)
