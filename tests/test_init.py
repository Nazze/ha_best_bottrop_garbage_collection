"""Test integration_blueprint setup process."""

from homeassistant.exceptions import ConfigEntryNotReady
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.best_bottrop_garbage_collection import (
    BESTCoordinator,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.best_bottrop_garbage_collection.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState

from .const import MOCK_CONFIG_1, MOCK_CONFIG_2


# We can pass fixtures as defined in conftest.py to tell pytest to use the fixture
# for a given test. We can also leverage fixtures and mocks that are available in
# Home Assistant using the pytest_homeassistant_custom_component plugin.
# Assertions allow you to verify that the return value of whatever is on the left
# side of the assertion matches with the right side.
async def test_setup_unload_and_reload_entry(hass, bypass_get_data):
    """Test entry setup and unload."""
    # Create a mock entry so we don't have to go through config flow
    config_entry1 = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG_1, entry_id="test1")

    # Create another mock entry so we don't have to go through config flow
    config_entry2 = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG_1, entry_id="test2")

    # Set up the entry and assert that the values set during setup are where we expect
    # them to be. Because we have patched the BESTCoordinator.async_update_data
    # call, no code from custom_components/best_bottrop_garbage_collection/update_data actually runs.
    config_entry1.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry1.entry_id)
    assert await async_setup_entry(hass, config_entry1)
    await hass.async_block_till_done()

    print("%s", str(type(hass.data[DOMAIN])))
    assert DOMAIN in hass.data and isinstance(
        hass.data[DOMAIN]["coordinator"], BESTCoordinator
    )

    config_entry2.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry2.entry_id)
    assert await async_setup_entry(hass, config_entry2)
    await hass.async_block_till_done()
    assert DOMAIN in hass.data and isinstance(
        hass.data[DOMAIN]["coordinator"], BESTCoordinator
    )

    # # Reload the entry and assert that the data from above is still there
    # assert await async_reload_entry(hass, config_entry) is None
    # assert DOMAIN in hass.data and config_entry.entry_id in hass.data[DOMAIN]
    # assert type(hass.data[DOMAIN][config_entry.entry_id]) == BESTCoordinator

    # Unload the entry and verify that the data has been removed
    print("Hass Data: %s", hass.data)
    assert await async_unload_entry(hass, config_entry1)
    print("Hass Data: %s", hass.data)
    assert type(hass.data[DOMAIN]) != BESTCoordinator
