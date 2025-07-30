"""Intégration Zendure pour Home Assistant."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceEntry

from .zendurermanager import ZendureManager

_LOGGER = logging.getLogger(__name__)

# Liste des plateformes supportées par l'intégration (types d'entités HA)
PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.NUMBER, Platform.SELECT, Platform.SENSOR, Platform.SWITCH]

# Type alias pour faciliter la gestion des ConfigEntry typés
type MyConfigEntry = ConfigEntry[RuntimeData]

@dataclass
class RuntimeData:
    """Classe pour stocker les données runtime de l'intégration."""
    manager: ZendureManager

async def async_setup_entry(hass: HomeAssistant, config_entry: MyConfigEntry) -> bool:
    """
    Configure l'intégration Zendure à partir d'une entrée de configuration.
    Initialise le manager, prépare les plateformes et lance le chargement des données.
    """
    manager = ZendureManager(hass, config_entry)
    config_entry.runtime_data = RuntimeData(manager)
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    _LOGGER.debug("Ouverture de la connexion API")
    if not await manager.load():
        # Si le chargement échoue, signale que la config n'est pas prête
        raise ConfigEntryNotReady

    # Rafraîchit les données à la première configuration
    await manager.async_config_entry_first_refresh()

    # Ajoute un listener pour gérer les mises à jour de la configuration
    config_entry.async_on_unload(config_entry.add_update_listener(_async_update_listener))

    # Retourne True si la configuration est réussie
    return True

async def _async_update_listener(hass: HomeAssistant, config_entry: MyConfigEntry) -> None:
    """
    Gère la mise à jour des options de configuration.
    Recharge l'intégration si les options changent.
    """
    await hass.config_entries.async_reload(config_entry.entry_id)

async def async_remove_config_entry_device(_hass: HomeAssistant, _config_entry: ConfigEntry, _device_entry: DeviceEntry) -> bool:
    """
    Gère la suppression d'un appareil de l'intégration.
    Ici, on retourne toujours False (suppression non supportée).
    """
    return False

async def async_unload_entry(hass: HomeAssistant, config_entry: MyConfigEntry) -> bool:
    """
    Décharge une entrée de configuration.
    Décharge les plateformes et appelle le déchargement du manager.
    """
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    if unload_ok:
        # Si le déchargement est réussi, on décharge le manager
        data = config_entry.runtime_data
        manager = data.manager
        if manager:
            await manager.unload()
        return True

    # Si le déchargement échoue, log une erreur et retourne False
    _LOGGER.error("async_unload_entry : échec du déchargement des plateformes")
    return False

async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Gère la migration d'une ancienne entrée de configuration vers une nouvelle version.
    Met à jour la version mineure si besoin.
    """
    if entry.version == 1 and entry.minor_version < 1:
        new_data = entry.data.copy()
        hass.config_entries.async_update_entry(entry, data=new_data, minor_version=2)
        _LOGGER.info(f"Migration vers la version de configuration %s.%s réussie {entry.version}, {entry.minor_version}")
    return True
