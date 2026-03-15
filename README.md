# TikTok TTS — Home Assistant Custom Integration

A Home Assistant custom integration that provides Text-to-Speech using TikTok's voice engine, supporting a wide range of languages and expressive voices.

---

## Credits & Attribution

| Role | Person / Project | Link |
|---|---|---|
| **Original integration author** | Philipp Lüttecke | [philipp-luettecke/tiktoktts](https://github.com/philipp-luettecke/tiktoktts) |
| **Community TTS proxy** | Weilbyte | [Weilbyte/tiktok-tts](https://github.com/Weilbyte/tiktok-tts) |
| **Voice list reference** | oscie57 | [oscie57/tiktok-voice](https://github.com/oscie57/tiktok-voice) |
| **Fork author** | Steven Fox | [sfox38/tiktoktts](https://github.com/sfox38/tiktoktts) |

> [!NOTE]
> This fork modernises the original integration for current Home Assistant versions, fixes some bugs, adds a UI config flow, direct API mode with endpoint fallback, automatic text chunking, and improves error handling.

---

## Installation

### HACS (Recommended)

1. Open **HACS** in your Home Assistant sidebar.
2. Click the three-dot menu (top right) and choose **Custom repositories**.
3. Paste `https://github.com/sfox38/tiktoktts` and select **Integration** as the category.
4. Click **Add**, then find **tiktoktts** in the HACS Integration list and click **Download**.
5. Restart Home Assistant.

### Manual Installation

1. Download the latest release zip from this repository and unpack it.
2. Copy the `tiktoktts` folder into your `config/custom_components/` directory. The result should be `config/custom_components/tiktoktts/`.
3. Restart Home Assistant.


---

## Configuration

After restarting, go to **Settings -> Devices & Services -> Add Integration** and search for **TikTokTTS**.

### Connection Modes

#### Community Proxy (recommended)
Uses the open-source proxy by [Weilbyte](https://github.com/Weilbyte/tiktok-tts). No TikTok account required. The default endpoint is `https://tiktok-tts.weilnet.workers.dev`.

For better reliability, you can self-host your own proxy instance and enter its URL during setup. See the [Weilbyte repo](https://github.com/Weilbyte/tiktok-tts) for instructions.

#### Direct API ⚠️
Calls TikTok's internal API directly using your TikTok session cookie.

> [!IMPORTANT]
> This uses an unofficial, reverse-engineered API and may violate TikTok's Terms of Service. Use at your own risk.

Requires a `sessionid` cookie from a logged-in TikTok browser session:
1. Log in to TikTok in your browser
2. Open Developer Tools (F12) -> Application → Cookies
3. Copy the value of the `sessionid` cookie

The integration will automatically try multiple regional TikTok endpoints if the primary one fails.

---

## Usage

### tts.speak action

```yaml
action: tts.speak
target:
  entity_id: tts.tiktoktts
data:
  media_player_entity_id: media_player.your_speaker
  message: "Hello, this is TikTok TTS"
  language: en_us
  options:
    voice: en_us_007
```

The `language` field filters available voices in the Automations editor UI. The `options.voice` field selects the specific voice. If you omit `options.voice`, the integration will use your configured default voice (if it matches the selected language) or the first available voice for the requested language.

### Supported Languages

| Code | Language |
|---|---|
| `en_us` | English (US) |
| `en_uk` | English (UK) |
| `en_au` | English (AU) |
| `fr` | French |
| `de` | German |
| `es` | Spanish |
| `es_mx` | Spanish (Mexico) |
| `pt_br` | Portuguese (Brazil) |
| `id` | Indonesian |
| `ja` | Japanese |
| `ko` | Korean |

### Changing the Default Voice

Go to **Settings -> Devices & Services -> TikTok TTS -> Configure** (gear icon). Changes take effect immediately after saving, no restart required.

---

## Troubleshooting

### Proxy endpoint is unreliable
The community Weilbyte proxy is a free, volunteer-run service and may occasionally be unavailable. For a more reliable setup, self-host your own proxy instance. See [Weilbyte/tiktok-tts](https://github.com/Weilbyte/tiktok-tts).

### Direct API: session_id expired
TikTok session IDs expire periodically. If you see errors about an invalid or expired session ID, go to the integration options and update the value from your browser cookies.

### Check the logs
Go to **Settings -> System -> Logs** and filter for `tiktoktts` to see detailed error messages.

---

## Disclaimer

This integration is not affiliated with, endorsed by, or connected to TikTok or ByteDance in any way. The direct API mode uses an unofficial, reverse-engineered endpoint. Use of the direct API mode may violate TikTok's Terms of Service.
