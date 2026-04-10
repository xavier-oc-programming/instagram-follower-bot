"""
04_find_followers_of_the_target_account.py

Day 52 — Instagram Follower Bot
Step 4 — Find the followers of the target account

Version: profile-first navigation + robust scrollbox detection.

- Opens the target profile (not the /followers/ URL directly)
- Clicks the Followers link on the profile header
- Locates the true scrollable element inside the modal
  (explicitly matches `overflow-y: hidden auto`, with a dynamic fallback)
- Scrolls until no new entries load
- Collects visible "Follow" buttons for Step 5
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
from selenium.common.exceptions import TimeoutException
import os
import time

# ==============================
# CONSTANTS
# ==============================
SIMILAR_ACCOUNT = "kylemadeitt"
USERNAME = "*****"  # e.g. your_instagram_username
PASSWORD = "*****"  # e.g. your_instagram_password

HOME_URL = "https://www.instagram.com/"
LOGIN_URL = "https://www.instagram.com/accounts/login/"
PROFILE_URL_TPL = "https://www.instagram.com/{username}/"

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
FOLLOW_BUTTONS_IN_DIALOG_XPATH = "//div[@role='dialog']//button[normalize-space(.)='Follow']"
DIALOG_XPATH = "//div[@role='dialog']"


# ==============================
# CLASS
# ==============================
class InstaFollower:
    def __init__(self, username: str, password: str, target_account: str):
        self.username = username
        self.password = password
        self.target_account = target_account
        self.follow_buttons = []

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
    # Step 4 — Find followers
    # -----------------------------
    def find_followers(self, scroll_cycles: int = 24, pause_between_scrolls: float = 1.1):
        """Open the followers modal and scroll to load entries."""
        self.ensure_logged_in()

        profile_url = PROFILE_URL_TPL.format(username=self.target_account.strip("/"))
        print(f"Navigating to profile: {profile_url}")
        self.driver.get(profile_url)

        # Click Followers link on the profile header
        followers_xp = FOLLOWERS_LINK_XPATH_TPL.format(username=self.target_account.strip("/"))
        if not self.clickable_and_click(By.XPATH, followers_xp, timeout=15, pause=0.5):
            print("Could not open Followers dialog. Check the account or selectors.")
            return

        # Wait for the followers dialog to appear
        try:
            dialog = self.wait.until(EC.presence_of_element_located((By.XPATH, DIALOG_XPATH)))
            print("Followers dialog opened.")
        except TimeoutException:
            print("Followers dialog did not appear.")
            return

        # Locate the correct scrollable element: overflow-y: hidden auto
        try:
            scroll_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "div[role='dialog'] div[style*='overflow-y: hidden auto']"
                ))
            )
            print("Scrollable container (overflow-y: hidden auto) located.")
        except TimeoutException:
            # Fallback to dynamic discovery of any scrollable descendant
            scroll_box = self.driver.execute_script(
                """
                const dialog = arguments[0];
                const all = dialog.querySelectorAll('*');
                for (const el of all) {
                    const s = getComputedStyle(el);
                    if ((s.overflowY === 'auto' || s.overflowY === 'scroll' || s.overflowY === 'overlay')
                        && el.scrollHeight > el.clientHeight + 10) {
                        return el;
                    }
                }
                return null;
                """,
                dialog,
            )
            if scroll_box:
                print("Fallback scrollable container found dynamically.")
            else:
                print("Failed to locate scroll container.")
                return

        # Focus the scrollable container so keys and wheel go to the right node
        try:
            self.driver.execute_script("arguments[0].focus();", scroll_box)
            scroll_box.click()
        except Exception:
            pass

        # Scrolling loop with stagnation detection and nudges
        print(f"Scrolling followers dialog for up to {scroll_cycles} cycles...")
        last_height = -1
        stagnant = 0
        for i in range(scroll_cycles):
            # Primary: jump to bottom
            self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", scroll_box)
            time.sleep(pause_between_scrolls)

            new_height = self.driver.execute_script("return arguments[0].scrollHeight;", scroll_box)

            if new_height == last_height:
                stagnant += 1
                # Nudge with key and incremental scroll
                try:
                    scroll_box.send_keys(Keys.END)
                except Exception:
                    pass
                time.sleep(pause_between_scrolls)
                try:
                    self.driver.execute_script("arguments[0].scrollBy(0, arguments[0].clientHeight);", scroll_box)
                except Exception:
                    pass
                time.sleep(pause_between_scrolls)
                new_height = self.driver.execute_script("return arguments[0].scrollHeight;", scroll_box)

                if new_height == last_height and stagnant >= 2:
                    print(f"No more followers loading after cycle {i + 1}. Stopping early.")
                    break
            else:
                stagnant = 0

            last_height = new_height

        # Collect Follow buttons inside the dialog
        self.follow_buttons = self.driver.find_elements(By.XPATH, FOLLOW_BUTTONS_IN_DIALOG_XPATH)
        print(f"Collected {len(self.follow_buttons)} 'Follow' buttons for Step 5.")

        # Diagnostics
        try:
            ch = self.driver.execute_script("return arguments[0].scrollHeight;", scroll_box)
            cl = self.driver.execute_script("return arguments[0].clientHeight;", scroll_box)
            st = self.driver.execute_script("return arguments[0].scrollTop;", scroll_box)
            print(f"Scrollbox metrics → scrollHeight: {ch}, clientHeight: {cl}, scrollTop: {st}")
        except Exception:
            pass


# ==============================
# RUN
# ==============================
if __name__ == "__main__":
    bot = InstaFollower(
        username=USERNAME,
        password=PASSWORD,
        target_account=SIMILAR_ACCOUNT,
    )
    bot.find_followers(scroll_cycles=24, pause_between_scrolls=1.1)
    print("Finished Step 4.")
