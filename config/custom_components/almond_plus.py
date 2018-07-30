"""
Support for Almond+.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/almond_plus/
"""
import logging
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.discovery import load_platform

# -*- coding: utf-8 -*-
import threading
import websocket
import uuid
import json
import time
import traceback

REQUIREMENTS = ['websocket-client']

_LOGGER = logging.getLogger(__name__)


DOMAIN = "almond_plus"
DATA_ALMONDPLUS = "ALMONDPLUS"
CONF_URL = "url"


CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_URL): cv.string,
    }),
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config):
    """Set up the Almond+ component."""
    return_status = False
    try:
        global myhass_data
        myhass_data = {}
        myhass_data["config"] = config[DOMAIN]
        connect_url = config[DOMAIN][CONF_URL]
        myhass_data["almondplus_api"] = AlmondPlus(connect_url, almond_plus_call_back)
        myhass_data["almondplus_switch_entities"] = None
        hass.data[DATA_ALMONDPLUS] = myhass_data
        hass.data[DATA_ALMONDPLUS]["almondplus_api"].start()
        time.sleep(2)
        _LOGGER.debug("Test Almond+ setup: "+str(hass.data[DATA_ALMONDPLUS]["almondplus_api"].get_device_list()))
        _LOGGER.debug("Loading switch platform")
        load_platform(hass, 'switch', DOMAIN, discovered=None, hass_config=None)
        time.sleep(2)
        switches = sorted(hass.states.async_entity_ids('switch'))
        _LOGGER.debug("switch list 1: "+str(switches))
        tmp_switches = myhass_data["almondplus_switch_entities"]
        _LOGGER.debug("switch list 2: "+str(tmp_switches))
        return_status = True
    except Exception as e:
        _LOGGER.error("Error\n"
                      +"**************************\n"
                      + str(e) + "\n"
                      + traceback.format_exc()
                      + "**************************")
    _LOGGER.debug("Setup ended with "+str(return_status))
    return return_status


def almond_plus_call_back(almond_entities):
    tmp_switches = myhass_data["almondplus_switch_entities"]
    tmp_almond_entities = myhass_data["almondplus_api"].get_device_list()
    for almond_key, almond_entity in almond_entities.items():
        _LOGGER.debug("id: "+almond_entity.id+" device_id: "
                      + almond_entity.device_id+" value: "
                      + almond_entity.value_value)
        tmp_id = almond_entity.id
        tmp_device_id = almond_entity.device_id
        tmp_key = tmp_id.zfill(4) + tmp_device_id.zfill(4)
        """
        First check through switches
        """
        for switch_entity in tmp_switches:
            if switch_entity.id == tmp_id and switch_entity.device_id == tmp_device_id:
                switch_entity.update(tmp_almond_entities[tmp_key])


def stop_almond_plus(event):
    pass


def start_almond_plus(event):
    pass


