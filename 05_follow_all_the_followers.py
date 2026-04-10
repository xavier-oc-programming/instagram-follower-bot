"""
05_follow_all_the_followers.py

Day 52 — Instagram Follower Bot
Step 5 — Follow all the followers

Includes everything from Step 4 (baseline kept as-is), plus:
- Global SCROLL_CYCLES and SCROLL_PAUSE controls
- export_visible_usernames() to CSV for auditing
- Follow loop that waits for state-change to prevent double clicks
- Counts visible "Follow" buttons after initial scroll and stops
  after following exactly that many
- More robust scrolling with progress-by-count, mixed nudges, and backoff
"""

# ==============================
# IMPORTS
# ==============================
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
)
import os
import time
import csv

# ==============================
# CONSTANTS
# ==============================
SIMILAR_ACCOUNT = "kylemadeitt"
USERNAME = "*****"  # e.g. your_instagram_username
PASSWORD = "*****"  # e.g. your_instagram_password

HOME_URL = "https://www.instagram.com/"
LOGIN_URL = "https://www.instagram.com/accounts/login/"
PROFILE_URL_TPL = "https://www.instagram.com/{username}/"

# Tunables
SCROLL_CYCLES = 4          # how many scroll passes to load followers initially
SCROLL_PAUSE = 1.1         # pause between scrolls
FOLLOW_DELAY = 1.0         # pause between follow clicks
MAX_EMPTY_RUNS = 3         # how many consecutive empty passes before stopping follow loop
NUDGE_EVERY = 5            # after this many clicks, nudge scroll to reveal more buttons

# XPaths
ACCEPT_COOKIES_XPATH = "//button[contains(text(), 'Allow all cookies') or contains(text(), 'Accept')]"
SAVE_INFO_XPATH = "//button[contains(normalize-space(.), 'Save info')]"
OK_MESSAGING_DIALOG_XPATH = "//div[@role='dialog']//*[@role='button' and normalize-space(.)='OK']"

# Auth indicators
AUTH_PRESENCE_XPATHS = [
    "//a[@href='/explore/']",
    "//a[@href='/direct/inbox/']",
    "//button[.//div[contains(@aria-label, 'Search')]]",
]
LOGIN_FORM_USERNAME_XPATH = "//input[@name='username']"

# Followers elements
FOLLOWERS_LINK_XPATH_TPL = "//a[@href='/{username}/followers/']"
FOLLOW_BUTTONS_IN_DIALOG_XPATH = ("//div[@role='dialog']//button["
                                  "normalize-space(.)='Follow' or normalize-space(.)='Seguir']")
DIALOG_XPATH = "//div[@role='dialog']"
CANCEL_POPUP_BUTTON_XPATH = "//div[@role='dialog']//button[normalize-space(.)='Cancel']"


