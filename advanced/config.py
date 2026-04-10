# ============================================================
# URLs
# ============================================================
HOME_URL = "https://www.instagram.com/"
LOGIN_URL = "https://www.instagram.com/accounts/login/"
PROFILE_URL_TPL = "https://www.instagram.com/{username}/"

# ============================================================
# Selenium — driver setup
# ============================================================
# Must match your installed Chrome major version.
# Check: /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version
CHROME_VERSION = 146

WAIT_TIMEOUT = 20       # seconds — global explicit wait
SHORT_WAIT = 3          # seconds — per-candidate selector fallback wait
OPTIONAL_WAIT = 4       # seconds — optional / non-deterministic popups

# ============================================================
# Credentials keys (loaded from .env by main.py)
# ============================================================
ENV_USERNAME = "INSTAGRAM_USERNAME"
ENV_PASSWORD = "INSTAGRAM_PASSWORD"
ENV_TARGET   = "INSTAGRAM_TARGET"

# ============================================================
# Scraping / thresholds
# ============================================================
# Follow flow
SCROLL_CYCLES_FOLLOW = 4       # scroll passes when loading followers modal
SCROLL_PAUSE = 1.1             # seconds between scroll nudges
FOLLOW_DELAY = 1.0             # seconds between follow clicks
MAX_EMPTY_RUNS = 3             # consecutive empty passes before giving up
NUDGE_EVERY = 5                # clicks between periodic scroll nudges

# Unfollow flow
SCROLL_CYCLES_UNFOLLOW = 6     # scroll passes when loading following modal
UNFOLLOW_DELAY = 0.9           # seconds between unfollow actions
MAX_UNFOLLOWS = 25             # safety cap; set None to remove

# Modal animation
MODAL_SETTLE = 0.3             # seconds to wait after opening a modal

# ============================================================
# XPaths — login / session detection
# ============================================================
XPATH_ACCEPT_COOKIES = (
    "//button[contains(., 'Allow all cookies') or contains(., 'Accept')]"
)
XPATH_SAVE_INFO = "//button[contains(normalize-space(.), 'Save info')]"
XPATH_OK_MESSAGING = (
    "//div[@role='dialog']//*[@role='button' and normalize-space(.)='OK']"
)
XPATH_LOGIN_FORM_USERNAME = "//input[@name='username']"

XPATHS_AUTH_PRESENCE = [
    "//a[@href='/explore/']",
    "//a[@href='/direct/inbox/']",
    "//button[.//div[contains(@aria-label, 'Search')]]",
]

# ============================================================
# XPaths — followers modal
# ============================================================
XPATH_FOLLOWERS_LINK_TPL = "//a[@href='/{username}/followers/']"
XPATH_DIALOG = "//div[@role='dialog']"
XPATH_FOLLOW_BUTTONS = (
    "//div[@role='dialog']//button["
    "normalize-space(.)='Follow' or normalize-space(.)='Seguir']"
)
XPATH_CANCEL_POPUP = (
    "//div[@role='dialog']//button[normalize-space(.)='Cancel']"
)

# ============================================================
# CSS selectors — scroll container detection
# ============================================================
CSS_SCROLLBOX = "div[role='dialog'] div[style*='overflow-y: hidden auto']"

# ============================================================
# XPaths — following / unfollow modal
# ============================================================
XPATH_FOLLOWING_LINK_TPL = "//a[@href='/{username}/following/']"
XPATH_UNFOLLOW_TOGGLE = (
    "//div[@role='dialog']//button["
    "normalize-space(.)='Following' or normalize-space(.)='Siguiendo' or "
    "normalize-space(.)='Requested' or normalize-space(.)='Solicitado'"
    "]"
)
XPATH_CONFIRM_UNFOLLOW = (
    "//div[@role='dialog']//button["
    "normalize-space(.)='Unfollow' or normalize-space(.)='Dejar de seguir' or "
    "normalize-space(.)='Remove' or normalize-space(.)='Eliminar'"
    "]"
)
XPATH_CANCEL = (
    "//div[@role='dialog']//button["
    "normalize-space(.)='Cancel' or normalize-space(.)='Cancelar']"
)

POST_UNFOLLOW_LABELS = ("follow", "seguir", "follow back")