class AlmondPlus:
    """
    This class will be the API for Almond+
    For now I am including it in the hass component for connivance debugging.
    Once finished it will be moved to it's own lib as pre hass guidelines
    Also the hass specific debug statements will be removed.
    """

    def __init__(self, api_url, call_back=None):
        """
        The init of the Almond+ Setup global vars and start a thread to receive on
        :param api_url:
            The URL to connect to the Almond+
        :param call_back:
            A reference to function that when an unsolicited received (a received that was
                not in response to a send) will build a dict and return it of
                device id, device_id, value
        """
        self.api_url = api_url
        self.ws = None
        self.call_back = call_back
        self.receive_task = None
        self.last_dym_upate = ""
        self.keep_running = True
        self.client_running = False
        self.send_receive = {}
        self.entity_dict = None
        t = threading.Thread(target=self.api_dispatcher, args=())
        t.start()

    def __del__(self):
        if self.ws is not None:
            self.stop()

    def connect(self):
        """
        The function creates a websocket 'ws'
        """
        _LOGGER.debug("connecting")
        if self.ws is None:
            _LOGGER.debug("opening socket")
            self.ws = websocket.WebSocket()
            _LOGGER.debug("WebSocket ("+str(self.ws)+")")
            self.ws.connect(self.api_url)
            _LOGGER.debug("Socket connected")

    def disconnect(self):
        pass

    def _send_receive(self, message):
        """
        The function will wrap the 'message' with a unique identifier,
            send the message and wait for the response.
        All messages sent will receive a response. That response may indicate success,
            but that is only success for receiving the message. Any command to change the
            state of a device will only know if it is successful when a dynamic message is recived.
            So only 'DeviceList' response really contains useful data.
        :param message:
        'message' is a string of a CommandType and nay data needed.
        It is a json formatted string. All inner elements must use double quotes.
        :return:
        The response after the message tracking data is removed
        """
        tmp_uuid = str(uuid.uuid1())
        my_message = '{"MobileInternalIndex":"' + tmp_uuid + '",' + message + '}'
        _LOGGER.debug("Send next")
        self.send(my_message)
        _LOGGER.debug("After send")
        loop_count = 0
        tmp_resp = ""
        while loop_count < 20:
            loop_count += 1
            print("loop_count: " + str(loop_count))
            if tmp_uuid in self.send_receive:
                print("tmp response: " + json.dumps(self.send_receive[tmp_uuid]))
                tmp_resp = self.send_receive[tmp_uuid]
                del self.send_receive[tmp_uuid]
                break
            time.sleep(.5)
        return tmp_resp

    def get_device_list(self):
        """
        Will poll Almond+ for devices info if needed
        :return:
            Returns a dict of Almond+ Entities
            The key is id and device_id zero filled to 4 digets.
        """
        if self.entity_dict is None:
            message = '"CommandType":"DeviceList"'
            self.entity_dict = self._build_entity_list(self._send_receive(message))
        return self.entity_dict

    def _build_entity_list(self, receive_data):
        """
        Helper function to build a dict of Almond+ entities from
            a response message.
        :param receive_data:
            The receive data may be from a device_list or state change event
        :return:
            Almond+ entity dict
        """
        entity_dict = {}
        response = receive_data["Devices"]
        for id in response:
            if 'Data' in response[id]:
                tmp_device_data = response[id]["Data"]
            else:
                tmp_device_data = []
            if 'DeviceValues' in response[id]:
                tmp_device_value = response[id]["DeviceValues"]
            else:
                tmp_device_value = []
            for device_id in tmp_device_value:
                tmp_entity = AlmondPlusEntity(id
                                              , tmp_device_data
                                              , device_id
                                              , tmp_device_value[device_id])
                tmp_key = id.zfill(4)+device_id.zfill(4)
                entity_dict[tmp_key] = tmp_entity
        return entity_dict

    def set_device(self, id, device_id, value):
        """
        Set device to value
        :param id:
        :param device_id:
        :param value:
            No testing if value is correct type
        :return:
        """
        message = '"CommandType":"UpdateDeviceIndex", "ID":"' \
                  + id + '","Index":"' + device_id + '", "Value":"' + value + '"'
        response = self._send_receive(message)["Success"]
        return response.lower() == 'true'

    def send(self, message):
        _LOGGER.debug("sending "+message)
        self.ws.send(message)
        _LOGGER.debug("Sent")

    def _update_entity(self, entity_update):
        """
        Helper function to keep Almond+ dict up to date.
        :param entity_update:
            The dict of entity may be full or partial, example from a value
                change event.
        """
        for entity_key, entity_value in entity_update.items():
            if entity_key in self.entity_dict:
                if len(entity_value.name) > 0:
                    self.entity_dict[entity_key].name = entity_value.name
                if len(entity_value.friendly_device_type) > 0:
                    self.entity_dict[entity_key].friendly_device_type = entity_value.friendly_device_type
                if len(entity_value.type) > 0:
                    self.entity_dict[entity_key].type = entity_value.type
                if len(entity_value.location) > 0:
                    self.entity_dict[entity_key].location = entity_value.location
                if len(entity_value.last_active_epoch) > 0:
                    self.entity_dict[entity_key].last_active_epoch = entity_value.last_active_epoch
                if len(entity_value.model) > 0:
                    self.entity_dict[entity_key].model = entity_value.model
                if len(entity_value.value_name) > 0:
                    self.entity_dict[entity_key].value_name = entity_value.value_name
                if len(entity_value.value_type) > 0:
                    self.entity_dict[entity_key].value_type = entity_value.value_type
                if len(entity_value.value_value) > 0:
                    self.entity_dict[entity_key].value_value = entity_value.value_value

    def receive(self):
        """
        The receive function is part of the worker loop.
        The dispatch thread will re-launch as necessarily.
        The receive can be generated from a device state change or
            response to a command. Any commands will have a different guid
        :return:
            Nothing is return directly, but the internal Almond+ entities will be up to date.
        """
        _LOGGER.debug("receive started")
        try:
            recv_data = self.ws.recv()
            _LOGGER.debug(recv_data)
            parse_data = json.loads(recv_data)
            if 'MobileInternalIndex' in parse_data:
                tmp_mobile_internal_index = parse_data['MobileInternalIndex']
                self.send_receive[tmp_mobile_internal_index] = parse_data
                _LOGGER.debug("load send rec: " + tmp_mobile_internal_index + '-' + json.dumps(self.send_receive[tmp_mobile_internal_index]))
            elif 'CommandType' in parse_data:
                if 'Devices' in parse_data:
                    tmp_entity_list = self._build_entity_list(parse_data)
                    self._update_entity(tmp_entity_list)
                    if self.call_back is not None:
                        self.call_back(tmp_entity_list)
                _LOGGER.debug(parse_data['CommandType'])

        except Exception as e:
            _LOGGER.error("Error (Almond+ receive())\n"
                          + "**************************\n"
                          + str(e) + "\n"
                          + traceback.format_exc()
                          + "**************************")
            self.ws = None
            return
        _LOGGER.debug("receive ended")
        if self.client_running:
            self.receive()

    def api_dispatcher(self):
        """
        This is the other half of the worker loop.
        Will connet then call receive function which will call it's self.
        The only reason receive returns is either the client is stopped or
            there was an error.
        """
        while self.keep_running:
            _LOGGER.debug("Dispatcher Start")
            if self.client_running:
                _LOGGER.debug("Client is running")
                if self.ws is None:
                    _LOGGER.debug("self.ws is none")
                    self.connect()
                    self.receive()

    def start(self):
        """
        keep_running flag will keep the dispatch looping
        then when this function turns on the client_running flag
            the dispatch loop will then call connect/receive.
        """
        _LOGGER.debug("start started")
        self.client_running = True
        _LOGGER.debug("start Finsh")

    def stop(self):
        """
        clears both the dispatch and communications flags then
            closes the socket connection allowing the threads to
            unwind and the API shuts down.
        """
        print("Stop 1")
        self.client_running = False
        self.keep_running = False
        if self.ws is not None:
            self.ws.close()
            self.ws = None
        print("Stop 2")


