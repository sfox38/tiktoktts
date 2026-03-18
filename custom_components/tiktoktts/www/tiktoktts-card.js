/**
 * tiktoktts-card.js - Custom Lovelace card for the TikTok TTS integration.
 *
 * Provides a self-contained voice testing panel that reads from and writes to
 * the shared TikTokTTS helper entities without requiring any templates, scripts,
 * or additional configuration from the user.
 *
 * Entities used:
 *   select.tiktoktts_language  - language dropdown
 *   select.tiktoktts_voice     - voice dropdown (filtered by language)
 *   select.tiktoktts_device    - output media player dropdown
 *   text.tiktoktts_message     - message text input
 *   button.tiktoktts_speak     - triggers tts.speak server-side
 *
 * Design decisions:
 *   - Shadow DOM is used for style isolation so HA theme changes don't bleed in.
 *   - _isFocused flag tracks textarea focus instead of document.activeElement
 *     because Shadow DOM isolates the active element - the standard check always
 *     returns the shadow host, never the textarea inside it.
 *   - Message sync is debounced 350ms so HA isn't called on every keystroke.
 *   - Empty message sends a single space instead of "" because HA's text entity
 *     rejects truly empty strings with "required key not provided". button.py
 *     strips whitespace so the space is never actually spoken.
 *   - Voice options are rebuilt when "All Languages" is selected to avoid a
 *     stale DOM cache issue where the full voice list wasn't rendering correctly.
 *   - While API ID text is selected, only el.value is synced (not innerHTML)
 *     so the browser selection is preserved across HA state updates.
 *   - CSS variables map to HA theme variables with dark-mode fallbacks,
 *     so the card follows the user's chosen theme automatically.
 *   - The Speak button calls button.tiktoktts_speak via a HA service call so
 *     all the tts.speak logic stays server-side in button.py - no templates needed.
 *
 * Registration:
 *   This file is served by HA at /tiktoktts/tiktoktts-card.js via the static
 *   path registered in frontend/__init__.py. The Lovelace resource entry is also
 *   added automatically so users just add:
 *     type: custom:tiktoktts-card
 */

class TikTokTTSCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass            = null;
    this._isFocused       = false;  // true while the message textarea has focus
    this._voiceIdSelected = false;  // true while the API ID span text is selected

    // Fixed entity IDs for all TikTokTTS helper entities
    this._entities = {
      language: "select.tiktoktts_language",
      voice:    "select.tiktoktts_voice",
      device:   "select.tiktoktts_device",
      message:  "text.tiktoktts_message",
      speak:    "button.tiktoktts_speak",
    };
  }

  // Called by HA when the card is added to a dashboard.
  // config may contain user-provided YAML options in future - currently unused.
  setConfig(config) {
    this._config = config;
    this._render();
  }

  // Called by HA every time any entity state changes.
  // Triggers a state sync to keep the card in sync with HA.
  set hass(hass) {
    this._hass = hass;
    this._updateStates();
  }

  // -------------------------------------------------------------------------
  // Rendering
  // -------------------------------------------------------------------------

  /** Build the full shadow DOM - called once on setConfig. */
  _render() {
    this.shadowRoot.innerHTML = `
      <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }

        /* CSS custom properties.
           Backgrounds and borders use fixed dark values so the card always
           looks structured regardless of HA theme. Text and accent colours
           use HA theme variables so they follow the user's theme. */
        :host {
          --tts-bg:         #1c1c1e;
          --tts-card-bg:    #2c2c2e;
          --tts-field-bg:   #242426;
          --tts-border:     #3a3a3c;
          --tts-border-dim: #2c2c2e;
          --tts-accent:     var(--primary-color, #30d158);
          --tts-text:       var(--primary-text-color, #f2f2f7);
          --tts-text-dim:   var(--secondary-text-color, #8e8e93);
          --tts-focus:      var(--accent-color, #0a84ff);
          --tts-radius:     var(--ha-card-border-radius, 16px);
          --tts-radius-sm:  10px;
          font-family: var(--paper-font-body1_-_font-family,
                        -apple-system, "SF Pro Display", "Helvetica Neue", sans-serif);
        }

        ha-card {
          background: var(--tts-card-bg);
          border-radius: var(--tts-radius);
          padding: 20px;
          display: flex;
          flex-direction: column;
          gap: 14px;
          border: 1px solid var(--tts-border);
          box-shadow: 0 4px 24px rgba(0,0,0,0.5);
        }

        /* Card header */
        .header {
          display: flex;
          align-items: center;
          gap: 10px;
          padding-bottom: 14px;
          border-bottom: 1px solid var(--tts-border);
        }

        .header-icon {
          width: 36px;
          height: 36px;
          border-radius: 10px;
          overflow: hidden;
          flex-shrink: 0;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .header-icon img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .header-text h2 {
          font-size: 17px;
          font-weight: 600;
          color: var(--tts-text);
          letter-spacing: -0.3px;
        }

        .header-text p {
          font-size: 12px;
          color: var(--tts-text-dim);
          margin-top: 1px;
        }

        /* Generic field wrapper - label above, input row below */
        .field {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .field-label {
          font-size: 11px;
          font-weight: 600;
          color: var(--tts-text-dim);
          text-transform: uppercase;
          letter-spacing: 0.6px;
          padding-left: 2px;
        }

        /* Row containing an icon + input/select element */
        .field-row {
          display: flex;
          align-items: center;
          gap: 10px;
          background: var(--tts-field-bg);
          border-radius: var(--tts-radius-sm);
          padding: 10px 12px;
          border: 1px solid var(--tts-border);
          transition: border-color 0.15s, box-shadow 0.15s;
        }

        .field-row:focus-within {
          border-color: var(--tts-focus);
          box-shadow: 0 0 0 1px var(--tts-focus);
        }

        .field-icon {
          color: var(--tts-text-dim);
          flex-shrink: 0;
          width: 18px;
          height: 18px;
        }

        /* Shared styles for all <select> dropdowns */
        select {
          flex: 1;
          background: transparent;
          border: none;
          outline: none;
          color: var(--tts-text);
          font-size: 14px;
          font-family: inherit;
          cursor: pointer;
          min-width: 0;
        }

        select option {
          background: #2c2c2e;
          color: #f2f2f7;
        }

        /* Voice API ID - monospace, dimmed label, selectable code value */
        .voice-id {
          font-size: 11px;
          color: var(--tts-text-dim);
          padding: 4px 2px 0 2px;
          font-family: "SF Mono", "Menlo", "Monaco", monospace;
          user-select: none;
          letter-spacing: 0.2px;
        }

        .voice-id span {
          color: var(--tts-accent);
          user-select: all;
          cursor: text;
          outline: none;
        }

        /* Message field - slightly deeper background + accent border to stand out */
        .message-field .field-row {
          background: var(--tts-bg);
          border-color: var(--tts-border);
          align-items: flex-start;
          padding: 12px;
          gap: 8px;
        }

        .message-field .field-row:focus-within {
          border-color: var(--tts-focus);
          box-shadow: 0 0 0 1px var(--tts-focus);
        }

        .message-field .field-icon {
          margin-top: 2px;
        }

        .message-input-wrap {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 4px;
          min-width: 0;
        }

        textarea {
          flex: 1;
          background: transparent;
          border: none;
          outline: none;
          color: var(--tts-text);
          font-size: 14px;
          font-family: inherit;
          cursor: text;
          line-height: 1.5;
          resize: none;
          min-height: 64px;
          max-height: 160px;
          overflow-y: auto;
          white-space: pre-wrap;
          word-wrap: break-word;
          width: 100%;
        }

        .char-count {
          font-size: 10px;
          color: var(--tts-text-dim);
          text-align: right;
          transition: color 0.15s;
        }

        .char-count.warning { color: #ff9f0a; }
        .char-count.danger  { color: #ff453a; }

        /* Speak button - accent background, white text, full width */
        .speak-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          background: var(--tts-accent);
          color: #fff;
          border: none;
          border-radius: var(--tts-radius-sm);
          padding: 13px 20px;
          font-size: 15px;
          font-weight: 600;
          font-family: inherit;
          cursor: pointer;
          width: 100%;
          letter-spacing: -0.2px;
          transition: filter 0.15s, transform 0.1s, opacity 0.15s;
          margin-top: 2px;
        }

        .speak-btn:hover    { filter: brightness(1.2); }
        .speak-btn:active   { transform: scale(0.98); opacity: 0.9; }
        .speak-btn:disabled { opacity: 0.5; cursor: not-allowed; }

        .speak-btn svg {
          width: 18px;
          height: 18px;
          flex-shrink: 0;
        }

        /* Status line below the button */
        .status {
          font-size: 11px;
          color: var(--tts-text-dim);
          text-align: center;
          min-height: 14px;
          transition: color 0.2s;
        }
        .status.ok    { color: var(--tts-accent); }
        .status.error { color: #ff453a; }
      </style>

      <ha-card>
        <div class="header">
          <div class="header-icon"><img src="/tiktoktts/icon.png" alt="TikTok TTS"/></div>
          <div class="header-text">
            <h2>TikTok TTS</h2>
            <p><i>TikTok to me</i></p>
          </div>
        </div>

        <div class="field">
          <div class="field-label">Language</div>
          <div class="field-row">
            <svg class="field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 5h12M9 3v2m-3.5 9.5A7.5 7.5 0 0 0 12 19m0 0a7.5 7.5 0 0 0 7.5-7.5M12 19v2m0-9.5a3.5 3.5 0 0 1 0 7"/>
            </svg>
            <select id="sel-language"></select>
          </div>
        </div>

        <div class="field">
          <div class="field-label">Voice</div>
          <div class="field-row">
            <svg class="field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v3M8 22h8"/>
            </svg>
            <select id="sel-voice"></select>
          </div>
          <!-- Voice API ID shown in monospace below the dropdown.
               tabindex="0" kept for accessibility. -->
          <div class="voice-id" id="voice-id">API ID: <span id="voice-id-value" tabindex="0">-</span></div>
        </div>

        <div class="field">
          <div class="field-label">Speaker</div>
          <div class="field-row">
            <svg class="field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="4" y="2" width="16" height="20" rx="3"/>
              <circle cx="12" cy="14" r="3"/>
              <circle cx="12" cy="7" r="1" fill="currentColor"/>
            </svg>
            <select id="sel-device"></select>
          </div>
        </div>

        <div class="field message-field">
          <div class="field-label">Message</div>
          <div class="field-row">
            <svg class="field-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            <div class="message-input-wrap">
              <textarea id="inp-message" placeholder="Type your message…" maxlength="500" rows="3"></textarea>
              <div class="char-count" id="char-count">0 / 500</div>
            </div>
          </div>
        </div>

        <button class="speak-btn" id="btn-speak">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v3M8 22h8"/>
          </svg>
          Speak...
        </button>

        <!-- Status feedback line: shows "✓ Done" or "✗ Error" briefly after pressing Speak -->
        <div class="status" id="status"></div>
      </ha-card>
    `;

    this._bindEvents();
  }

  // -------------------------------------------------------------------------
  // Event binding
  // -------------------------------------------------------------------------

  /** Attach all event listeners after the shadow DOM is built. */
  _bindEvents() {
    const root = this.shadowRoot;

    // Select changes -> call HA select.select_option service immediately
    root.getElementById("sel-language").addEventListener("change", (e) => {
      this._callSelectService(this._entities.language, e.target.value);
    });

    root.getElementById("sel-voice").addEventListener("change", (e) => {
      this._callSelectService(this._entities.voice, e.target.value);
    });

    root.getElementById("sel-device").addEventListener("change", (e) => {
      this._callSelectService(this._entities.device, e.target.value);
    });

    // Track textarea focus with a flag rather than document.activeElement.
    // Shadow DOM isolates the active element so document.activeElement always
    // returns the shadow host, never the textarea inside it.
    const textarea = root.getElementById("inp-message");
    textarea.addEventListener("focus", () => { this._isFocused = true; });
    textarea.addEventListener("blur",  () => { this._isFocused = false; });

    // Debounced message sync: wait 600ms after the user stops typing before
    // calling HA to avoid flooding the service bus on every keystroke.
    // Sends " " (single space) for empty input because HA's text entity
    // rejects truly empty strings with "required key not provided".
    let _debounce;
    textarea.addEventListener("input", (e) => {
      const val = e.target.value;
      this._updateCharCount(val.length);
      clearTimeout(_debounce);
      _debounce = setTimeout(() => {
        this._callTextService(this._entities.message, val || " ");
      }, 600);
    });

    // Track voice ID selection state so _updateStates skips DOM rebuilds
    // while text is selected (any DOM rebuild clears browser text selection).
    // We use selectstart (fires when selection begins) rather than mousedown
    // (fires before selection exists) so the flag is accurate.
    // The flag stays true until the user clicks elsewhere in the card.
    const voiceIdSpan = root.getElementById("voice-id-value");
    voiceIdSpan.addEventListener("selectstart", () => {
      this._voiceIdSelected = true;
    });

    // Clear selection when user clicks anything else in the card.
    // pointerdown fires before focus moves so Ctrl+C still works -
    // the selection is cleared only after the pointer is pressed elsewhere,
    // giving the user time to Ctrl+C before clicking away.
    root.querySelector("ha-card").addEventListener("pointerdown", (e) => {
      const path = e.composedPath();
      const clickedVoiceId = path.some(el => el.id === "voice-id-value");
      if (clickedVoiceId) return;
      this._voiceIdSelected = false;
      const sel = window.getSelection();
      if (sel) sel.removeAllRanges();
    });

    root.getElementById("btn-speak").addEventListener("click", () => {
      this._speak();
    });
  }

  // -------------------------------------------------------------------------
  // State sync
  // -------------------------------------------------------------------------

  /** Sync all card controls to current HA entity states.
   *  Called on every hass setter invocation (i.e. on any state change in HA). */
  _updateStates() {
    if (!this._hass || !this.shadowRoot.getElementById("sel-language")) return;

    const root = this.shadowRoot;
    const e    = this._entities;

    // Language dropdown
    const langState = this._hass.states[e.language];
    if (langState) {
      this._populateSelect(
        root.getElementById("sel-language"),
        langState.attributes.options || [],
        langState.state
      );
    }

    // Voice dropdown + API ID display
    const voiceState = this._hass.states[e.voice];
    if (voiceState) {
      const options = voiceState.attributes.options || [];

      // Skip voice dropdown rebuild while the API ID span is selected -
      // any DOM rebuild immediately clears the browser text selection.
      if (!this._voiceIdSelected) {
        // Force a full DOM rebuild when "All Languages" is selected because
        // the options list changes significantly and the equality check could
        // produce a false positive, leaving the wrong voices displayed.
        const isAllLangs = langState && langState.state === "🌐 All Languages";
        this._populateSelect(
          root.getElementById("sel-voice"),
          options,
          voiceState.state,
          isAllLangs  // forceRebuild
        );

        // Update the API ID display - reads from the 'code' state attribute
        // set by VoiceSelectEntity.extra_state_attributes in select.py
        const code = voiceState.attributes.code || "";
        root.getElementById("voice-id-value").textContent = code || "-";
      }
    }

    // Device dropdown - options come from friendly names, current value is
    // also a friendly name (deviceState.state). Use requestAnimationFrame to
    // retry setting the value after the DOM settles, which fixes the issue
    // where the device reverts to the first item on page reload.
    // Device dropdown - the correct selection is guaranteed by select.py's
    // _async_refresh_devices() which preserves the restored device_id and
    // waits for late-registering players rather than falling back to index 0.
    const deviceState = this._hass.states[e.device];
    if (deviceState) {
      this._populateSelect(
        root.getElementById("sel-device"),
        deviceState.attributes.options || [],
        deviceState.state
      );
    }

    // Message textarea - only sync from HA when not focused.
    // _isFocused flag is used instead of document.activeElement (see _bindEvents).
    const msgState = this._hass.states[e.message];
    if (msgState && !this._isFocused) {
      // Treat "unknown", "unavailable", and our empty-string placeholder " "
      // as empty so the textarea shows blank rather than a stray space
      const val = (msgState.state === "unknown" ||
                   msgState.state === "unavailable" ||
                   msgState.state === " ")
        ? ""
        : msgState.state;
      const textarea = root.getElementById("inp-message");
      if (textarea.value !== val) {
        textarea.value = val;
        this._updateCharCount(val.length);
      }
    }
  }

  // -------------------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------------------

  /** Populate a <select> element with options, rebuilding the DOM only when
   *  the options list has actually changed (or when forceRebuild is true).
   *  Preserves the current selection if the value still exists in the new list.
   *
   *  @param {HTMLSelectElement} el           - The select element to update
   *  @param {string[]}          options      - New options list
   *  @param {string}            currentValue - Value to select
   *  @param {boolean}           forceRebuild - Skip equality check and always rebuild
   */
  _populateSelect(el, options, currentValue, forceRebuild = false) {
    const existing = Array.from(el.options).map(o => o.value);
    const same = !forceRebuild &&
      existing.length === options.length &&
      options.every((o, i) => o === existing[i]);

    if (!same) {
      el.innerHTML = options.map(o =>
        `<option value="${this._esc(o)}">${this._esc(o)}</option>`
      ).join("");
    }

    if (el.value !== currentValue) el.value = currentValue;
  }

  /** Update the character counter below the message textarea.
   *  Colour changes: neutral -> orange at 350 -> red at 450. */
  _updateCharCount(len) {
    const el = this.shadowRoot.getElementById("char-count");
    el.textContent = `${len} / 500`;
    el.className   = "char-count" +
      (len > 450 ? " danger" : len > 350 ? " warning" : "");
  }

  /** Call select.select_option to persist a dropdown change to HA. */
  _callSelectService(entityId, value) {
    this._hass.callService("select", "select_option", {
      entity_id: entityId,
      option:    value,
    });
  }

  /** Call text.set_value to persist the message textarea content to HA. */
  _callTextService(entityId, value) {
    this._hass.callService("text", "set_value", {
      entity_id: entityId,
      value:     value,
    });
  }

  /** Handle Speak button press.
   *  Validates the message, disables the button, calls button.press on
   *  button.tiktoktts_speak, then shows feedback and re-enables the button. */
  async _speak() {
    const btn    = this.shadowRoot.getElementById("btn-speak");
    const status = this.shadowRoot.getElementById("status");
    const msg    = this.shadowRoot.getElementById("inp-message").value.trim();

    if (!msg) {
      status.textContent = "⚠️ Please type a message first.";
      status.className   = "status error";
      setTimeout(() => { status.textContent = ""; status.className = "status"; }, 3000);
      return;
    }

    btn.disabled       = true;
    btn.textContent    = "Speaking…";
    status.textContent = "";
    status.className   = "status";

    try {
      // button.tiktoktts_speak reads all entity states server-side and calls
      // tts.speak - no templates needed in the card
      await this._hass.callService("button", "press", {
        entity_id: this._entities.speak,
      });
      status.textContent = "✓ Done";
      status.className   = "status ok";
    } catch (err) {
      status.textContent = "✗ Error - check logs";
      status.className   = "status error";
    } finally {
      // Re-enable button and clear status after 2.5s
      setTimeout(() => {
        btn.disabled = false;
        btn.innerHTML = `
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="18" height="18">
            <path d="M12 2a3 3 0 0 1 3 3v7a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v3M8 22h8"/>
          </svg>
          Speak...`;
        status.textContent = "";
        status.className   = "status";
      }, 2500);
    }
  }

  /** Escape a string for safe insertion into HTML attribute values or content. */
  _esc(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  // -------------------------------------------------------------------------
  // Lovelace card API
  // -------------------------------------------------------------------------

  /** Tells HA how many dashboard rows this card occupies. */
  getCardSize() { return 6; }

  /** Default config stub shown in the visual card editor. */
  static getStubConfig() { return {}; }
}

customElements.define("tiktoktts-card", TikTokTTSCard);

// Register with the HA card picker so the card appears in the "Add Card" UI
window.customCards = window.customCards || [];
window.customCards.push({
  type:        "tiktoktts-card",
  name:        "TikTok TTS",
  description: "Voice testing panel for the TikTok TTS integration",
  preview:     true,
});