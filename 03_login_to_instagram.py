"""
03_login_to_instagram.py

Day 52 — Instagram Follower Bot
Step 3 — Login to Instagram (smart session detection + project-local Chrome profile)

Change in this version:
- If an active session is detected, the script returns immediately.
  It does NOT attempt onboarding or print any onboarding-related messages.
"""

# ==============================
# IMPORTS
# ==============================
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time

# ==============================
# CONSTANTS
# ==============================
SIMILAR_ACCOUNT = "chefsteps"
USERNAME = "*****"  # e.g. your_instagram_username
PASSWORD = "*****"  # e.g. your_instagram_password

HOME_URL = "https://www.instagram.com/"
LOGIN_URL = "https://www.instagram.com/accounts/login/"

# XPaths
ACCEPT_COOKIES_XPATH = "//button[contains(text(), 'Allow all cookies') or contains(text(), 'Accept')]"
SAVE_INFO_XPATH = "//button[contains(normalize-space(.), 'Save info')]"
OK_MESSAGING_DIALOG_XPATH = "//div[@role='dialog']//*[@role='button' and normalize-space(.)='OK']"

# Indicators of an authenticated session
AUTH_PRESENCE_XPATHS = [
    "//a[@href='/explore/']",
    "//a[@href='/direct/inbox/']",
    "//button[.//div[contains(@aria-label, 'Search')]]",
]

# Login form indicator
LOGIN_FORM_USERNAME_XPATH = "//input[@name='username']"


# ==============================
# CLASS
# ==============================
class InstaFollower:
    def __init__(self, username: str, password: str, target_account: str):
        self.username = username
        self.password = password
        self.target_account = target_account

        chrome_options = Options()
        chrome_options.add_experimental_option("detach", True)

        # Project-local Chrome profile (persists login, cookies, dismissed popups)
        project_dir = os.path.dirname(os.path.abspath(__file__))
        self.profile_path = os.path.join(project_dir, "chrome_profile")
        os.makedirs(self.profile_path, exist_ok=True)
        chrome_options.add_argument(f"user-data-dir={self.profile_path}")

        # Disable Chrome notifications
        chrome_prefs = {"profile.default_content_setting_values.notifications": 2}
        chrome_options.add_experimental_option("prefs", chrome_prefs)

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)

        # Onboarding sentinel — left in place for the first real login,
        # but not consulted when a session is already active.
        self.onboarding_flag = os.path.join(self.profile_path, ".onboarding_done")

    # ----------------------------------------------------------
    # Utility methods
    # ----------------------------------------------------------
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

    # ----------------------------------------------------------
    # Session detection
    # ----------------------------------------------------------
    def is_logged_in(self):
        """Return True if the current profile is already authenticated."""
        self.driver.get(HOME_URL)

        # If login form appears, not logged in
        if self.element_exists(By.XPATH, LOGIN_FORM_USERNAME_XPATH, timeout=5):
            return False

        # If any authenticated-only elements exist, assume logged in
        for xp in AUTH_PRESENCE_XPATHS:
            if self.element_exists(By.XPATH, xp, timeout=5):
                return True

        # Fallback check based on URL
        return "instagram.com" in self.driver.current_url and not self.driver.current_url.startswith(LOGIN_URL)

    # ----------------------------------------------------------
    # Core workflow
    # ----------------------------------------------------------
    def ensure_logged_in(self):
        """
        If logged in, return immediately (no onboarding, no extra messages).
        Otherwise, perform login and one-time onboarding.
        """
        if self.is_logged_in():
            print("Session already active. Skipping login.")
            return

        print("No active session found. Logging in now...")
        self.driver.get(LOGIN_URL)

        # Accept cookies if shown
        self.clickable_and_click(By.XPATH, ACCEPT_COOKIES_XPATH, timeout=6, pause=0.2)

        # Fill login form
        try:
            username_input = self.wait.until(EC.presence_of_element_located((By.NAME, "username")))
            password_input = self.wait.until(EC.presence_of_element_located((By.NAME, "password")))
            username_input.clear()
            username_input.send_keys(self.username)
            password_input.clear()
            password_input.send_keys(self.password)
            password_input.send_keys(Keys.ENTER)
            print("Submitted login credentials.")
        except TimeoutException:
            print("Login fields not found — check for UI changes.")
            return

        # One-time post-login dialogs (only on real login)
        if self.clickable_and_click(By.XPATH, SAVE_INFO_XPATH, timeout=10, pause=1.0):
            print("'Save info' clicked.")
        if self.clickable_and_click(By.XPATH, OK_MESSAGING_DIALOG_XPATH, timeout=10, pause=0.5):
            print("'Messaging tab has a new look' accepted with OK.")

        # Verify login succeeded
        if self.is_logged_in():
            print("Login successful.")
        else:
            print("Login verification failed — check browser manually.")

    # Compatibility alias
    def login(self):
        self.ensure_logged_in()


# ==============================
# RUN
# ==============================
if __name__ == "__main__":
    bot = InstaFollower(
        username=USERNAME,
        password=PASSWORD,
        target_account=SIMILAR_ACCOUNT,
    )
    bot.login()
    print("Finished Step 3.")