class AlmondPlusEntityList:
    """
    Class to manage a dictionary of Almond+ entities
    Each Almond+ device has an id. Then that device may have
        more than one switch, sensor, or ect identified with a
        device_id. Both numbers zero filled to 4 digits make up the
        entity key.
    """
    def __init__(self):
        self._EntityDict = {}
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self):
        self._index += 1
        if self._index >= len(self._EntityDict):
            raise StopIteration
        return self._EntityDict.get(list(self._EntityDict.keys())[self._index])

    def __str__(self):
        for key in self._EntityDict:
            return '{"' + key + '":"AlmondPlusEntity:"' + str(self._EntityDict[key]) + '"}'

    def __len__(self):
        return len(self._EntityDict)

    def clear(self):
        self._EntityDict.clear()

    def append(self, value):
        self._EntityDict[value.id.zfill(4)+value.device_id.zfill(4)] = value

    def get(self, id, device_id):
        return self._EntityDict[id.zfill(4)+device_id.zfill(4)]

    def exist(self, id, device_id):
        return id.zfill(4)+device_id.zfill(4) in self._EntityDict.keys()


class AlmondPlusEntity:
    def __init__(self, id, device_data, device_id, device_values):
        self.device_id = device_id
        self.id = str(id)
        if len(device_values) > 0:
            self.value_name = device_values["Name"]
            self.value_value = device_values["Value"]
            if "Type" in device_values:
                self.value_type = device_values["Type"]
            else:
                self.value_type = ""
        else:
            self.value_name = ""
            self.value_value = ""
            self.value_type = ""

        if len(device_data) > 0:
            self.name = device_data["Name"]
            self.friendly_device_type = device_data["FriendlyDeviceType"]
            self.type = device_data["Type"]
            self.location = device_data["Location"]
            self.last_active_epoch = device_data["LastActiveEpoch"]
            self.model = device_data["Model"]
        else:
            self.name = ""
            self.friendly_device_type = ""
            self.type = ""
            self.location = ""
            self.last_active_epoch = ""
            self.model = ""

    def __str__(self):
        return '{' \
                + '"id":"' + self.id + '"' \
                + ',"device_id":"' + self.device_id + '"' \
                + ',"name":"' + self.name + '"' \
                + ',"friendly_device_type":"' + self.friendly_device_type + '"' \
                + ',"location":"' + self.location + '"' \
                + ',"last_active_epoch":"' + self.last_active_epoch + '"' \
                + ',"model":"' + self.model + '"' \
                + ',"value_name":"' + self.value_name + '"' \
                + ',"value_value":"' + self.value_value + '"' \
                + ',"value_type":"' + self.value_type + '"' \
                + '}'


