"""Platform sensor for BEST Bottrop."""

from __future__ import annotations

import logging
from best_bottrop_garbage_collection_dates import BESTBottropGarbageCollectionDates
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from homeassistant.components.sensor import (
    RestoreEntity,
    RestoreSensor,
    SensorEntity,
    SensorExtraStoredData,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)

from homeassistant.core import (
    callback,
    HomeAssistant,
)
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

# from homeassistant.helpers.entity_component import EntityComponent
from .const import (
    ATTRIBUTION,
    DOMAIN,
    SERVICE_IGNORE,
)
import voluptuous as vol


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

    coordinator = hass.data[DOMAIN]["coordinator"]

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

    platform = entity_platform.async_get_current_platform()

    _LOGGER.debug("Registering service")

    platform.async_register_entity_service(
        SERVICE_IGNORE,
        {vol.Optional("days", default=2): int},
        SERVICE_IGNORE,
    )
    async_add_entities(entities)


class BESTBottropSensor(CoordinatorEntity, RestoreSensor):
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

        # change the string format from e.g. "Gelbe Tonne" to "gelbe_tonne"
        street_name_unique = street_name.lower()
        trash_type_unique = trash_type_name.lower().replace(" ", "_")

        self._attr_attribution = ATTRIBUTION
        self._attr_unique_id = f"{street_name_unique}_{number}_{trash_type_unique}"
        self.entity_id = f"sensor.{street_name_unique}_{number}_{trash_type_unique}"
        self._attr_name = f"{trash_type_name}"
        self._attr_icon = TRASH_ICONS[trash_type_id]
        self._state = None

        # extra attributes

        self._extra_attributes = {}
        self._extra_attributes["street_name"] = street_name
        self._extra_attributes["street_id"] = street_id
        self._extra_attributes["street_number"] = number
        self._extra_attributes["trash_type_id"] = trash_type_id
        self._extra_attributes["trash_type_name"] = trash_type_name
        self._extra_attributes["special_message"] = ""
        self._extra_attributes["next_date"] = None
        self._extra_attributes["days"] = -1
        self._extra_attributes["ignore_until"] = None

    async def async_added_to_hass(self) -> None:
        """Check, if data to be restored."""

        _LOGGER.debug("Checking for available data to be restored")
        await super().async_added_to_hass()

        # ls = await self.async_get_last_state()
        # lss = await self.async_get_last_sensor_data()
        # lsed = await self.async_get_last_extra_data()

        if (last_state := await self.async_get_last_state()) is not None:
            _LOGGER.debug(
                "Restoring data from BEST sensor with entity_id %s", self.entity_id
            )
            if last_state.state != "unknown":
                self._state = last_state.state
                self._attr_native_value = last_state
            # ADDED CODE HERE
            if last_state.attributes is not None:
                # extra attributes
                # check if at least one key is there, then it is initialized and we should be safe to assign the others as well
                if "street_name" in last_state.attributes:
                    self._extra_attributes.update(last_state.attributes)
            else:
                _LOGGER.debug("No restoring extra data found for %s", self.entity_id)
        else:
            _LOGGER.debug(
                "Could not restore state and extra data for %s", self.entity_id
            )
        self.async_schedule_update_ha_state(True)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug(
            "I am %s, callback function called",
            self._attr_unique_id,
        )

        if self._extra_attributes["trash_type_id"] == "A2954658":
            _LOGGER.debug("Container ignored")
            return

        # Now find my JSON
        # sub_list_data: lists
        # the data is structured as a dict. The key is the street_id.
        # That data to that key is the JSON-dict.
        if (self.coordinator.data is not None) and (
            self._extra_attributes["street_id"] in self.coordinator.data
        ):
            street_json = self.coordinator.data[self._extra_attributes["street_id"]]
            # iterate throught the JSON of our street_id!
            for next_collection in street_json:
                # now find the resulting trash type
                if (
                    self._extra_attributes["trash_type_id"]
                    == next_collection["trashType"]
                ):
                    # next collection date for the trashtype found
                    # the format is dd.mm.yyyy
                    ldate = next_collection["formattedDate"].split(".", 3)
                    next_date = date(int(ldate[2]), int(ldate[1]), int(ldate[0]))
                    _LOGGER.debug("Next date %s", next_date)
                    _LOGGER.debug("Today  %s", datetime.today())
                    _LOGGER.debug(
                        "Ignore until  %s", self._extra_attributes["ignore_until"]
                    )

                    if (
                        (self._extra_attributes["ignore_until"] is not None)
                        and (isinstance(self._extra_attributes["ignore_until"], str))
                        and (
                            (
                                ignore := datetime.strptime(
                                    self._extra_attributes["ignore_until"], "%Y-%m-%d"
                                ).date()
                            )
                            is not None
                        )
                        and (next_date <= ignore)
                    ):
                        _LOGGER.debug("SKIPPING")
                        continue

                    diff_date = next_date - date.today()

                    _LOGGER.debug("Diff  %s", diff_date)

                    self._extra_attributes["next_date"] = date(
                        next_date.year, next_date.month, next_date.day
                    )

                    _LOGGER.debug(
                        "Updateing native value: %s",
                        str(diff_date.days),
                    )

                    if diff_date.days >= 0:
                        # if the diff date == 0, then it is/was today.
                        self._state = diff_date.days
                        self._extra_attributes["days"] = diff_date.days
                    else:
                        self._state = None

                    self._extra_attributes["special_message"] = next_collection[
                        "message"
                    ]
                    break
        # self.async_write_ha_state()
        super()._handle_coordinator_update()

    @property
    def extra_state_attributes(self):
        """Generate dictionary with extra state attributes."""
        return self._extra_attributes

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        return self._state

    async def ignore(self, days: int) -> None:
        """Handle the ignore call. This will ignore this entity for the defined days."""
        _LOGGER.debug("Called handle_ignore for %s", self._attr_unique_id)

        ignore_until: date = None

        _LOGGER.debug("got days %s", str(days))

        if days == 0:
            _LOGGER.debug("Days is zero. Resetting")
            ignore_until = None
        else:
            ignore_until = date.today() + timedelta(days=days)

        _LOGGER.debug("Ignoring until %s", ignore_until)
        self._extra_attributes["ignore_until"] = str(ignore_until)

        await self.async_update_ha_state(True)
