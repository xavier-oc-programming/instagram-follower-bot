"""
03_login_to_instagram.py

Day 52 — Instagram Follower Bot
Persistent Chrome Profile Version

This version saves a Chrome user profile folder inside your project directory.
This keeps your login session and dismissed popups, avoiding repeated logins.
"""

# ============================================================
# IMPORTS
# ============================================================
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time

# ============================================================
# CONSTANTS
# ============================================================
SIMILAR_ACCOUNT = "chefsteps"
USERNAME = "*****"  # e.g. your_instagram_username
PASSWORD = "*****"  # e.g. your_instagram_password
LOGIN_URL = "https://www.instagram.com/accounts/login/"
ACCEPT_COOKIES_XPATH = "//button[contains(text(), 'Allow all cookies') or contains(text(), 'Accept')]"
SAVE_INFO_XPATH = "//button[contains(text(), 'Save info')]"
TURN_OFF_NOTIFICATIONS_XPATH = "//button[contains(text(), 'Not now')]"

# ============================================================
# CLASS
# ============================================================
class InstaFollower:
    def __init__(self, username: str, password: str, target_account: str):
        self.username = username
        self.password = password
        self.target_account = target_account

        chrome_options = Options()
        chrome_options.add_experimental_option("detach", True)

        # ----------------------------------------------------
        # 1. Create a dedicated Chrome profile inside this project
        # ----------------------------------------------------
        project_dir = os.path.dirname(os.path.abspath(__file__))
        profile_path = os.path.join(project_dir, "chrome_profile")

        # Ensure the folder exists
        os.makedirs(profile_path, exist_ok=True)

        # Tell Chrome to use this profile
        chrome_options.add_argument(f"user-data-dir={profile_path}")

        # Optional: disable notification popups
        chrome_prefs = {"profile.default_content_setting_values.notifications": 2}
        chrome_options.add_experimental_option("prefs", chrome_prefs)

        # Launch Chrome
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)

        print(f"Chrome launched with persistent profile at:\n{profile_path}")

    def login(self):
        """Automates login process or just opens Instagram if already logged in."""
        print("Opening Instagram login page...")
        self.driver.get(LOGIN_URL)

        # Step 1: Handle cookie popup
        try:
            cookie_button = self.wait.until(
                EC.presence_of_element_located((By.XPATH, ACCEPT_COOKIES_XPATH))
            )
            cookie_button.click()
            print("Cookie popup dismissed.")
        except TimeoutException:
            print("No cookie popup found (might already be dismissed).")

        # Step 2: Try locating the username field to see if login is required
        try:
            username_input = self.wait.until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            password_input = self.wait.until(
                EC.presence_of_element_located((By.NAME, "password"))
            )
            username_input.send_keys(self.username)
            password_input.send_keys(self.password)
            password_input.send_keys(Keys.ENTER)
            print("Submitted login credentials.")
        except TimeoutException:
            print("No login form detected — likely already logged in.")

        # Step 3: Handle "Save info" popup
        try:
            save_info_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, SAVE_INFO_XPATH))
            )
            time.sleep(2)
            save_info_button.click()
            print("'Save info' popup confirmed.")
        except TimeoutException:
            print("No 'Save info' popup appeared.")

        # Step 4: Handle "Turn on notifications" popup
        try:
            not_now_notifications = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, TURN_OFF_NOTIFICATIONS_XPATH))
            )
            time.sleep(2)
            not_now_notifications.click()
            print("'Turn on notifications' popup dismissed.")
        except TimeoutException:
            print("No 'Turn on notifications' popup appeared.")

        print("Login process complete or already active session detected.")

# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    bot = InstaFollower(
        username=USERNAME,
        password=PASSWORD,
        target_account=SIMILAR_ACCOUNT,
    )
    bot.login()
