"""
For more details about this platform, please refer to the documentation
https://home-assistant.io/components/cover/almond_plus
"""

import logging
import requests
import traceback
import datetime

from homeassistant.components.cover import (
    CoverDevice, PLATFORM_SCHEMA, SUPPORT_OPEN, SUPPORT_CLOSE, STATE_OPENING, STATE_CLOSING)
from homeassistant.const import (STATE_UNKNOWN, STATE_CLOSED, STATE_OPEN)

_LOGGER = logging.getLogger(__name__)

DOMAIN = "almond_plus"
DATA_ALMONDPLUS = "ALMONDPLUS"


def setup_platform(hass, config, add_devices, discovery_info=None):
    global my_almond_plus
    return_value = False
    try:
        _LOGGER.debug("Started - find me 3")
        my_almond_plus = hass.data[DATA_ALMONDPLUS]["almondplus_api"]
        covers = []
        _LOGGER.debug("looking for devices (cover)")
        for almond_key, almond_entity in my_almond_plus.get_device_list().items():
            _LOGGER.debug("Device Name (cover) "+almond_entity.name+" type "+almond_entity.type)
            if almond_entity.type == "53":
                tmp = AlmondPlusCover(almond_entity)
                _LOGGER.debug("Device - Str (cover)"+str(tmp))
                _LOGGER.debug("Device - (cover)" + tmp.id + ", " + tmp.device_id + ", " + tmp.state + ", " + tmp.name)
                covers.append(tmp)
        if len(covers) > 0:
            add_devices(covers)
            hass.data[DATA_ALMONDPLUS]["almondplus_cover_entities"] = covers
        return_value = True
    except Exception as e:
        _LOGGER.error("Error\n"
                      + "**************************\n"
                      + str(e) + "\n"
                      + traceback.format_exc()
                      + "**************************")
    _LOGGER.debug("Setup ended with " + str(return_value))
    return return_value


#               "4":{
#                   "Data":{
#                         "ID":"4",
#                         "Name":"GarageDoorOpener Two Car",
#                         "FriendlyDeviceType":"GarageDoorOpener",
#                         "Type":"53",
#                         "Location":"Default",
#                         "LastActiveEpoch":"1531243088",
#                         "Model":"Unknown: type=4744,",
#                         "Version":"0",
#                         "Manufacturer":"Linear"
#                         },
#                   "DeviceValues":{
#                                   "1":{
#                                       "Name":"BARRIER OPERATOR",
#                                       "Value":"0",
#                                       "Type":"44"
#                                       }
#                                 }
#                   }


class AlmondPlusCover(CoverDevice):
    """Representation of a Almond+ cover."""

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
        self._state_before_move = None
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
        """Return the name of the cover."""
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
    def should_poll(self):
        return False

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
        if value_value.lower() == "0":
            self._state = STATE_CLOSED
            _LOGGER.debug("Setting closed "+self._state)
        elif value_value.lower() == "255":
            self._state = STATE_OPEN
            _LOGGER.debug("Setting open "+self._state)
        elif value_value.lower() == "254":
            self._state = STATE_OPENING
            _LOGGER.debug("Setting opening " + self._state)
        elif value_value.lower() == "252":
            self._state = STATE_CLOSING
            _LOGGER.debug("Setting closing " + self._state)
        else:
            self._state = 'unknown'
            _LOGGER.debug("Setting unknown " + self._state)
        _LOGGER.debug("Setting State Finish "+self._state)

    @property
    def is_opening(self):
        """Return if the cover is opening."""
        if self._state in [STATE_UNKNOWN]:
            return None
        return self._state in [STATE_OPENING]

    @property
    def is_closing(self):
        """Return if the cover is closing."""
        if self._state in [STATE_UNKNOWN]:
            return None
        return self._state in [STATE_CLOSING]

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        if self._state in [STATE_UNKNOWN]:
            return None
        return self._state in [STATE_CLOSED, STATE_OPENING]

    def close_cover(self, **kwargs):
        """Close the cover."""
        if self._state not in [STATE_CLOSED, STATE_CLOSING]:
            _LOGGER.debug("Close Cover")
            self._state_before_move = self._state
            my_almond_plus.set_device(self.id, self.device_id, "0")

    def open_cover(self, **kwargs):
        """Open the cover."""
        if self._state not in [STATE_OPEN, STATE_OPENING]:
            _LOGGER.debug("Open Cover")
            self._state_before_move = self._state
            my_almond_plus.set_device(self.id, self.device_id, "255")

    def update(self, device):
        _LOGGER.debug("Switch Update -"+self._id+"-"+self.device_id+"-")
        self._update_properties(device)
        self.schedule_update_ha_state()

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_OPEN | SUPPORT_CLOSE
