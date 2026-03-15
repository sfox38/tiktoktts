"""Constants for tiktoktts."""
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

# ---------------------------------------------------------------------------
# Integration identity
# ---------------------------------------------------------------------------

NAME = "TikTok TTS"
DOMAIN = "tiktoktts"
VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Attribution & credits
# ---------------------------------------------------------------------------

ORIGINAL_AUTHOR = "Philipp Lüttecke (@philipp-luettecke)"
ORIGINAL_REPO = "https://github.com/philipp-luettecke/tiktoktts"

FORK_AUTHOR = "Steven Fox (@sfox38)"
FORK_REPO = "https://github.com/sfox38/tiktoktts"

PROXY_AUTHOR = "Weilbyte"
PROXY_REPO = "https://github.com/Weilbyte/tiktok-tts"
PROXY_ATTRIBUTION = (
    f"Community TTS proxy by {PROXY_AUTHOR} — {PROXY_REPO}. "
    "Self-hosting your own instance is recommended for reliability."
)

DIRECT_API_ATTRIBUTION = (
    "Direct API mode uses TikTok's unofficial internal API, "
    "reverse-engineered by the open-source community. "
    "Use of this API may violate TikTok's Terms of Service. "
    "Use at your own risk."
)

ATTRIBUTION = (
    f"Originally by {ORIGINAL_AUTHOR} ({ORIGINAL_REPO}). "
    f"Forked and extended by {FORK_AUTHOR} ({FORK_REPO})."
)

# ---------------------------------------------------------------------------
# Config entry keys
# ---------------------------------------------------------------------------

CONF_ENDPOINT = "api_endpoint"
CONF_VOICE = "voice"
CONF_SESSION_ID = "session_id"
CONF_API_MODE = "api_mode"

# ---------------------------------------------------------------------------
# API modes
# ---------------------------------------------------------------------------

API_MODE_PROXY = "proxy"
API_MODE_DIRECT = "direct"

# ---------------------------------------------------------------------------
# Proxy API
# ---------------------------------------------------------------------------

# Default community proxy — operated by Weilbyte, may be unreliable.
# Users can self-host from: https://github.com/Weilbyte/tiktok-tts
DEFAULT_PROXY_ENDPOINT = "https://tiktok-tts.weilnet.workers.dev"

PROXY_API_PATH_GENERATE = "/api/generation"
PROXY_API_PATH_STATUS = "/api/status"
PROXY_API_FIELD_TEXT = "text"
PROXY_API_FIELD_VOICE = "voice"
PROXY_API_FIELD_DATA = "data"
PROXY_API_FIELD_AVAILABLE = "available"

# ---------------------------------------------------------------------------
# Direct TikTok API (unofficial, reverse-engineered)
# ---------------------------------------------------------------------------

# Known regional endpoints — the configured one is tried first,
# remaining ones are used as automatic fallback.
DIRECT_API_ENDPOINTS = [
    "https://api16-normal-c-useast1a.tiktokv.com",
    "https://api16-normal-useast5.us.tiktokv.com",
    "https://api16-core.tiktokv.com",
    "https://api16-normal-c-alisg.tiktokv.com",
]

DIRECT_API_PATH = "/media/api/text/speech/invoke/"

# Spoofed Android User-Agent required by TikTok's internal API
DIRECT_API_USER_AGENT = (
    "com.zhiliaoapp.musically/2022600030 "
    "(Linux; U; Android 7.1.2; es_ES; SM-G988N; Build/NRD90M;tt-ok/3.12.13.1)"
)

# TikTok API request parameter names
DIRECT_API_PARAM_SPEAKER = "text_speaker"
DIRECT_API_PARAM_TEXT = "req_text"
DIRECT_API_PARAM_MAP_TYPE = "speaker_map_type"
DIRECT_API_PARAM_AID = "aid"

# TikTok API fixed parameter values
DIRECT_API_MAP_TYPE_VALUE = 0
DIRECT_API_AID_VALUE = 1233

# TikTok API response field names
DIRECT_API_FIELD_STATUS_CODE = "status_code"
DIRECT_API_FIELD_STATUS_MSG = "status_msg"
DIRECT_API_FIELD_DATA = "data"
DIRECT_API_FIELD_AUDIO = "v_str"

# TikTok API status codes
DIRECT_API_STATUS_OK = 0
DIRECT_API_STATUS_INVALID_SESSION = 4

# Max characters per API request (TikTok enforced limit)
DIRECT_API_CHUNK_SIZE = 200

# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------

AUDIO_FORMAT = "mp3"

# ---------------------------------------------------------------------------
# Request behaviour
# ---------------------------------------------------------------------------

REQUEST_TIMEOUT = 20    # seconds
REQUEST_MAX_RETRIES = 2
REQUEST_RETRY_DELAY = 1.5  # seconds between retries

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_ENDPOINT = DEFAULT_PROXY_ENDPOINT
DEFAULT_VOICE = "en_us_001"
DEFAULT_LANG = "en_us"
DEFAULT_API_MODE = API_MODE_PROXY

# ---------------------------------------------------------------------------
# Supported voices
# Source: https://github.com/oscie57/tiktok-voice
# ---------------------------------------------------------------------------

SUPPORTED_VOICES = [
    # --- DISNEY / CHARACTER VOICES ---
    "en_us_ghostface",       # Ghost Face (Scream)
    "en_us_chewbacca",       # Chewbacca
    "en_us_c3po",            # C3PO
    "en_us_stitch",          # Stitch
    "en_us_stormtrooper",    # Stormtrooper
    "en_us_rocket",          # Rocket Raccoon

    # --- ENGLISH VOICES ---
    "en_au_001",             # English AU - Female
    "en_au_002",             # English AU - Male
    "en_uk_001",             # English UK - Male 1
    "en_uk_003",             # English UK - Male 2
    "en_us_001",             # English US - Female (Int. 1)
    "en_us_002",             # English US - Female (Int. 2)
    "en_us_006",             # English US - Male 1
    "en_us_007",             # English US - Male 2
    "en_us_009",             # English US - Male 3
    "en_us_010",             # English US - Male 4

    # --- EUROPEAN VOICES ---
    "fr_001",                # French - Male 1
    "fr_002",                # French - Male 2
    "de_001",                # German - Female
    "de_002",                # German - Male
    "es_002",                # Spanish - Male
    "es_mx_002",             # Spanish MX - Male

    # --- PORTUGUESE (BRAZIL) ---
    "br_001",                # Portuguese BR - Female 1
    "br_003",                # Portuguese BR - Female 2
    "br_004",                # Portuguese BR - Female 3
    "br_005",                # Portuguese BR - Male

    # --- ASIAN VOICES ---
    "id_001",                # Indonesian - Female
    "jp_001",                # Japanese - Female 1
    "jp_003",                # Japanese - Female 2
    "jp_005",                # Japanese - Female 3
    "jp_006",                # Japanese - Male
    "kr_002",                # Korean - Male 1
    "kr_003",                # Korean - Female
    "kr_004",                # Korean - Male 2

    # --- SINGING / EXPRESSIVE VOICES ---
    "en_female_f08_salut_damour",   # Alto
    "en_male_m03_lobby",            # Tenor
    "en_female_f08_warmy_breeze",   # Warmy Breeze
    "en_male_m03_sunshine_soon",    # Sunshine Soon

    # --- OTHER / NARRATOR VOICES ---
    "en_male_narration",     # Narrator
    "en_male_funny",         # Wacky
    "en_female_emotional",   # Peaceful / Emotional
]

# Maps language codes to the voices that belong to that language
VOICES_BY_LANGUAGE: dict[str, list[str]] = {
    "en_us": [
        "en_us_001", "en_us_002", "en_us_006", "en_us_007",
        "en_us_009", "en_us_010",
        "en_us_ghostface", "en_us_chewbacca", "en_us_c3po",
        "en_us_stitch", "en_us_stormtrooper", "en_us_rocket",
        "en_female_f08_salut_damour", "en_male_m03_lobby",
        "en_female_f08_warmy_breeze", "en_male_m03_sunshine_soon",
        "en_male_narration", "en_male_funny", "en_female_emotional",
    ],
    "en_uk": ["en_uk_001", "en_uk_003"],
    "en_au": ["en_au_001", "en_au_002"],
    "fr":    ["fr_001", "fr_002"],
    "de":    ["de_001", "de_002"],
    "es":    ["es_002"],
    "es_mx": ["es_mx_002"],
    "pt_br": ["br_001", "br_003", "br_004", "br_005"],
    "id":    ["id_001"],
    "ja":    ["jp_001", "jp_003", "jp_005", "jp_006"],
    "ko":    ["kr_002", "kr_003", "kr_004"],
}

SUPPORTED_LANGUAGES = list(VOICES_BY_LANGUAGE.keys())

SUPPORTED_OPTIONS = [CONF_VOICE]