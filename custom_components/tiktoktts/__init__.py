"""TikTok TTS - Home Assistant Custom Integration.

This is the integration entry point. HA calls async_setup once at startup,
async_setup_entry when the user adds the integration via the UI, and
async_unload_entry when they remove it.

Architecture overview
---------------------
The integration consists of these files:

  __init__.py   (this file)
    Registers the integration with HA, initializes the random voice store,
    installs the random-voice-aware TTS cache subclass, registers the
    tiktoktts.set_random_voices service, auto-registers the Lovelace card
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
    Also handles random voice resolution: when voice=random is requested,
    picks a voice at random from the configured language pool, then sets
    the _random_voice_active flag so the next call is also a cache miss.

  select.py
    Defines three SHARED SelectEntity subclasses - one instance each for the
    whole integration regardless of how many config entries exist:
      - LanguageSelectEntity: dropdown of all supported language codes, plus
        "All Languages" and "Random Voice" (when a pool is configured).
        Exposes random_voice_languages as a state attribute for the card.
      - VoiceSelectEntity: dropdown of voices filtered to the selected language.
        State is a friendly label; raw API code exposed via 'code' attribute.
        Shows a single "Random Voice" option when random language is selected.
      - DeviceSelectEntity: dropdown of all available media_player entities,
        populated dynamically from hass.states. Refreshes automatically when
        new devices come online (e.g. browser_mod, mobile app).
    Created on the first config entry load, skipped for subsequent entries.
    Entity IDs: select.tiktoktts_language, select.tiktoktts_voice,
                select.tiktoktts_device

  text.py
    Defines a single SHARED MessageTextEntity - one instance for the whole
    integration. Provides a native HA text input field without requiring a
    manually created input_text helper. Max length is 255 chars (HA platform
    limit). Entity ID: text.tiktoktts_message

  button.py
    Defines a single SHARED SpeakButtonEntity - one instance for the whole
    integration. When pressed it reads the current state of the language,
    voice, message, and device entities server-side and calls tts.speak
    directly in Python - no templates or scripts required.
    Automatically disables caching when random voice is selected, and sets
    the _random_voice_active flag so the cache subclass forces a miss.
    Picks the correct TTS entity (proxy or direct) by checking loaded config
    entry states, not hass.states, to avoid stale entity state issues.
    Entity ID: button.tiktoktts_speak

  frontend/__init__.py
    Registers the Lovelace card JS file as a static HTTP path and adds it
    to Lovelace's resource list automatically. No manual resource
    configuration required by the user.

  www/tiktoktts-card.js
    Custom Lovelace card providing a polished TTS control panel. Added to
    a dashboard with: type: custom:tiktoktts-card
    Includes the Random Voice settings panel (dice button) for selecting
    which language groups to include in the random voice pool.

  const.py
    All constants: API paths, field names, status codes, voice lists,
    language mappings, retry tuning, entity IDs/names, singleton flags,
    random voice constants, and attribution strings. If you need to adjust
    a behaviour (e.g. retry count, chunk size) or add a new voice, this is
    the only file you should need to touch.

Storage convention
------------------
Connection config (API mode, endpoint, voice, session_id) is stored in
entry.data (not entry.options). This keeps a single source of truth that
both config_flow.py and tts.py read from consistently. When the options flow
saves changes it calls async_update_entry() to write directly into entry.data,
then returns an empty async_create_entry() to close the flow. The update
listener below detects the change and reloads the entry.

Random voice language preferences are stored separately using HA's Store class
(homeassistant.helpers.storage), written to .storage/tiktoktts_random_voices.json.
This is the correct HA-idiomatic approach for user preference data that should
persist independently of config entries.

Singleton tracking
------------------
hass.data[DOMAIN] is used to track whether the shared select, text, and button
entities have been created. Keys defined in const.py:
  HASS_DATA_SELECT_CREATED, HASS_DATA_TEXT_CREATED, HASS_DATA_BUTTON_CREATED.
These flags are cleared when the last config entry is unloaded so that
removing and re-adding the integration recreates the entities cleanly.

Random voice cache mechanism
----------------------------
HA's TTS SpeechManager maintains an in-memory dict (mem_cache) keyed on a hash
of (message, language, options). When voice=random is passed as an option, the
cache key is always the same for a given message regardless of which random voice
is actually selected. Without intervention, HA serves the first cached audio
forever without calling async_get_tts_audio again.

To fix this, we replace mem_cache with _RandomVoiceAwareCache, a dict subclass
that overrides get() and __contains__ to return a cache miss whenever the
_random_voice_active flag is set in hass.data[DOMAIN].

The flag is set by button.py before each Speak press (dashboard path) and also
set at the end of async_get_tts_audio after resolving a random voice (automation
path). This creates a self-perpetuating mechanism: each random voice call sets
the flag so the next call is also forced to be a miss, ensuring
async_get_tts_audio is called on every tts.speak with voice=random regardless
of call source.

The cache subclass is installed by _install_random_voice_cache() which is called
both from async_setup (primary) and async_setup_entry (fallback, since HA may
skip async_setup when config entries already exist on startup).

Lovelace card registration
---------------------------
The custom Lovelace card is registered in async_setup (not async_setup_entry)
so it runs exactly once per HA startup regardless of how many config entries
exist. Registration is deferred until homeassistant_started to ensure Lovelace
resources are fully loaded. Requires 'frontend' and 'http' in manifest.json.

Credits
-------
Original integration: Philipp Luttecke (https://github.com/philipp-luettecke/tiktoktts)
Community TTS proxy:  Weilbyte (https://github.com/Weilbyte/tiktok-tts)
Fork author:          Steven Fox / sfox38 (https://github.com/sfox38/tiktoktts)
"""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, CoreState, EVENT_HOMEASSISTANT_STARTED
from homeassistant.helpers.storage import Store
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    HASS_DATA_LANGUAGE_ENTITY,
    HASS_DATA_RANDOM_LANGS,
    HASS_DATA_RANDOM_STORE,
    LOGGER,
    RANDOM_VOICE_CODE,
    SERVICE_SET_RANDOM_VOICES,
    SUPPORTED_LANGUAGES,
)
from .frontend import JSModuleRegistration

