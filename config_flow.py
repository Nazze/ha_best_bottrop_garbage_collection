"""Config flow for BEST Bottrop garbage collection dates component"""
from __future__ import annotations

import logging

# from multiprocessing.sharedctypes import Value
# from typing import Any

from aiohttp import ClientResponseError

# from attr import validate
from best_bottrop_garbage_collection_dates import BESTBottropGarbageCollectionDates
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

# from homeassistant.helpers import aiohttp_client

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Garbage Collection Dates in Bottrop."""

    VERSION = 1
    _prefilled: list[str] | None = None
    _bgc: BESTBottropGarbageCollectionDates() = BESTBottropGarbageCollectionDates()
    _street_id_dict: dict = None
    _selected_street_id: str = ""
    _selected_number: int = 0
    _selected_street_name: str = ""
    _data: dict[str, int] = None

    async def validate_best_config(self) -> None:
        """Validate that the data is correct and can be retrieved
        Raises a ValueError if there the data cannot be retrieved
        """
        res_list: list[dict] = [""]
        errors: dict[str, str] = {}

        if self._selected_street_id == "" or self._selected_number <= 0:
            raise ValueError

        #        session = async_get_clientsession(hass)
        try:
            res_list = await self._bgc.get_dates_as_json(
                self._selected_street_id, self._selected_number
            )
            if len(res_list) == 0:
                raise ValueError
        except ClientResponseError as e:
            # There was some kind of problem to make the GET command (connectivity problems?)
            _LOGGER.exception("Unexpected exception")
            raise ValueError

        # If the result is empty, the API did not return anything due to invalid data

    async def async_step_user(
        self, user_input: dict[str, int] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        self._data = user_input
        errors: dict[str, str] = {}

        if self._street_id_dict is None:
            self._street_id_dict = self._bgc.get_street_id_dict()

        if self._prefilled is None and self._street_id_dict is not None:
            self._prefilled = []
            streets = list(self._street_id_dict.keys())
            for street in sorted(streets):
                self._prefilled.append(street)

        if user_input is not None:

            self._selected_street_name = user_input["street_name"]

            self._selected_street_id = self._street_id_dict.get(
                self._selected_street_name
            )

            self._selected_number = user_input["number"]

            # Check if getting data works in the validate function
            try:
                await self.validate_best_config()
            except ValueError:
                errors = {"base": "config"}

            if not errors:
                await self.async_set_unique_id(
                    f"{self._selected_street_id}_{self._selected_number}"
                )
                self._abort_if_unique_id_configured()
                self._data["street_id"] = self._selected_street_id

                _LOGGER.debug(
                    "Creating entry %s %s %s",
                    self._selected_street_name,
                    self._selected_number,
                    self._data,
                )

                return self.async_create_entry(
                    title=f"{self._selected_street_name} {self._selected_number}",
                    data=self._data,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("street_name"): vol.In(self._prefilled),
                    vol.Required("number"): int,
                }
            ),
            errors=errors,
        )
