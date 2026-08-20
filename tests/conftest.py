"""Test stubs for Home Assistant modules.

The integration is tested without a Home Assistant installation, so the parts
it imports are stubbed here. Anything the integration actually calls is
implemented; everything else is a placeholder.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sys
import types
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@dataclass(frozen=True, kw_only=True)
class EntityDescription:
    """Minimal Home Assistant entity description stub."""

    key: str
    translation_key: str | None = None
    icon: str | None = None
    device_class: Any = None
    native_unit_of_measurement: str | None = None
    state_class: Any = None


class ConfigEntry:
    """Minimal typed config entry stub."""

    def __class_getitem__(cls, item: Any) -> type[ConfigEntry]:
        """Support ConfigEntry[T] annotations."""
        return cls


class ConfigFlow:
    """Minimal config flow stub."""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Accept Home Assistant config flow class keywords."""
        super().__init_subclass__()


class OptionsFlow:
    """Minimal options flow stub."""


class CoordinatorEntity:
    """Minimal coordinator entity stub."""

    def __class_getitem__(cls, item: Any) -> type[CoordinatorEntity]:
        """Support CoordinatorEntity[T] annotations."""
        return cls

    def __init__(self, coordinator: Any) -> None:
        """Initialize the coordinator stub."""
        self.coordinator = coordinator

    @property
    def available(self) -> bool:
        """Return entity availability."""
        return True


class DataUpdateCoordinator:
    """Minimal data update coordinator stub."""

    def __class_getitem__(cls, item: Any) -> type[DataUpdateCoordinator]:
        """Support DataUpdateCoordinator[T] annotations."""
        return cls

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the coordinator stub."""
        self.data = None
        self.hass = args[0] if args else None


class UpdateFailed(Exception):
    """Minimal update failed exception."""


def _module(name: str) -> types.ModuleType:
    module = types.ModuleType(name)
    sys.modules[name] = module
    return module


_module("homeassistant")
_module("homeassistant.components")
_module("homeassistant.helpers")
_module("homeassistant.util")

config_validation = _module("homeassistant.helpers.config_validation")
config_validation.config_entry_only_config_schema = lambda domain: domain
config_validation.string = str

binary_sensor = _module("homeassistant.components.binary_sensor")
binary_sensor.BinarySensorEntity = type("BinarySensorEntity", (), {})
binary_sensor.BinarySensorEntityDescription = EntityDescription

sensor = _module("homeassistant.components.sensor")
sensor.SensorDeviceClass = types.SimpleNamespace(
    TIMESTAMP="timestamp", WIND_SPEED="wind_speed"
)
sensor.SensorStateClass = types.SimpleNamespace(MEASUREMENT="measurement")
sensor.SensorEntity = type("SensorEntity", (), {})
sensor.SensorEntityDescription = EntityDescription

frontend = _module("homeassistant.components.frontend")
frontend.add_extra_js_url = lambda hass, url: None

http = _module("homeassistant.components.http")
http.StaticPathConfig = lambda url_path, path, cache_headers=True: (
    url_path,
    path,
    cache_headers,
)

loader = _module("homeassistant.loader")


async def _async_get_integration(hass: Any, domain: str) -> Any:
    """Return a minimal integration stub."""
    return types.SimpleNamespace(version="0.0.0-test")


loader.async_get_integration = _async_get_integration

config_entries = _module("homeassistant.config_entries")
config_entries.ConfigEntry = ConfigEntry
config_entries.ConfigFlow = ConfigFlow
config_entries.ConfigFlowResult = dict[str, Any]
config_entries.OptionsFlow = OptionsFlow

const = _module("homeassistant.const")
const.Platform = types.SimpleNamespace(SENSOR="sensor", BINARY_SENSOR="binary_sensor")

core = _module("homeassistant.core")
core.HomeAssistant = object
core.ServiceCall = object
core.SupportsResponse = types.SimpleNamespace(OPTIONAL="optional")
core.callback = lambda func: func

exceptions = _module("homeassistant.exceptions")
exceptions.HomeAssistantError = type("HomeAssistantError", (Exception,), {})

aiohttp_client = _module("homeassistant.helpers.aiohttp_client")
aiohttp_client.async_get_clientsession = lambda hass: None

entity_platform = _module("homeassistant.helpers.entity_platform")
entity_platform.AddEntitiesCallback = object

update_coordinator = _module("homeassistant.helpers.update_coordinator")
update_coordinator.CoordinatorEntity = CoordinatorEntity
update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
update_coordinator.UpdateFailed = UpdateFailed

selector = _module("homeassistant.helpers.selector")
selector.NumberSelector = lambda config: (lambda value: value)
selector.NumberSelectorConfig = lambda **kwargs: kwargs
selector.NumberSelectorMode = types.SimpleNamespace(BOX="box")
selector.SelectSelector = lambda config: (lambda value: value)
selector.SelectSelectorConfig = lambda **kwargs: kwargs
selector.SelectSelectorMode = types.SimpleNamespace(LIST="list", DROPDOWN="dropdown")
selector.SelectOptionDict = lambda **kwargs: kwargs
selector.TextSelector = lambda *args, **kwargs: (lambda value: value)

typing_module = _module("homeassistant.helpers.typing")
typing_module.ConfigType = dict[str, Any]

dt = _module("homeassistant.util.dt")
dt.now = lambda: datetime.now().astimezone()
sys.modules["homeassistant.util"].dt = dt
