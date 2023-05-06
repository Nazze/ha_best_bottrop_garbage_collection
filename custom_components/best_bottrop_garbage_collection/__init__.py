from homeassistant.const import Platform
import logging
from datetime import timedelta, date
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
    UpdateFailed,
)
import async_timeout

from best_bottrop_garbage_collection_dates import BESTBottropGarbageCollectionDates

from .const import (
    DOMAIN,
    ATTR_DAYS,
    DEFAULT_DAYS,
    SENSOR_PLATFORM,
    COORDINATOR,
    ENITITY_COMPONENT,
    SERVICE_IGNORE,
)

PLATFORMS = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BEST Bottrop from a config entry."""

    coordinator = BESTCoordinator(hass)
    hass.data[DOMAIN] = {COORDINATOR: coordinator}
    # hass.data[DOMAIN].coordinator = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Update data for the first time. This has to be done after adding the entities,
    # otherwise the listeners won't be ready and won't be updated after reboot or
    # adding the component for the first time
    await coordinator.async_refresh()

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload BEST Bottrop config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)

    return unload_ok


class BESTCoordinator(DataUpdateCoordinator):
    """This is the coordinator for the BEST custom component."""

    def __init__(self, hass):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            logging.getLogger(__name__),
            # Name of the data. For logging purposes.
            name=DOMAIN,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(hours=4),
        )

    async def _async_update_data(self) -> dict:
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        # create a list with responses

        # streetid : JSON-Object
        ret_dict: dict = {}

        for entry in self.hass.config_entries.async_entries(DOMAIN):
            _LOGGER.debug(
                "Request for data fetch for street_id %s", entry.data["street_id"]
            )

            # ClientError Exceptions already caught by HA
            async with async_timeout.timeout(10):
                resp = await BESTBottropGarbageCollectionDates().get_dates_as_json(
                    entry.data["street_id"], entry.data["number"]
                )
            resp_list = list(resp)
            # the data is structured as a dict. The key is the street_id. That data to that key is the JSON-dict.
            ret_dict[entry.data["street_id"]] = resp_list

        return ret_dict
