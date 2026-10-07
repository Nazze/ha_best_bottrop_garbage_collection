"""Tests for the BEST Bottrop sensor."""

from datetime import timedelta

from custom_components.best_bottrop_garbage_collection import BESTCoordinator
from custom_components.best_bottrop_garbage_collection.sensor import BESTBottropSensor
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util


async def test_sensor_keeps_last_data_when_refresh_fails(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep the previous sensor value and mark it stale after a failed refresh."""
    monkeypatch.setattr(BESTBottropSensor, "async_write_ha_state", lambda self: None)

    coordinator = BESTCoordinator(hass)
    sensor = BESTBottropSensor(
        coordinator,
        street_name="Ernst-Wilczok-Platz",
        street_id="street-id",
        number=1,
        trash_type_id="3F14EDC7",
        trash_type_name="Gelbe Tonne",
    )
    assert not sensor.available

    today = dt_util.now().date()
    first_date = today + timedelta(days=5)
    first_collection = {
        "formattedDate": first_date.strftime("%d.%m.%Y"),
        "message": "first collection",
        "trashType": "3F14EDC7",
    }
    coordinator.data = {"street-id": [first_collection]}
    coordinator.last_update_success = True

    sensor._handle_coordinator_update()  # noqa: SLF001

    previous_attributes = sensor.extra_state_attributes.copy()
    assert sensor.available
    assert sensor.native_value == 5
    assert previous_attributes["data_is_stale"] is False

    coordinator.last_update_success = False
    sensor._handle_coordinator_update()  # noqa: SLF001

    assert sensor.available
    assert sensor.native_value == 5
    assert {
        key: value
        for key, value in sensor.extra_state_attributes.items()
        if key != "data_is_stale"
    } == {
        key: value
        for key, value in previous_attributes.items()
        if key != "data_is_stale"
    }
    assert sensor.extra_state_attributes["data_is_stale"] is True

    second_date = today + timedelta(days=8)
    coordinator.data = {
        "street-id": [
            {
                "formattedDate": second_date.strftime("%d.%m.%Y"),
                "message": "updated collection",
                "trashType": "3F14EDC7",
            }
        ]
    }
    coordinator.last_update_success = True
    sensor._handle_coordinator_update()  # noqa: SLF001

    assert sensor.native_value == 8
    assert sensor.extra_state_attributes["next_date"] == str(second_date)
    assert sensor.extra_state_attributes["special_message"] == "updated collection"
    assert (
        sensor.extra_state_attributes["data_updated_at"]
        != previous_attributes["data_updated_at"]
    )
    assert sensor.extra_state_attributes["data_is_stale"] is False