# ==============================
# CLASS
# ==============================
class InstaFollower:
    def __init__(self, username: str, password: str, target_account: str):
        self.username = username
        self.password = password
        self.target_account = target_account
        self.follow_buttons = []
        self.scroll_box = None  # keep a handle to the scrollable node

        chrome_options = Options()
        chrome_options.add_experimental_option("detach", True)

        project_dir = os.path.dirname(os.path.abspath(__file__))
        self.profile_path = os.path.join(project_dir, "chrome_profile")
        os.makedirs(self.profile_path, exist_ok=True)
        chrome_options.add_argument(f"user-data-dir={self.profile_path}")

        prefs = {"profile.default_content_setting_values.notifications": 2}
        chrome_options.add_experimental_option("prefs", prefs)

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)

    # -----------------------------
    # Utilities
    # -----------------------------
    def element_exists(self, by, value, timeout=5):
        try:
            WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((by, value)))
            return True
        except TimeoutException:
            return False

    def clickable_and_click(self, by, value, timeout=10, pause=0.5):
        try:
            el = WebDriverWait(self.driver, timeout).until(EC.element_to_be_clickable((by, value)))
            if pause:
                time.sleep(pause)
            el.click()
            return True
        except TimeoutException:
            return False

    def get_text(self, el) -> str:
        """Safely get visible text from a WebElement (text or innerText)."""
        try:
            txt = (el.text or "").strip()
            if not txt:
                txt = (el.get_attribute("innerText") or "").strip()
            return txt
        except Exception:
            return ""

    def _count_follow_items(self) -> int:
        """Count current 'Follow/Seguir' buttons in the dialog for progress detection."""
        try:
            return len(self.driver.find_elements(
                By.XPATH,
                "//div[@role='dialog']//button[normalize-space(.)='Follow' or normalize-space(.)='Seguir']"
            ))
        except Exception:
            return 0

    def _focus_scrollbox(self, scroll_box):
        """Ensure the scrollable container has focus so key events apply to it."""
        try:
            self.driver.execute_script("arguments[0].focus();", scroll_box)
            scroll_box.click()
        except Exception:
            pass

    # -----------------------------
    # Session detection
    # -----------------------------
    def is_logged_in(self):
        self.driver.get(HOME_URL)
        if self.element_exists(By.XPATH, LOGIN_FORM_USERNAME_XPATH, timeout=5):
            return False
        for xp in AUTH_PRESENCE_XPATHS:
            if self.element_exists(By.XPATH, xp, timeout=5):
                return True
        return "instagram.com" in self.driver.current_url and not self.driver.current_url.startswith(LOGIN_URL)

    def ensure_logged_in(self):
        if self.is_logged_in():
            print("Session already active. Skipping login.")
            return

        print("No active session found. Logging in now...")
        self.driver.get(LOGIN_URL)
        self.clickable_and_click(By.XPATH, ACCEPT_COOKIES_XPATH, timeout=6, pause=0.2)

        # Flexible login field detection
        user_el = None
        for name in ("username", "email"):
            if self.element_exists(By.NAME, name, timeout=2):
                user_el = self.driver.find_element(By.NAME, name)
                break

        pass_el = None
        for name in ("password", "pass"):
            if self.element_exists(By.NAME, name, timeout=2):
                pass_el = self.driver.find_element(By.NAME, name)
                break

        if not (user_el and pass_el):
            print("Login fields not found — UI may have changed.")
            return

        user_el.clear()
        user_el.send_keys(self.username)
        pass_el.clear()
        pass_el.send_keys(self.password)
        pass_el.send_keys(Keys.ENTER)
        print("Submitted login credentials.")

        self.clickable_and_click(By.XPATH, SAVE_INFO_XPATH, timeout=10, pause=1.0)
        self.clickable_and_click(By.XPATH, OK_MESSAGING_DIALOG_XPATH, timeout=10, pause=0.5)

        if self.is_logged_in():
            print("Login successful.")
        else:
            print("Login verification failed — check browser manually.")

    # -----------------------------
    # Step 4 — Open followers and prepare scroll
    # -----------------------------
    def open_followers_modal(self):
        profile_url = PROFILE_URL_TPL.format(username=self.target_account.strip("/"))
        print(f"Navigating to profile: {profile_url}")
        self.driver.get(profile_url)

        followers_xp = FOLLOWERS_LINK_XPATH_TPL.format(username=self.target_account.strip("/"))
        if not self.clickable_and_click(By.XPATH, followers_xp, timeout=15, pause=0.5):
            print("Could not open Followers dialog. Check the account or selectors.")
            return None

        try:
            dialog = self.wait.until(EC.presence_of_element_located((By.XPATH, DIALOG_XPATH)))
            print("Followers dialog opened.")
            return dialog
        except TimeoutException:
            print("Followers dialog did not appear.")
            return None

    def find_scrollbox(self, dialog_el):
        # Preferred: element with overflow-y: hidden auto
        try:
            scroll_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div[role='dialog'] div[style*='overflow-y: hidden auto']")
                )
            )
        except TimeoutException:
            scroll_box = None

        if not scroll_box:
            # Fallback: dynamic detection
            js = """
            const root = arguments[0];
            const all = root.querySelectorAll('*');
            for (const el of all) {
                const s = getComputedStyle(el);
                const oy = s.overflowY.toLowerCase();
                if ((oy === 'auto' || oy === 'scroll' || oy === 'overlay') && el.scrollHeight > el.clientHeight + 10) {
                    return el;
                }
            }
            return null;
            """
            scroll_box = self.driver.execute_script(js, dialog_el)
            if scroll_box:
                print("Fallback scrollable container found dynamically.")
            else:
                print("Failed to locate scroll container.")
                return None

        print("Scrollable container located.")
        return scroll_box

    def scroll_followers(self, scroll_box, scroll_cycles: int = SCROLL_CYCLES, pause_between_scrolls: float = SCROLL_PAUSE):
        """
        More robust scrolling:
        - Initial settle wait
        - Progress by item-count increase OR scrollHeight increase
        - Mixed scroll nudges (setTop, small increments, END key)
        - Progressive backoff when stagnant
        """
        # Initial settle: let the first batch render
        time.sleep(max(0.6, pause_between_scrolls))

        self._focus_scrollbox(scroll_box)

        last_height = self.driver.execute_script("return arguments[0].scrollHeight;", scroll_box)
        last_count  = self._count_follow_items()

        print(f"Initial metrics → scrollHeight: {last_height}, follow-buttons: {last_count}")

        stagnant_runs = 0
        for i in range(scroll_cycles):
            # Primary jump
            self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", scroll_box)
            time.sleep(pause_between_scrolls)

            # Secondary small nudges to trigger lazy-load on some layouts
            try:
                self.driver.execute_script("arguments[0].scrollBy(0, Math.floor(arguments[0].clientHeight*0.6));", scroll_box)
                time.sleep(0.25 + pause_between_scrolls*0.25)
                self.driver.execute_script("arguments[0].scrollBy(0, Math.floor(arguments[0].clientHeight*0.4));", scroll_box)
                time.sleep(0.25 + pause_between_scrolls*0.25)
            except Exception:
                pass

            # Tertiary: END key (goes to the scrollable node if focused)
            try:
                scroll_box.send_keys(Keys.END)
            except Exception:
                pass

            # Allow network/render
            time.sleep(pause_between_scrolls)

            # Re-measure both height and item count
            new_height = self.driver.execute_script("return arguments[0].scrollHeight;", scroll_box)
            new_count  = self._count_follow_items()

            progressed = (new_height > last_height) or (new_count > last_count)

            print(f"Cycle {i+1}/{scroll_cycles} → "
                  f"scrollHeight: {last_height}→{new_height} "
                  f"buttons: {last_count}→{new_count} "
                  f"{'progress' if progressed else 'no change'}")

            if progressed:
                stagnant_runs = 0
                last_height = new_height
                last_count  = new_count
            else:
                stagnant_runs += 1
                # Progressive backoff: wait longer before next attempt
                backoff = min(2.5, 0.6 * stagnant_runs)
                time.sleep(backoff)

                # If repeatedly stagnant, try re-focusing and a top→bottom sweep
                if stagnant_runs >= 2:
                    self._focus_scrollbox(scroll_box)
                    try:
                        self.driver.execute_script("arguments[0].scrollBy(0, -Math.floor(arguments[0].clientHeight*0.2));", scroll_box)
                        time.sleep(0.3)
                        self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", scroll_box)
                    except Exception:
                        pass

                # If still no progress after a few tries, bail early
                if stagnant_runs >= 3:
                    print(f"No more followers loaded after cycle {i+1} (stagnant_runs={stagnant_runs}). Stopping early.")
                    break

        # Final diagnostics
        try:
            ch = self.driver.execute_script("return arguments[0].scrollHeight;", scroll_box)
            cl = self.driver.execute_script("return arguments[0].clientHeight;", scroll_box)
            st = self.driver.execute_script("return arguments[0].scrollTop;", scroll_box)
            total_buttons = self._count_follow_items()
            print(f"Final scrollbox metrics → scrollHeight: {ch}, clientHeight: {cl}, scrollTop: {st}, buttons: {total_buttons}")
        except Exception:
            pass

    def export_visible_usernames(self, file_path: str = "visible_followers.csv"):
        links = self.driver.find_elements(By.XPATH, "//div[@role='dialog']//a[contains(@href,'/')]")
        names = [a.text.strip() for a in links if a.text.strip()]
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["username"])
            for n in names:
                writer.writerow([n])
        print(f"Exported {len(names)} usernames to {file_path}")

    # -----------------------------
    # Step 5 — Follow loop (state-change wait logic + stop after initial count)
    # -----------------------------
    def follow_all_no_left_behind(self, max_follows: int | None = None):
        """
        Click every visible 'Follow'/'Seguir' button exactly once.
        After clicking, WAIT until the same element flips away from 'Follow'/'Seguir'
        (e.g., to 'Following'/'Siguiendo' or 'Requested'/'Solicitado') or goes stale,
        then proceed.

        If max_follows is provided, stop after that many successful follows.
        """
        FOLLOW_LABELS = ("follow", "seguir")  # pre-click state
        total_clicked = 0
        empty_runs = 0
        clicks_since_nudge = 0

        def nudge_scroll():
            try:
                self.driver.execute_script(
                    "arguments[0].scrollBy(0, Math.floor(arguments[0].clientHeight*0.6));",
                    self.scroll_box,
                )
                time.sleep(SCROLL_PAUSE)
                self.driver.execute_script(
                    "arguments[0].scrollBy(0, Math.floor(arguments[0].clientHeight*0.4));",
                    self.scroll_box,
                )
                time.sleep(SCROLL_PAUSE)
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", self.scroll_box)
                time.sleep(SCROLL_PAUSE)
            except Exception:
                pass

        while True:
            if max_follows is not None and total_clicked >= max_follows:
                print(f"Reached initial target of {max_follows} follows. Stopping.")
                break

            # Only query buttons that currently say 'Follow'/'Seguir'
            buttons = self.driver.find_elements(By.XPATH, FOLLOW_BUTTONS_IN_DIALOG_XPATH)

            if not buttons:
                empty_runs += 1
                print(f"No 'Follow' buttons visible (run {empty_runs}/{MAX_EMPTY_RUNS}).")
                if empty_runs >= MAX_EMPTY_RUNS:
                    break
                nudge_scroll()
                continue
            else:
                empty_runs = 0

            btn = buttons[0]

            # Bring into view
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                time.sleep(0.15)
            except Exception:
                pass

            # Click (normal → JS fallback)
            clicked = False
            for attempt in range(2):
                try:
                    if attempt == 0:
                        btn.click()
                    else:
                        self.driver.execute_script("arguments[0].click();", btn)
                    clicked = True
                    break
                except ElementClickInterceptedException:
                    print("Click intercepted. Attempting to dismiss popup with 'Cancel'.")
                    if self.clickable_and_click(By.XPATH, CANCEL_POPUP_BUTTON_XPATH, timeout=5, pause=0.2):
                        print("Popup dismissed. Retrying click.")
                        continue
                except StaleElementReferenceException:
                    # Row re-rendered instantly; treat as clicked and proceed to the wait.
                    clicked = True
                    break
                except Exception as e:
                    print(f"Unexpected click error: {e}")
                    break

            if not clicked:
                time.sleep(0.5)
                continue

            # Wait for the same element to stop being 'Follow'/'Seguir' OR go stale
            def state_changed(drv):
                try:
                    _ = btn.is_displayed()  # raises if stale
                    label = self.get_text(btn).lower()
                    # Success once not 'follow/seguir' anymore
                    return label not in ("follow", "seguir") and len(label) > 0
                except StaleElementReferenceException:
                    return True  # row re-rendered ⇒ consider it changed
                except Exception:
                    return False

            try:
                WebDriverWait(self.driver, 6).until(state_changed)
            except TimeoutException:
                print("Warning: button did not visibly flip after click; continuing cautiously.")
                time.sleep(0.4)

            total_clicked += 1
            clicks_since_nudge += 1
            print(f"Clicked Follow #{total_clicked}.")
            time.sleep(FOLLOW_DELAY)

            # Periodic nudge to surface more buttons deeper in the list
            if clicks_since_nudge >= NUDGE_EVERY:
                nudge_scroll()
                clicks_since_nudge = 0

        print(f"Finished. Total follows attempted: {total_clicked}")

    # -----------------------------
    # Orchestrator
    # -----------------------------
    def run(self):
        self.ensure_logged_in()
        dialog = self.open_followers_modal()
        if dialog is None:
            return

        self.scroll_box = self.find_scrollbox(dialog)
        if self.scroll_box is None:
            print("Could not find scrollable container.")
            return

        # Initial load
        self.scroll_followers(self.scroll_box, scroll_cycles=SCROLL_CYCLES, pause_between_scrolls=SCROLL_PAUSE)

        # Count how many "Follow" buttons are visible right now (post-scroll),
        # and stop after following exactly that many.
        initial_buttons = self.driver.find_elements(By.XPATH, FOLLOW_BUTTONS_IN_DIALOG_XPATH)
        initial_follow_count = len(initial_buttons)
        print(f"Initial visible 'Follow' buttons after scrolling: {initial_follow_count}")

        if initial_follow_count == 0:
            print("No 'Follow' buttons available after initial scroll.")
            return

        # Optional: audit list
        # self.export_visible_usernames("visible_followers.csv")

        # Follow pass (stop after initial_follow_count)
        self.follow_all_no_left_behind(max_follows=initial_follow_count)


# ==============================
# RUN
# ==============================
if __name__ == "__main__":
    bot = InstaFollower(
        username=USERNAME,
        password=PASSWORD,
        target_account=SIMILAR_ACCOUNT,
    )
    bot.run()
    print("Finished Step 5.")