PLATFORMS: list[Platform] = [Platform.TTS, Platform.SELECT, Platform.TEXT, Platform.BUTTON]

_STORAGE_KEY     = f"{DOMAIN}_random_voices"
_STORAGE_VERSION = 1


class _RandomVoiceAwareCache(dict):
    """A dict subclass that makes HA's TTS mem_cache always miss for random voice calls.

    Installed over the SpeechManager's mem_cache dict after HA starts. Works by
    overriding get() and __contains__ to return a cache miss whenever the
    _random_voice_active flag is set in hass.data[DOMAIN].

    The flag is set by button.py before each Speak press (dashboard path) and
    also set at the end of async_get_tts_audio after resolving a random voice
    (automation path). This creates a self-perpetuating mechanism: each random
    voice call sets the flag so the next call is also forced to be a miss,
    ensuring async_get_tts_audio is called on every tts.speak with voice=random.

    All non-random cache lookups pass through to the underlying dict normally,
    so regular TTS caching is completely unaffected.

    Relies on hass.data["tts_manager"].mem_cache being a plain dict - a private
    HA internal. All methods are wrapped defensively; if HA's internals change
    the worst case is that random voice falls back to cached behavior.
    """

    def __init__(self, hass_ref: list, *args, **kwargs) -> None:
        """Store a reference to hass so we can read the active flag."""
        super().__init__(*args, **kwargs)
        self._hass_ref = hass_ref

    def _is_random_active(self) -> bool:
        """Return True if a random voice call is currently in progress."""
        try:
            hass = self._hass_ref[0]
            return hass.data.get(DOMAIN, {}).get("_random_voice_active", False)
        except Exception:
            return False

    def __contains__(self, key: object) -> bool:
        if self._is_random_active():
            return False
        return super().__contains__(key)

    def get(self, key: object, default=None) -> object:
        if self._is_random_active():
            return default
        return super().get(key, default)

    def __getitem__(self, key: object) -> object:
        if self._is_random_active():
            raise KeyError(key)
        return super().__getitem__(key)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register the Lovelace card resource and initialize the random voice store.

    Runs exactly once per HA startup regardless of how many config entries exist.
    Handles three responsibilities:

    1. Random voice store: loads the saved language pool from .storage/ and
       registers the tiktoktts.set_random_voices service so the dashboard card
       can update the pool without requiring a restart.

    2. Lovelace card: registers the card JS file and defers until
       homeassistant_started to ensure Lovelace resources are fully loaded.

    3. Random voice cache: installs _RandomVoiceAwareCache over HA's TTS
       mem_cache after homeassistant_started. Also attempted from
       async_setup_entry as a fallback for cases where async_setup is skipped.
    """
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    # Load saved random voice language pool from persistent storage.
    # Invalid language codes are filtered out so stale entries don't cause issues.
    store = Store(hass, _STORAGE_VERSION, _STORAGE_KEY)
    hass.data[DOMAIN][HASS_DATA_RANDOM_STORE] = store

    saved = await store.async_load()
    if saved and isinstance(saved.get("languages"), list):
        langs = [l for l in saved["languages"] if l in SUPPORTED_LANGUAGES]
    else:
        langs = []
    hass.data[DOMAIN][HASS_DATA_RANDOM_LANGS] = langs
    LOGGER.debug("Random voice languages loaded: %s", langs)

    async def _handle_set_random_voices(call) -> None:
        """Handle tiktoktts.set_random_voices service calls.

        Called by the dashboard card's "Save and close" button. Saves the
        updated language list to persistent storage and refreshes the language
        dropdown so "Random Voice" appears or disappears as appropriate.
        """
        languages = call.data.get("languages", [])
        valid = [l for l in languages if l in SUPPORTED_LANGUAGES]
        hass.data[DOMAIN][HASS_DATA_RANDOM_LANGS] = valid
        await store.async_save({"languages": valid})
        LOGGER.debug("Random voice languages saved: %s", valid)

        # Refresh the language dropdown entity directly via its stored reference.
        # This is more reliable than going through entity_components which can
        # return None if the component hasn't fully initialised.
        entity = hass.data.get(DOMAIN, {}).get(HASS_DATA_LANGUAGE_ENTITY)
        if entity and hasattr(entity, "async_refresh_random_voice_option"):
            await entity.async_refresh_random_voice_option()

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_RANDOM_VOICES,
        _handle_set_random_voices,
        schema=vol.Schema({
            vol.Required("languages"): vol.All(cv.ensure_list, [cv.string]),
        }),
    )

    async def _register_frontend(_event=None) -> None:
        await JSModuleRegistration(hass).async_register()
        _install_random_voice_cache(hass)

    if hass.state == CoreState.running:
        await _register_frontend()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _register_frontend)

    return True


def _install_random_voice_cache(hass: HomeAssistant) -> None:
    """Replace HA's TTS mem_cache with our random-voice-aware subclass.

    Locates the SpeechManager via hass.data["tts_manager"] and replaces its
    mem_cache dict with _RandomVoiceAwareCache. Called after homeassistant_started
    to ensure the TTS component is fully loaded.

    Guarded by a try/except so that if HA's internal structure changes in a
    future version, the integration continues to work - random voice will fall
    back to cached behavior rather than crashing.
    """
    try:
        manager = hass.data.get("tts_manager")
        if manager is None:
            LOGGER.warning("TikTokTTS: could not find TTS SpeechManager - random voice cache not installed")
            return
        existing = getattr(manager, "mem_cache", None)
        if existing is None:
            LOGGER.warning("TikTokTTS: TTS SpeechManager has no mem_cache - random voice cache not installed")
            return
        if isinstance(existing, _RandomVoiceAwareCache):
            LOGGER.debug("TikTokTTS: random voice cache already installed")
            return
        hass_ref = [hass]
        new_cache = _RandomVoiceAwareCache(hass_ref, existing)
        manager.mem_cache = new_cache
        LOGGER.debug("TikTokTTS: random voice cache installed successfully")
    except Exception:  # noqa: BLE001
        LOGGER.warning("TikTokTTS: failed to install random voice cache - voice=random may not work correctly")


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

    Also attempts to install the random voice cache here as a fallback,
    since async_setup may be skipped by HA when config entries already exist.
    The random_cache_installed flag prevents duplicate installation.
    """
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.data[DOMAIN].get("random_cache_installed"):
        async def _install_cache(_event=None) -> None:
            _install_random_voice_cache(hass)
            hass.data[DOMAIN]["random_cache_installed"] = True

        if hass.state == CoreState.running:
            await _install_cache()
        else:
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _install_cache)

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