"""
02_create_a_class.py

Day 52 — Instagram Follower Bot
Step 2 — Create a Class

This step focuses on creating a structured, object-oriented foundation
for your Selenium Instagram automation bot.

We will:
1. Define a class called `InstaFollower`
2. Initialize the Selenium WebDriver in the constructor (__init__)
3. Create three placeholder methods:
   - login()
   - find_followers()
   - follow()
4. Instantiate the class and call these methods in order.
"""

# ------------------------------------------------------------
# IMPORTS
# ------------------------------------------------------------
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

# ------------------------------------------------------------
# CLASS DEFINITION
# ------------------------------------------------------------
class InstaFollower:
    """
    A class that encapsulates all Instagram automation behaviors.

    Responsibilities:
    - Launch and manage a Selenium browser instance.
    - Log into Instagram.
    - Find followers of a target account.
    - Follow each retrieved user.

    Attributes
    ----------
    driver : selenium.webdriver.Chrome
        The main Selenium browser driver used for automation.
    """

    def __init__(self):
        """
        Initializes the Selenium WebDriver when an InstaFollower
        object is created.

        Notes:
        - ChromeOptions are configured with 'detach=True' to prevent
          the browser from closing immediately after script execution.
        """
        chrome_options = Options()
        chrome_options.add_experimental_option("detach", True)

        self.driver = webdriver.Chrome(options=chrome_options)
        print("✅ Selenium WebDriver initialized successfully.")

    # --------------------------------------------------------
    # Placeholder Methods
    # --------------------------------------------------------

    def login(self):
        """
        Placeholder method to handle Instagram login.

        In Step 3, this will:
        - Navigate to https://www.instagram.com
        - Enter username and password
        - Handle cookie pop-ups
        - Click the login button
        """
        print("🔹 login() method called (to be implemented in Step 3)")

    def find_followers(self):
        """
        Placeholder method to locate and scroll through the followers list.

        In Step 4, this will:
        - Navigate to the target account
        - Click on the followers link
        - Scroll through the followers pop-up window
        """
        print("🔹 find_followers() method called (to be implemented in Step 4)")

    def follow(self):
        """
        Placeholder method to follow users retrieved from the list.

        In Step 5, this will:
        - Iterate through the followers list
        - Click 'Follow' buttons one by one
        """
        print("🔹 follow() method called (to be implemented in Step 5)")


# ------------------------------------------------------------
# EXECUTION (only runs when this file is executed directly)
# ------------------------------------------------------------
if __name__ == "__main__":
    bot = InstaFollower()   # Initialize the bot
    bot.login()             # Step 3 placeholder
    bot.find_followers()    # Step 4 placeholder
    bot.follow()            # Step 5 placeholder

    print("✅ Class and method structure set up successfully!")