'''
This is an example response from a Almond+ Device List.
Some of the JSON has been expanded for reference.
'''
# {
#   "MobileInternalIndex":"9cfd3f18-8467-11e8-bbd0-0023246df72f",
#   "CommandType":"DeviceList",
#   "Devices" : {
#               "2":{
#                   "Data":{
#                         "ID":"2",
#                         "Name":"Under Cabinet MultiSwitch",
#                         "FriendlyDeviceType":"BinarySwitch",
#                         "Type":"43",
#                         "Location":"Under Cabinet",
#                         "LastActiveEpoch":"1531220046",
#                         "Model":"Unknown: type=2017,",
#                         "Version":"4",
#                         "Manufacturer":"YALE"
#                         },
#                   "DeviceValues":{
#                                   "1":{
#                                       "Name":"SWITCH_BINARY1",
#                                       "Value":"false",
#                                       "Type":"1"
#                                       },
#                                   "2":{
#                                       "Name":"SWITCH_BINARY2",
#                                       "Value":"false",
#                                       "Type":"1"
#                                       }
#                                 }
#                   },
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
#                   },"5":{"Data":{"ID":"5","Name":"Garage Lights Inside/Outside","FriendlyDeviceType":"BinarySwitch","Type":"43","Location":"Default","LastActiveEpoch":"1531219310","Model":"Unknown: type=2017,","Version":"4","Manufacturer":"YALE"},"DeviceValues":{"1":{"Name":"SWITCH_BINARY1","Value":"false","Type":"1"},"2":{"Name":"SWITCH_BINARY2","Value":"false","Type":"1"}}},"6":{"Data":{"ID":"6","Name":"Vaulted Ceiling/Porch Light","FriendlyDeviceType":"BinarySwitch","Type":"43","Location":"Default","LastActiveEpoch":"1530761308","Model":"Unknown: type=2017,","Version":"4","Manufacturer":"YALE"},"DeviceValues":{"1":{"Name":"SWITCH_BINARY1","Value":"false","Type":"1"},"2":{"Name":"SWITCH_BINARY2","Value":"false","Type":"1"}}},"7":{"Data":{"ID":"7","Name":"Almond Click Purp","FriendlyDeviceType":"SecurifiButton","Type":"61","Location":"Default","LastActiveEpoch":"1531191308","Model":"ZB2-BU01 ","Version":"0","Manufacturer":"Securifi L"},"DeviceValues":{"1":{"Name":"PRESS","Value":"3","Type":"91"},"2":{"Name":"LOW BATTERY","Value":"false","Type":"12"},"3":{"Name":"TAMPER","Value":"false","Type":"9"}}},"8":{"Data":{"ID":"8","Name":"Outside outlet Entryway","FriendlyDeviceType":"BinarySwitch","Type":"1","Location":"Default","LastActiveEpoch":"1531220050","Model":"Unknown: type=2017,","Version":"4","Manufacturer":"YALE"},"DeviceValues":{"1":{"Name":"SWITCH BINARY","Value":"false","Type":"1"}}},"9":{"Data":{"ID":"9","Name":"Power Strip 1","FriendlyDeviceType":"BinarySwitch","Type":"1","Location":"Default","LastActiveEpoch":"1531242749","Model":"ZFM-80","Version":"4","Manufacturer":"Remotec"},"DeviceValues":{"1":{"Name":"SWITCH BINARY","Value":"false","Type":"1"}}}}
# }
#
