""" Platform sensor for BEST Bottrop"""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import (
    HomeAssistant,
    callback,
)
from datetime import date
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from best_bottrop_garbage_collection_dates import BESTBottropGarbageCollectionDates
from datetime import timedelta
from aiohttp import ClientError

import logging

from . import get_coordinator
from .const import ATTRIBUTION

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=5)

TRASH_ICONS = {
    # Graue Tonne
    "F7CB1CCE": "mdi:trash-can-outline",
    # Gelbe Tonne
    "3F14EDC7": "mdi:recycle",
    # Blue/Paper
    "DFF3C375": "mdi:newspaper-variant-multiple-outline",
    # Braune Tonne / Kompost / Bio
    "AE9A662E": "mdi:sprout",
    # Weihnachtsbaum
    "43806A8A": "mdi:pine-tree",
    # Container
    "A2954658": "mdi:truck-cargo-container",
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Defer sensor setup to the shared sensor module."""

    coordinator = await get_coordinator(hass)

    entities: list[BESTBottropSensor] = []

    bgc = BESTBottropGarbageCollectionDates()

    await bgc.get_trash_types()

    for trash_type in bgc.trash_types_json:
        entities.append(
            BESTBottropSensor(
                coordinator,
                config_entry.data["street_name"],
                config_entry.data["street_id"],
                config_entry.data["number"],
                trash_type.get("id"),
                trash_type.get("name"),
            )
        )

    async_add_entities(entities, True)


class BESTBottropSensor(CoordinatorEntity, SensorEntity):
    """Representation BEST Bottrop garbage collection data."""

    _bcgc = BESTBottropGarbageCollectionDates()

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        street_name: str,
        street_id: str,
        number: int,
        trash_type_id: str,
        trash_type_name: str,
    ) -> None:
        """Initialize BEST Bottrop sensor."""
        super().__init__(coordinator)

        self._attr_attribution = ATTRIBUTION
        self._attr_native_unit_of_measurement = "date"
        self._attr_unique_id = f"{street_name}-{number}-{trash_type_name}"
        self._attr_name = f"{street_name} {number} {trash_type_name}"
        self._attr_icon = TRASH_ICONS[trash_type_id]
        self._state = None

        # extra attributes
        self._street_name = street_name
        self._street_id = street_id
        self._number = number
        self._trash_type_id = trash_type_id
        self._trash_type_name = trash_type_name
        self._message = ""
        self._next_date = None
        self._days = 0

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug(
            "I am %s, callback function called",
            self._attr_unique_id,
        )
        # Now find my JSON
        sub_list_data: lists
        for sub_list_data in self.coordinator.data:
            if self._street_id in sub_list_data[0]:
                # iterate throught the JSON of our street_id!
                for next_collection in sub_list_data[1]:
                    # now find the resulting trash type
                    _LOGGER.debug("Unpacking data %s", next_collection)
                    if self._trash_type_id == next_collection["trashType"]:
                        # next collection date for the trashtype found
                        # the format is dd.mm.yyyy
                        ldate = next_collection["formattedDate"].split(".", 3)
                        _LOGGER.debug(
                            "Updateing native value: %s",
                            str(date(int(ldate[2]), int(ldate[1]), int(ldate[0]))),
                        )
                        # self._attr_native_value = date(
                        # int(ldate[2]), int(ldate[1]), int(ldate[0])
                        # )
                        self._state = str(
                            date(int(ldate[2]), int(ldate[1]), int(ldate[0]))
                        )
                        self._next_date = date(
                            int(ldate[2]), int(ldate[1]), int(ldate[0])
                        )

                        diff_date = self._next_date - date.today()

                        if diff_date.days > 0:
                            self._days = diff_date.days
                        else:
                            self._days = 0

                        self._message = next_collection["message"]

                        self.async_write_ha_state()
                        break
        # self._attr_is_on = self.coordinator.data[self.idx]["state"]
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self):
        """Generate dictionary with extra state attributes."""
        attr = {
            "street_name": self._street_name,
            "street_number": self._number,
            "street_id": self._street_id,
            "trash_type_id": self._trash_type_id,
            "trash_type_name ": self._trash_type_name,
            "special_message": self._message,
            "next_collection_date": str(self._next_date),
            "days_left": self._days,
        }

        return attr

    @property
    def available(self) -> bool:
        """Return if sensor is available."""
        return self.coordinator.last_update_success and (
            self._street_id in self.coordinator.data[0]
        )

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        return self._state

    @property
    def should_poll(self) -> bool:
        return False
