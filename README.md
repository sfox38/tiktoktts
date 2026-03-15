# TikTok TTS : Home Assistant Custom Integration

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

## Upgrading from the Original Integration

If you were using [philipp-luettecke/tiktoktts](https://github.com/philipp-luettecke/tiktoktts), this fork has **breaking changes** that require a clean removal before installing. You cannot simply overwrite the old files.

### Breaking Changes

| What changed | Original | This fork |
|---|---|---|
| **Configuration method** | `configuration.yaml` | UI config flow (Settings -> Devices & Services) |
| **Entity ID** | May vary | `tts.tiktoktts_proxy` (proxy mode) or `tts.tiktoktts_direct` (direct mode) |
| **Default language** | `de` (German) | `en_us` (English US) |
| **Default voice** | `de_001` | `en_us_001` |
| **`platform:` entry in YAML** | Required | **Must be removed** |

### Step 1: Remove the `platform:` entry from `configuration.yaml`

Open your `configuration.yaml` and delete the TikTok TTS platform entry. It will look something like this - remove the whole block:

```yaml
tts:
  - platform: tiktoktts
    api_endpoint: https://tiktok-tts.weilnet.workers.dev
    voice: en_us_001
```

If `tts:` was only used for TikTok TTS, remove the entire `tts:` section. If you have other TTS platforms listed under `tts:`, remove only the `tiktoktts` entry and leave the others.

### Step 2: Delete the Old Integration Files

In your `config/custom_components/` directory, delete the entire `tiktoktts/` folder and everything inside it.

### Step 3: Clear the Old TTS Cache

HA caches generated audio files and sometimes holds on to old entity state. Go to **Developer Tools -> States** and confirm no `tiktoktts` entities remain. If any do, click each one and use the delete (bin) icon to remove them.

### Step 4: Restart Home Assistant

Go to **Settings -> System -> Restart** and do a full restart (not Quick Reload).

### Step 5: Install This Fork and Reconfigure

Follow the [Installation](#installation) steps below. When you reach **Settings -> Devices & Services -> Add Integration**, you will go through the new UI setup wizard to reconfigure your endpoint and default voice.

> [!NOTE]
> Any automations that used `tts.tiktoktts` with a `platform: tiktoktts` style service call will need to be updated to use the `tts.speak` action format shown in the [Usage](#usage) section below.

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
2. Open Developer Tools (F12) -> Application -> Cookies
3. Copy the value of the `sessionid` cookie

The integration will automatically try multiple regional TikTok endpoints if the primary one fails.

---

## Usage

### Entity Names

Each configured instance creates its own entity with a fixed ID based on the connection mode:

| Mode | Friendly Name | Entity ID |
|---|---|---|
| Community Proxy | TikTokTTS Proxy | `tts.tiktoktts_proxy` |
| Direct API | TikTokTTS Direct | `tts.tiktoktts_direct` |

Both entities can coexist if you have configured both modes. Use the appropriate entity ID in your automations depending on which connection you want to use.

### tts.speak action

**Proxy mode:**
```yaml
action: tts.speak
target:
  entity_id: tts.tiktoktts_proxy
data:
  media_player_entity_id: media_player.your_speaker
  message: "Hello, this is TikTok TTS"
  language: en_us
  options:
    voice: en_us_007
```

**Direct API mode:**
```yaml
action: tts.speak
target:
  entity_id: tts.tiktoktts_direct
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


### Supported Voices

Voices are grouped by language. The **Voice ID** is the value to use in the
`options.voice` field of the `tts.speak` action.

#### 🇺🇸 English (US) `en_us`

| Voice ID | Description |
|---|---|
| `en_us_001` | Female (International 1) |
| `en_us_002` | Female (International 2) |
| `en_us_006` | Male 1 |
| `en_us_007` | Male 2 |
| `en_us_009` | Male 3 |
| `en_us_010` | Male 4 |

#### 🇬🇧 English (UK) `en_uk`

| Voice ID | Description |
|---|---|
| `en_uk_001` | Male 1 |
| `en_uk_003` | Male 2 |

#### 🇦🇺 English (AU) `en_au`

| Voice ID | Description |
|---|---|
| `en_au_001` | Female |
| `en_au_002` | Male |

#### 🇫🇷 French `fr`

| Voice ID | Description |
|---|---|
| `fr_001` | Male 1 |
| `fr_002` | Male 2 |

#### 🇩🇪 German `de`

| Voice ID | Description |
|---|---|
| `de_001` | Female |
| `de_002` | Male |

#### 🇪🇸 Spanish `es`

| Voice ID | Description |
|---|---|
| `es_002` | Male |

#### 🇲🇽 Spanish (Mexico) `es_mx`

| Voice ID | Description |
|---|---|
| `es_mx_002` | Male |

#### 🇧🇷 Portuguese (Brazil) `pt_br`

| Voice ID | Description |
|---|---|
| `br_001` | Female 1 |
| `br_003` | Female 2 |
| `br_004` | Female 3 |
| `br_005` | Male |

#### 🇮🇩 Indonesian `id`

| Voice ID | Description |
|---|---|
| `id_001` | Female |

#### 🇯🇵 Japanese `ja`

| Voice ID | Description |
|---|---|
| `jp_001` | Female 1 |
| `jp_003` | Female 2 |
| `jp_005` | Female 3 |
| `jp_006` | Male |

#### 🇰🇷 Korean `ko`

| Voice ID | Description |
|---|---|
| `kr_002` | Male 1 |
| `kr_003` | Female |
| `kr_004` | Male 2 |

#### 🎭 Character Voices `en_us`

These are novelty voices included in the English (US) language group.

| Voice ID | Description |
|---|---|
| `en_us_ghostface` | Ghost Face (Scream) |
| `en_us_chewbacca` | Chewbacca |
| `en_us_c3po` | C-3PO |
| `en_us_stitch` | Stitch |
| `en_us_stormtrooper` | Stormtrooper |
| `en_us_rocket` | Rocket Raccoon |

#### 🎵 Singing / Expressive Voices `en_us`

These voices work best with musical or expressive text.
They are included in the English (US) language group.

| Voice ID | Description |
|---|---|
| `en_female_f08_salut_damour` | Alto |
| `en_male_m03_lobby` | Tenor |
| `en_female_f08_warmy_breeze` | Warmy Breeze |
| `en_male_m03_sunshine_soon` | Sunshine Soon |
| `en_male_narration` | Narrator |
| `en_male_funny` | Wacky |
| `en_female_emotional` | Peaceful / Emotional |

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
