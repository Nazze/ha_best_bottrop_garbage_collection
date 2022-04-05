from homeassistant.const import Platform
import logging
from datetime import timedelta
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

from .const import DOMAIN

PLATFORMS = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BEST Bottrop from a config entry."""
    await get_coordinator(hass)
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload BEST Bottrop config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if len(hass.config_entries.async_entries(DOMAIN)) == 1:
        hass.data.pop(DOMAIN)

    return unload_ok


async def get_coordinator(
    hass: HomeAssistant,
) -> DataUpdateCoordinator:
    """Get the data update coordinator."""
    if DOMAIN in hass.data:
        return hass.data[DOMAIN]

    async def async_update_collection_dates() -> list[dict]:

        # create a list with responses
        # streetid : JSON-Object
        ret_list: list = []

        for entry in hass.config_entries.async_entries(DOMAIN):
            _LOGGER.debug("Request for update for entry %s", entry.data["street_id"])

            # ClientError Exceptions already caught by HA
            async with async_timeout.timeout(10):
                resp = await BESTBottropGarbageCollectionDates().get_dates_as_json(
                    entry.data["street_id"], entry.data["number"]
                )
            resp_list = list(resp)
            ret_list.append([entry.data["street_id"], resp_list])

        return ret_list

    # Update dates every 12 hrs
    coordinator = DataUpdateCoordinator(
        hass,
        logging.getLogger(__name__),
        name=DOMAIN,
        update_method=async_update_collection_dates,
        update_interval=timedelta(hours=12),
    )
    # await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN] = coordinator
    return coordinator
