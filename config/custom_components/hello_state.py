import logging

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'hello_state'
DEPENDENCIES = []

CONF_TEXT = 'text'
DEFAULT_TEXT = 'No text!'

def setup(hass, config):
    """Set up the Hello State component. """
    # Get the text from the configuration. Use DEFAULT_TEXT if no name is provided.
    text = config[DOMAIN].get(CONF_TEXT, DEFAULT_TEXT)

    # States are in the format DOMAIN.OBJECT_ID
    hass.states.set('hello_state.Hello_State', text)

    return True