"""TikTok TTS - Home Assistant Custom Integration.

This is the integration entry point. HA calls async_setup once at startup,
async_setup_entry when the user adds the integration via the UI, and
async_unload_entry when they remove it.

Architecture overview
---------------------
The integration consists of these files:

  __init__.py   (this file)
    Registers the integration with HA, auto-registers the Lovelace card
    resource, forwards setup to all platforms, and installs a config-entry
    update listener so that changes saved via the options UI (gear icon)
    automatically trigger a reload - no manual HA restart required.
    Also clears singleton flags when the last config entry is removed so
    shared entities are recreated cleanly if the integration is re-added.

  config_flow.py
    Implements the UI setup wizard and the options (reconfigure) screen.
    Covers two connection modes:
      - Proxy mode:  talks to a community-run HTTP proxy that forwards
                     requests to TikTok on your behalf. No TikTok account
                     needed. Default proxy: https://tiktok-tts.weilnet.workers.dev
      - Direct mode: calls TikTok's internal API directly, using a session
                     cookie extracted from a logged-in TikTok browser session.
                     Falls back through multiple regional endpoints automatically.
    Both modes perform a live connection test before saving, so bad credentials
    or unreachable endpoints are caught at setup time rather than at runtime.

  tts.py
    Defines TikTokTTSEntity, the HA TextToSpeechEntity subclass.
    Handles voice selection, text chunking (direct mode), retries, and audio
    decoding. All config is read dynamically from entry.data on every call,
    so options changes take effect as soon as the integration reloads.

  select.py
    Defines three SHARED SelectEntity subclasses - one instance each for the
    whole integration regardless of how many config entries exist:
      - LanguageSelectEntity: dropdown of all supported language codes.
      - VoiceSelectEntity: dropdown of voices filtered to the selected language.
        State is a friendly label; raw API code exposed via 'code' attribute.
      - DeviceSelectEntity: dropdown of all available media_player entities,
        populated dynamically from hass.states. Refreshes automatically when
        new devices come online (e.g. browser_mod, mobile app).
    Created on the first config entry load, skipped for subsequent entries.
    Entity IDs: select.tiktoktts_language, select.tiktoktts_voice,
                select.tiktoktts_device

  text.py
    Defines a single SHARED MessageTextEntity - one instance for the whole
    integration. Provides a native HA text input field without requiring a
    manually created input_text helper.
    Entity ID: text.tiktoktts_message

  button.py
    Defines a single SHARED SpeakButtonEntity - one instance for the whole
    integration. When pressed it reads the current state of the language,
    voice, message, and device entities server-side and calls tts.speak
    directly in Python - no templates or scripts required.
    Entity ID: button.tiktoktts_speak

  frontend/__init__.py
    Registers the Lovelace card JS file as a static HTTP path and adds it
    to Lovelace's resource list automatically. No manual resource
    configuration required by the user.

  www/tiktoktts-card.js
    Custom Lovelace card providing a polished TTS control panel. Added to
    a dashboard with: type: custom:tiktoktts-card

  const.py
    All constants: API paths, field names, status codes, voice lists,
    language mappings, retry tuning, entity IDs/names, singleton flags,
    and attribution strings. If you need to adjust a behaviour (e.g. retry
    count, chunk size) or add a new voice, this is the only file you should
    need to touch.

Storage convention
------------------
Everything is stored in entry.data (not entry.options). This keeps a single
source of truth that both config_flow.py and tts.py read from consistently.
When the options flow saves changes it calls async_update_entry() to write
directly into entry.data, then returns an empty async_create_entry() to close
the flow. The update listener below detects the change and reloads the entry.

Singleton tracking
------------------
hass.data[DOMAIN] is used to track whether the shared select, text, and button
entities have been created. Keys defined in const.py:
  HASS_DATA_SELECT_CREATED, HASS_DATA_TEXT_CREATED, HASS_DATA_BUTTON_CREATED.
These flags are cleared when the last config entry is unloaded so that
removing and re-adding the integration recreates the entities cleanly.

Lovelace card registration
---------------------------
The custom Lovelace card is registered in async_setup (not async_setup_entry)
so it runs exactly once per HA startup regardless of how many config entries
exist. Registration is deferred until homeassistant_started to ensure Lovelace
resources are fully loaded. Requires 'frontend' and 'http' in manifest.json.

Credits
-------
Original integration: Philipp Lüttecke (https://github.com/philipp-luettecke/tiktoktts)
Community TTS proxy:  Weilbyte (https://github.com/Weilbyte/tiktok-tts)
Fork author:          Steven Fox / sfox38 (https://github.com/sfox38/tiktoktts)
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, CoreState, EVENT_HOMEASSISTANT_STARTED

from .const import DOMAIN, LOGGER
from .frontend import JSModuleRegistration

PLATFORMS: list[Platform] = [Platform.TTS, Platform.SELECT, Platform.TEXT, Platform.BUTTON]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register the Lovelace card resource once at integration load time.

    This must run in async_setup (not async_setup_entry) so it executes
    exactly once per HA startup regardless of how many config entries exist.
    Registration is deferred until homeassistant_started if HA is still
    starting up, ensuring Lovelace resources are fully loaded first.
    """
    async def _register_frontend(_event=None) -> None:
        await JSModuleRegistration(hass).async_register()

    if hass.state == CoreState.running:
        await _register_frontend()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _register_frontend)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TikTok TTS from a config entry.

    Called by HA when:
      - The user completes the setup wizard for the first time
      - HA restarts and reloads all existing config entries
      - The integration is reloaded (e.g. after an options change)

    Forwards setup to all platforms and registers the update listener.
    The shared select/text/button entities are only created once -
    select.py, text.py, and button.py handle the singleton logic
    internally via hass.data[DOMAIN].
    """
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Wrap the listener registration in async_on_unload so that HA
    # automatically deregisters it when the entry is unloaded. Without this
    # the listener would accumulate duplicate registrations across reloads.
    entry.async_on_unload(
        entry.add_update_listener(_async_update_listener)
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Called by HA when the user removes the integration, or just before a
    reload. Delegates to HA's platform unloader which tears down all
    platform entities cleanly.

    If this is the last remaining config entry, clear the singleton flags
    from hass.data so the shared entities are recreated cleanly if the
    integration is added again.
    """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        remaining = hass.config_entries.async_entries(DOMAIN)
        # async_entries still includes the current entry during unload,
        # so check for <= 1 rather than == 0
        if len(remaining) <= 1:
            LOGGER.debug(
                "Last TikTokTTS config entry unloaded - clearing singleton flags"
            )
            hass.data.pop(DOMAIN, None)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when entry.data is updated.

    Triggered automatically whenever async_update_entry() is called on this
    config entry, which happens at the end of the options flow in config_flow.py.
    Reloading causes async_unload_entry + async_setup_entry to run in sequence,
    so the TikTokTTSEntity is recreated and picks up the new configuration
    values from entry.data immediately.
    """
    LOGGER.debug("Config entry updated for %s - reloading", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)