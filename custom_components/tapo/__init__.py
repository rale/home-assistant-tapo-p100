"""The tapo integration."""
import asyncio
import logging
from typing import cast
from typing import Optional

from custom_components.tapo.coordinators import HassTapoDeviceData
from custom_components.tapo.errors import DeviceNotSupported
from custom_components.tapo.hub.tapo_hub import TapoHub
from custom_components.tapo.migrations import migrate_entry_to_v3
from custom_components.tapo.migrations import migrate_entry_to_v4
from custom_components.tapo.setup_helpers import setup_tapo_device
from custom_components.tapo.setup_helpers import setup_tapo_hub
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .const import HUB_PLATFORMS
from .const import PLATFORMS

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the tapo_p100 component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up tapo from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    try:
        if entry.data.get("is_hub", False):
            hub = TapoHub(entry, await setup_tapo_hub(hass, entry))
            return await hub.initialize_hub(hass)
        else:
            device = await setup_tapo_device(hass, entry)
            return await device.initialize_device(hass)
    except DeviceNotSupported as error:
        raise error
    except Exception as error:
        raise ConfigEntryNotReady from error


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 3:  # migrate to add mac address
        migrate_entry_to_v4(hass, config_entry)
    elif config_entry.version >= 1:
        migrate_entry_to_v3(hass, config_entry)

    _LOGGER.info("Migration to version %s successful", config_entry.version)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    platform_to_unload = (
        PLATFORMS if not entry.data.get("is_hub", False) else HUB_PLATFORMS
    )
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in platform_to_unload
            ]
        )
    )
    if unload_ok:
        _LOGGER.info("Unloaded entry for %s", str(entry.entry_id))
        data = cast(
            Optional[HassTapoDeviceData], hass.data[DOMAIN].pop(entry.entry_id, None)
        )
        if data:
            data.config_entry_update_unsub()

    return unload_ok
