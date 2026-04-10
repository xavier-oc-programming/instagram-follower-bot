"""
02_create_a_class.py

Day 52 — Instagram Follower Bot
Step 2 — Create a Class (including Step 1 constants)

This file consolidates:
- Step 1: Credentials and target account constants
- Step 2: An object-oriented scaffold for the bot

This version also opens the Instagram LOGIN page so you
see the site up in Selenium as soon as the script runs.
"""

# ============================================================
# IMPORTS
# ============================================================
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# ============================================================
# STEP 1 — CONSTANTS (now using your provided credentials)
# ============================================================

SIMILAR_ACCOUNT = "chefsteps"  # The target account to mirror followers from
USERNAME = "*****"  # e.g. your_instagram_username
PASSWORD = "*****"  # e.g. your_instagram_password

# Primary login URL to load immediately
LOGIN_URL = "https://www.instagram.com/accounts/login/"

# Optional: if you already inspected cookie popups, keep XPaths here
ACCEPT_COOKIES_XPATH = "//button[contains(., 'Allow all cookies') or contains(., 'Accept')]"

# ============================================================
# STEP 2 — CLASS SCAFFOLD
# ============================================================

class InstaFollower:
    """
    Encapsulates the Selenium automation for Instagram.

    Responsibilities:
    - Start/own a Selenium driver session
    - Log in to Instagram (Step 3)
    - Find followers of a target account (Step 4)
    - Follow users (Step 5)
    """

    def __init__(self, username: str, password: str, target_account: str):
        """
        Initialize the WebDriver and store configuration.

        Parameters
        ----------
        username : str
            Instagram username for the automation account.
        password : str
            Instagram password for the automation account.
        target_account : str
            The public account whose followers we will try to follow.
        """
        self.username = username
        self.password = password
        self.target_account = target_account

        chrome_options = Options()
        # Keep the browser open after the script finishes (useful for debugging)
        chrome_options.add_experimental_option("detach", True)
        # Optional: disable notifications/popups via Chrome prefs
        chrome_prefs = {"profile.default_content_setting_values.notifications": 2}
        chrome_options.add_experimental_option("prefs", chrome_prefs)

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)  # explicit waits

        print("WebDriver initialized.")

    # --------------------------------------------------------
    # Step 3 — minimal implementation to open the login page
    # --------------------------------------------------------
    def login(self):
        """
        Open the Instagram login page so the site is up in Selenium.

        Next iteration will:
        - Handle cookie popups
        - Enter USERNAME and PASSWORD
        - Submit login
        """
        self.driver.get(LOGIN_URL)
        # Wait for a known element on the login page to ensure it loaded
        try:
            self.wait.until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            print("Instagram login page loaded.")
        except TimeoutException:
            print("Warning: Login page did not load within the expected time.")

    # --------------------------------------------------------
    # Step 4 placeholder — will be implemented next
    # --------------------------------------------------------
    def find_followers(self):
        print("find_followers() called — implement in Step 4.")

    # --------------------------------------------------------
    # Step 5 placeholder — will be implemented next
    # --------------------------------------------------------
    def follow(self):
        print("follow() called — implement in Step 5.")

# ============================================================
# RUN (only when executing this file directly)
# ============================================================
if __name__ == "__main__":
    bot = InstaFollower(
        username=USERNAME,
        password=PASSWORD,
        target_account=SIMILAR_ACCOUNT,
    )

    # This will open the Instagram login page in Selenium.
    bot.login()
    bot.find_followers()
    bot.follow()

    print("Script executed. The Instagram login page should be open in the browser.")
