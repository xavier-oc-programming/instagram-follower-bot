"""
06_unfollow_cleanup.py

Day 52 — Instagram Follower Bot
Unfollow Cleanup — open your Following list and unfollow people safely.

Design goals:
- Reuse the same project-local Chrome profile (./chrome_profile)
- Smart session detection (skip onboarding if already logged in)
- Open *your* profile → click "Following" to open the modal
- Robust scroll of the modal (mixed nudges; progress-by-count)
- Unfollow loop that:
    - Clicks only buttons that currently read "Following"/"Siguiendo"/"Requested"/"Solicitado"
    - Confirms the "Unfollow" dialog ("Unfollow"/"Dejar de seguir"/"Remove")
    - WAITS for the button to flip to "Follow"/"Seguir" or go stale before proceeding
    - Periodically nudges scroll to surface new rows
- Tunable limits (MAX_UNFOLLOWS) and delays

Note:
Instagram frequently tweaks UI. The XPaths below include multilingual/variant fallbacks.
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

# ==============================
# CONSTANTS
# ==============================
# Your login
USERNAME = "*****"  # e.g. your_instagram_username
PASSWORD = "*****"  # e.g. your_instagram_password

# The account whose "Following" list we will open.
# Usually this is your own username; keeping it separate lets you override if needed.
OWN_ACCOUNT = USERNAME

HOME_URL = "https://www.instagram.com/"
LOGIN_URL = "https://www.instagram.com/accounts/login/"
PROFILE_URL_TPL = "https://www.instagram.com/{username}/"

# Tunables
SCROLL_CYCLES = 6         # initial scroll passes in the Following modal
SCROLL_PAUSE = 1.1        # pause between scroll nudges
UNFOLLOW_DELAY = 0.9      # pause after a successful unfollow
MAX_EMPTY_RUNS = 3        # consecutive passes with no eligible buttons before stopping
NUDGE_EVERY = 7           # after this many actions, nudge scroll
MAX_UNFOLLOWS = 25        # safety cap; set None to remove limit

# XPaths — common UI bits
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

# Following modal open/scroll/selectors
FOLLOWING_LINK_XPATH_TPL = "//a[@href='/{username}/following/']"
DIALOG_XPATH = "//div[@role='dialog']"

# Buttons inside the Following modal:
# Toggle button that shows current relation (we only click if in a 'following/requested' state)
UNFOLLOW_TOGGLE_BUTTON_XPATH = (
    "//div[@role='dialog']//button["
    "normalize-space(.)='Following' or normalize-space(.)='Siguiendo' or "
    "normalize-space(.)='Requested' or normalize-space(.)='Solicitado'"
    "]"
)

# Confirmation dialog buttons
CONFIRM_UNFOLLOW_BUTTON_XPATH = (
    "//div[@role='dialog']//button["
    "normalize-space(.)='Unfollow' or normalize-space(.)='Dejar de seguir' or "
    "normalize-space(.)='Remove' or normalize-space(.)='Eliminar'"
    "]"
)
CANCEL_BUTTON_XPATH = "//div[@role='dialog']//button[normalize-space(.)='Cancel' or normalize-space(.)='Cancelar']"

# The post-unfollow target label for the toggle button
# (what we expect to see after state flips)
POST_UNFOLLOW_LABELS = ("follow", "seguir", "follow back")


# ==============================
# CLASS
# ==============================
class InstaUnfollower:
    def __init__(self, username: str, password: str, own_account: str):
        self.username = username
        self.password = password
        self.own_account = own_account
        self.scroll_box = None

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

    def _focus_scrollbox(self, scroll_box):
        """Ensure the scrollable container has focus so key events apply to it."""
        try:
            self.driver.execute_script("arguments[0].focus();", scroll_box)
            scroll_box.click()
        except Exception:
            pass

    def _count_unfollowables(self) -> int:
        """Count buttons that represent 'currently following/requested' state."""
        try:
            return len(self.driver.find_elements(By.XPATH, UNFOLLOW_TOGGLE_BUTTON_XPATH))
        except Exception:
            return 0

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
    # Open Following modal
    # -----------------------------
    def open_following_modal(self):
        profile_url = PROFILE_URL_TPL.format(username=self.own_account.strip("/"))
        print(f"Navigating to profile: {profile_url}")
        self.driver.get(profile_url)

        following_xp = FOLLOWING_LINK_XPATH_TPL.format(username=self.own_account.strip("/"))
        if not self.clickable_and_click(By.XPATH, following_xp, timeout=15, pause=0.5):
            print("Could not open Following dialog. Check the account or selectors.")
            return None

        try:
            dialog = self.wait.until(EC.presence_of_element_located((By.XPATH, DIALOG_XPATH)))
            print("Following dialog opened.")
            return dialog
        except TimeoutException:
            print("Following dialog did not appear.")
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

    def scroll_following(self, scroll_box, scroll_cycles: int = SCROLL_CYCLES, pause_between_scrolls: float = SCROLL_PAUSE):
        """
        Robust scrolling for Following modal:
        - Initial settle
        - Progress by count of 'following/requested' buttons or by scrollHeight
        - Mixed nudges + progressive backoff
        """
        time.sleep(max(0.6, pause_between_scrolls))
        self._focus_scrollbox(scroll_box)

        last_height = self.driver.execute_script("return arguments[0].scrollHeight;", scroll_box)
        last_count = self._count_unfollowables()
        print(f"Initial metrics → scrollHeight: {last_height}, following-buttons: {last_count}")

        stagnant_runs = 0
        for i in range(scroll_cycles):
            self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", scroll_box)
            time.sleep(pause_between_scrolls)

            try:
                self.driver.execute_script("arguments[0].scrollBy(0, Math.floor(arguments[0].clientHeight*0.6));", scroll_box)
                time.sleep(0.25 + pause_between_scrolls*0.25)
                self.driver.execute_script("arguments[0].scrollBy(0, Math.floor(arguments[0].clientHeight*0.4));", scroll_box)
                time.sleep(0.25 + pause_between_scrolls*0.25)
            except Exception:
                pass

            try:
                scroll_box.send_keys(Keys.END)
            except Exception:
                pass

            time.sleep(pause_between_scrolls)

            new_height = self.driver.execute_script("return arguments[0].scrollHeight;", scroll_box)
            new_count = self._count_unfollowables()
            progressed = (new_height > last_height) or (new_count > last_count)

            print(f"Cycle {i+1}/{scroll_cycles} → "
                  f"scrollHeight: {last_height}→{new_height} "
                  f"following-buttons: {last_count}→{new_count} "
                  f"{'progress' if progressed else 'no change'}")

            if progressed:
                stagnant_runs = 0
                last_height = new_height
                last_count = new_count
            else:
                stagnant_runs += 1
                backoff = min(2.5, 0.6 * stagnant_runs)
                time.sleep(backoff)
                if stagnant_runs >= 2:
                    self._focus_scrollbox(scroll_box)
                    try:
                        self.driver.execute_script("arguments[0].scrollBy(0, -Math.floor(arguments[0].clientHeight*0.2));", scroll_box)
                        time.sleep(0.3)
                        self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", scroll_box)
                    except Exception:
                        pass
                if stagnant_runs >= 3:
                    print(f"No more items loaded after cycle {i+1} (stagnant_runs={stagnant_runs}). Stopping early.")
                    break

        # Final diagnostics
        try:
            ch = self.driver.execute_script("return arguments[0].scrollHeight;", scroll_box)
            cl = self.driver.execute_script("return arguments[0].clientHeight;", scroll_box)
            st = self.driver.execute_script("return arguments[0].scrollTop;", scroll_box)
            total_btns = self._count_unfollowables()
            print(f"Final scrollbox metrics → scrollHeight: {ch}, clientHeight: {cl}, scrollTop: {st}, following-buttons: {total_btns}")
        except Exception:
            pass

    # -----------------------------
    # Unfollow loop (state-change wait)
    # -----------------------------
    def unfollow_all(self, max_unfollows: int | None = MAX_UNFOLLOWS, delay_sec: float = UNFOLLOW_DELAY):
        """
        Click 'Following'/'Siguiendo'/'Requested'/'Solicitado' buttons,
        confirm 'Unfollow', and wait until the button flips to
        'Follow'/'Seguir'/'Follow back' (or element goes stale), then continue.
        """
        total = 0
        empty_runs = 0
        clicks_since_nudge = 0

        def nudge_scroll():
            try:
                self.driver.execute_script(
                    "arguments[0].scrollBy(0, Math.floor(arguments[0].clientHeight*0.6));", self.scroll_box
                )
                time.sleep(SCROLL_PAUSE)
                self.driver.execute_script(
                    "arguments[0].scrollBy(0, Math.floor(arguments[0].clientHeight*0.4));", self.scroll_box
                )
                time.sleep(SCROLL_PAUSE)
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", self.scroll_box)
                time.sleep(SCROLL_PAUSE)
            except Exception:
                pass

        while True:
            if max_unfollows is not None and total >= max_unfollows:
                print(f"Reached max_unfollows={max_unfollows}. Stopping.")
                break

            buttons = self.driver.find_elements(By.XPATH, UNFOLLOW_TOGGLE_BUTTON_XPATH)
            if not buttons:
                empty_runs += 1
                print(f"No 'Following/Requested' buttons visible (run {empty_runs}/{MAX_EMPTY_RUNS}).")
                if empty_runs >= MAX_EMPTY_RUNS:
                    break
                nudge_scroll()
                continue
            else:
                empty_runs = 0

            btn = buttons[0]
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                time.sleep(0.15)
            except Exception:
                pass

            toggled = False
            for attempt in range(2):
                try:
                    if attempt == 0:
                        btn.click()
                    else:
                        self.driver.execute_script("arguments[0].click();", btn)
                    toggled = True
                    break
                except ElementClickInterceptedException:
                    print("Toggle click intercepted. Trying to dismiss overlay with Cancel.")
                    self.clickable_and_click(By.XPATH, CANCEL_BUTTON_XPATH, timeout=3, pause=0.1)
                except StaleElementReferenceException:
                    toggled = True
                    break
                except Exception as e:
                    print(f"Unexpected toggle click error: {e}")
                    break

            if not toggled:
                time.sleep(0.5)
                continue

            # Confirm Unfollow (dialog may appear)
            if not self.clickable_and_click(By.XPATH, CONFIRM_UNFOLLOW_BUTTON_XPATH, timeout=5, pause=0.2):
                # If no confirm appeared, the UI might have unfollowed instantly.
                # If a different confirm/cancel is present, try cancel to recover and skip.
                self.clickable_and_click(By.XPATH, CANCEL_BUTTON_XPATH, timeout=2, pause=0.1)

            # Wait for the same element to flip state or go stale
            def state_changed(drv):
                try:
                    _ = btn.is_displayed()  # raises if stale
                    label = self.get_text(btn).lower()
                    return any(label == t for t in POST_UNFOLLOW_LABELS)
                except StaleElementReferenceException:
                    return True
                except Exception:
                    return False

            try:
                WebDriverWait(self.driver, 6).until(state_changed)
            except TimeoutException:
                print("Warning: button did not visibly flip after unfollow; continuing cautiously.")
                time.sleep(0.4)

            total += 1
            clicks_since_nudge += 1
            print(f"Unfollowed #{total}.")
            time.sleep(delay_sec)

            if clicks_since_nudge >= NUDGE_EVERY:
                nudge_scroll()
                clicks_since_nudge = 0

        print(f"Finished. Total unfollows attempted: {total}")

    # -----------------------------
    # Orchestrator
    # -----------------------------
    def run(self):
        self.ensure_logged_in()

        dialog = self.open_following_modal()
        if dialog is None:
            return

        self.scroll_box = self.find_scrollbox(dialog)
        if self.scroll_box is None:
            print("Could not find scrollable container.")
            return

        # Initial load of rows
        self.scroll_following(self.scroll_box, scroll_cycles=SCROLL_CYCLES, pause_between_scrolls=SCROLL_PAUSE)

        # Unfollow pass
        self.unfollow_all(max_unfollows=MAX_UNFOLLOWS, delay_sec=UNFOLLOW_DELAY)


# ==============================
# RUN
# ==============================
if __name__ == "__main__":
    bot = InstaUnfollower(
        username=USERNAME,
        password=PASSWORD,
        own_account=OWN_ACCOUNT,
    )
    bot.run()
    print("Finished Unfollow Cleanup.")
