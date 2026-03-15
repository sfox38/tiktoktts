"""TikTok TTS — Home Assistant Custom Integration.

This is the integration entry point. HA calls async_setup_entry when the user
adds the integration via the UI, and async_unload_entry when they remove it.

Architecture overview
---------------------
The integration consists of four main files:

  __init__.py   (this file)
    Registers the integration with HA, forwards setup to the TTS platform,
    and installs a config-entry update listener so that changes saved via
    the options UI (gear icon) automatically trigger a reload — no manual
    HA restart required.

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

  const.py
    All constants: API paths, field names, status codes, voice lists,
    language mappings, retry tuning, and attribution strings.
    If you need to adjust a behaviour (e.g. retry count, chunk size) or
    add a new voice, this is the only file you should need to touch.

Storage convention
------------------
Everything is stored in entry.data (not entry.options). This keeps a single
source of truth that both config_flow.py and tts.py read from consistently.
When the options flow saves changes it calls async_update_entry() to write
directly into entry.data, then returns an empty async_create_entry() to close
the flow. The update listener below detects the change and reloads the entry.

Credits
-------
Original integration: Philipp Lüttecke (https://github.com/philipp-luettecke/tiktoktts)
Community TTS proxy:  Weilbyte (https://github.com/Weilbyte/tiktok-tts)
Fork author:          Steve Fox / sfox38 (https://github.com/sfox38/tiktoktts)
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import LOGGER

# Tell HA which platforms this integration provides.
# Must be a list — a single Platform value (not in a list) is silently ignored.
PLATFORMS: list[Platform] = [Platform.TTS]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TikTok TTS from a config entry.

    Called by HA when:
      - The user completes the setup wizard for the first time
      - HA restarts and reloads all existing config entries
      - The integration is reloaded (e.g. after an options change)

    Forwards setup to the TTS platform (tts.py) and registers the update
    listener that triggers an automatic reload when options are saved.
    """
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
    reload. Delegates to HA's platform unloader which tears down the TTS
    entity cleanly.
    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when entry.data is updated.

    Triggered automatically whenever async_update_entry() is called on this
    config entry — which happens at the end of the options flow in config_flow.py.
    Reloading causes async_unload_entry + async_setup_entry to run in sequence,
    so the TikTokTTSEntity is recreated and picks up the new configuration
    values from entry.data immediately.
    """
    LOGGER.debug("Config entry updated for %s — reloading", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)