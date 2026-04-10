"""
advanced/bot.py

InstaBot — Selenium automation for the Instagram follower/unfollow bot.

Handles all browser interaction:
  - Driver setup (undetected-chromedriver)
  - Session detection and login
  - Followers modal: scroll + follow loop
  - Following modal: scroll + unfollow loop

Pure logic — no print() in utility paths, no direct file writes, no UI.
Raises exceptions on failure; does NOT sys.exit().
"""

import os
import time
from pathlib import Path

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
)

import config


class InstaBot:
    """
    Automates Instagram follow/unfollow flows via Selenium.

    Responsibilities
    ----------------
    - Launch and manage an undetected-chromedriver browser session.
    - Detect and reuse an existing login session (persistent Chrome profile).
    - Log in with credentials from the environment.
    - Open the target account's followers modal, scroll it, and follow users.
    - Open the own account's following modal, scroll it, and unfollow users.
    """

    def __init__(self, username: str, password: str, target_account: str):
        self.username = username
        self.password = password
        self.target_account = target_account
        self.scroll_box = None

        options = uc.ChromeOptions()
        options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_setting_values.geolocation": 1,
        })

        profile_path = str(Path(__file__).parent / "chrome_profile")
        os.makedirs(profile_path, exist_ok=True)
        options.add_argument(f"--user-data-dir={profile_path}")

        self.driver = uc.Chrome(options=options, version_main=config.CHROME_VERSION)
        self.wait = WebDriverWait(self.driver, config.WAIT_TIMEOUT)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _js_click(self, element):
        """Click via normal click first; fall back to JS if intercepted."""
        try:
            element.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", element)

    def element_exists(self, by, value, timeout=5) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return True
        except TimeoutException:
            return False

    def _safe_click(self, by, value, timeout=10, pause=0.5) -> bool:
        """Wait for element to be clickable, then click it. Returns success."""
        try:
            el = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            if pause:
                time.sleep(pause)
            self._js_click(el)
            return True
        except TimeoutException:
            return False

    def get_text(self, el) -> str:
        """Safely return visible text from a WebElement."""
        try:
            txt = (el.text or "").strip()
            if not txt:
                txt = (el.get_attribute("innerText") or "").strip()
            return txt
        except Exception:
            return ""

    def _focus_scrollbox(self, scroll_box):
        try:
            self.driver.execute_script("arguments[0].focus();", scroll_box)
            scroll_box.click()
        except Exception:
            pass

    def _find_scrollbox(self, dialog_el):
        """Locate the scrollable list container inside a dialog."""
        try:
            box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, config.CSS_SCROLLBOX)
                )
            )
            return box
        except TimeoutException:
            pass

        # JS fallback — find any descendant with actual scroll content
        js = """
        const root = arguments[0];
        const all = root.querySelectorAll('*');
        for (const el of all) {
            const s = getComputedStyle(el);
            const oy = s.overflowY.toLowerCase();
            if ((oy === 'auto' || oy === 'scroll' || oy === 'overlay')
                && el.scrollHeight > el.clientHeight + 10) {
                return el;
            }
        }
        return null;
        """
        box = self.driver.execute_script(js, dialog_el)
        return box  # None if not found

    def _scroll_modal(self, scroll_box, scroll_cycles: int, pause: float,
                      count_fn) -> None:
        """
        Generic modal scroll loop.

        Scrolls `scroll_cycles` times, detects stagnation by comparing
        both scrollHeight and the result of `count_fn()`, applies
        progressive backoff and mixed nudges.
        """
        time.sleep(max(0.6, pause))
        self._focus_scrollbox(scroll_box)

        last_height = self.driver.execute_script(
            "return arguments[0].scrollHeight;", scroll_box
        )
        last_count = count_fn()
        print(f"Scroll start — height: {last_height}, items: {last_count}")

        stagnant = 0
        for i in range(scroll_cycles):
            self.driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight;", scroll_box
            )
            time.sleep(pause)

            try:
                self.driver.execute_script(
                    "arguments[0].scrollBy(0, Math.floor(arguments[0].clientHeight*0.6));",
                    scroll_box,
                )
                time.sleep(0.25 + pause * 0.25)
                self.driver.execute_script(
                    "arguments[0].scrollBy(0, Math.floor(arguments[0].clientHeight*0.4));",
                    scroll_box,
                )
                time.sleep(0.25 + pause * 0.25)
            except Exception:
                pass

            try:
                scroll_box.send_keys(Keys.END)
            except Exception:
                pass

            time.sleep(pause)

            new_height = self.driver.execute_script(
                "return arguments[0].scrollHeight;", scroll_box
            )
            new_count = count_fn()
            progressed = (new_height > last_height) or (new_count > last_count)

            print(
                f"Cycle {i+1}/{scroll_cycles} — "
                f"height: {last_height}→{new_height}  "
                f"items: {last_count}→{new_count}  "
                f"{'progress' if progressed else 'no change'}"
            )

            if progressed:
                stagnant = 0
                last_height = new_height
                last_count = new_count
            else:
                stagnant += 1
                time.sleep(min(2.5, 0.6 * stagnant))
                if stagnant >= 2:
                    self._focus_scrollbox(scroll_box)
                    try:
                        self.driver.execute_script(
                            "arguments[0].scrollBy(0, -Math.floor(arguments[0].clientHeight*0.2));",
                            scroll_box,
                        )
                        time.sleep(0.3)
                        self.driver.execute_script(
                            "arguments[0].scrollTop = arguments[0].scrollHeight;",
                            scroll_box,
                        )
                    except Exception:
                        pass
                if stagnant >= 3:
                    print(f"Stagnant after cycle {i+1}. Stopping scroll early.")
                    break

    # ------------------------------------------------------------------ #
    # Session detection & login
    # ------------------------------------------------------------------ #

    def is_logged_in(self) -> bool:
        self.driver.get(config.HOME_URL)
        if self.element_exists(By.XPATH, config.XPATH_LOGIN_FORM_USERNAME, timeout=5):
            return False
        for xp in config.XPATHS_AUTH_PRESENCE:
            if self.element_exists(By.XPATH, xp, timeout=5):
                return True
        return (
            "instagram.com" in self.driver.current_url
            and not self.driver.current_url.startswith(config.LOGIN_URL)
        )

    def login(self) -> None:
        """Log in if no active session exists; skip otherwise."""
        if self.is_logged_in():
            print("Session active — skipping login.")
            return

        print("No active session. Logging in...")
        self.driver.get(config.LOGIN_URL)
        self._safe_click(By.XPATH, config.XPATH_ACCEPT_COOKIES, timeout=6, pause=0.2)

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
            raise RuntimeError("Login fields not found — Instagram UI may have changed.")

        user_el.clear()
        user_el.send_keys(self.username)
        pass_el.clear()
        pass_el.send_keys(self.password)
        pass_el.send_keys(Keys.ENTER)
        print("Credentials submitted.")

        self._safe_click(By.XPATH, config.XPATH_SAVE_INFO, timeout=10, pause=1.0)
        self._safe_click(By.XPATH, config.XPATH_OK_MESSAGING, timeout=10, pause=0.5)

        if not self.is_logged_in():
            raise RuntimeError("Login verification failed — check the browser manually.")
        print("Login successful.")

    # ------------------------------------------------------------------ #
    # Follow flow
    # ------------------------------------------------------------------ #

    def _count_follow_buttons(self) -> int:
        try:
            return len(self.driver.find_elements(By.XPATH, config.XPATH_FOLLOW_BUTTONS))
        except Exception:
            return 0

    def open_followers_modal(self):
        """Navigate to the target profile and open its Followers dialog."""
        url = config.PROFILE_URL_TPL.format(username=self.target_account.strip("/"))
        print(f"Opening profile: {url}")
        self.driver.get(url)

        xp = config.XPATH_FOLLOWERS_LINK_TPL.format(
            username=self.target_account.strip("/")
        )
        if not self._safe_click(By.XPATH, xp, timeout=15, pause=0.5):
            raise RuntimeError("Could not open Followers dialog — check XPath or account name.")

        try:
            dialog = self.wait.until(
                EC.presence_of_element_located((By.XPATH, config.XPATH_DIALOG))
            )
            print("Followers dialog open.")
            return dialog
        except TimeoutException:
            raise RuntimeError("Followers dialog did not appear.")

    def scroll_followers(self, scroll_box) -> None:
        self._scroll_modal(
            scroll_box,
            scroll_cycles=config.SCROLL_CYCLES_FOLLOW,
            pause=config.SCROLL_PAUSE,
            count_fn=self._count_follow_buttons,
        )

    def follow_all(self, max_follows: int | None = None) -> int:
        """
        Click every visible Follow button.

        After each click waits for the button to leave the 'Follow/Seguir'
        state (or go stale) before proceeding.

        Returns the total number of follows clicked.
        """
        total = 0
        empty_runs = 0
        clicks_since_nudge = 0

        def nudge():
            try:
                self.driver.execute_script(
                    "arguments[0].scrollBy(0, Math.floor(arguments[0].clientHeight*0.6));",
                    self.scroll_box,
                )
                time.sleep(config.SCROLL_PAUSE)
                self.driver.execute_script(
                    "arguments[0].scrollBy(0, Math.floor(arguments[0].clientHeight*0.4));",
                    self.scroll_box,
                )
                time.sleep(config.SCROLL_PAUSE)
                self.driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight;", self.scroll_box
                )
                time.sleep(config.SCROLL_PAUSE)
            except Exception:
                pass

        while True:
            if max_follows is not None and total >= max_follows:
                print(f"Reached follow target ({max_follows}). Stopping.")
                break

            buttons = self.driver.find_elements(By.XPATH, config.XPATH_FOLLOW_BUTTONS)
            if not buttons:
                empty_runs += 1
                print(f"No Follow buttons visible ({empty_runs}/{config.MAX_EMPTY_RUNS}).")
                if empty_runs >= config.MAX_EMPTY_RUNS:
                    break
                nudge()
                continue
            else:
                empty_runs = 0

            btn = buttons[0]
            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", btn
                )
                time.sleep(0.15)
            except Exception:
                pass

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
                    self._safe_click(
                        By.XPATH, config.XPATH_CANCEL_POPUP, timeout=5, pause=0.2
                    )
                except StaleElementReferenceException:
                    clicked = True
                    break
                except Exception:
                    break

            if not clicked:
                time.sleep(0.5)
                continue

            def follow_state_changed(drv):
                try:
                    _ = btn.is_displayed()
                    label = self.get_text(btn).lower()
                    return label not in ("follow", "seguir") and len(label) > 0
                except StaleElementReferenceException:
                    return True
                except Exception:
                    return False

            try:
                WebDriverWait(self.driver, 6).until(follow_state_changed)
            except TimeoutException:
                time.sleep(0.4)

            total += 1
            clicks_since_nudge += 1
            print(f"Followed #{total}.")
            time.sleep(config.FOLLOW_DELAY)

            if clicks_since_nudge >= config.NUDGE_EVERY:
                nudge()
                clicks_since_nudge = 0

        print(f"Follow pass complete. Total: {total}")
        return total

    def run_follow(self) -> None:
        """Full follow flow: login → open modal → scroll → follow."""
        self.login()
        dialog = self.open_followers_modal()

        self.scroll_box = self._find_scrollbox(dialog)
        if self.scroll_box is None:
            raise RuntimeError("Could not locate the scrollable container in followers modal.")

        self.scroll_followers(self.scroll_box)

        initial_count = self._count_follow_buttons()
        print(f"Follow buttons visible after scroll: {initial_count}")
        if initial_count == 0:
            print("No Follow buttons found. Exiting.")
            return

        self.follow_all(max_follows=initial_count)

    # ------------------------------------------------------------------ #
    # Unfollow flow
    # ------------------------------------------------------------------ #

    def _count_unfollow_buttons(self) -> int:
        try:
            return len(self.driver.find_elements(By.XPATH, config.XPATH_UNFOLLOW_TOGGLE))
        except Exception:
            return 0

    def open_following_modal(self, own_account: str):
        """Navigate to own profile and open the Following dialog."""
        url = config.PROFILE_URL_TPL.format(username=own_account.strip("/"))
        print(f"Opening profile: {url}")
        self.driver.get(url)

        xp = config.XPATH_FOLLOWING_LINK_TPL.format(username=own_account.strip("/"))
        if not self._safe_click(By.XPATH, xp, timeout=15, pause=0.5):
            raise RuntimeError("Could not open Following dialog — check XPath or account name.")

        try:
            dialog = self.wait.until(
                EC.presence_of_element_located((By.XPATH, config.XPATH_DIALOG))
            )
            print("Following dialog open.")
            return dialog
        except TimeoutException:
            raise RuntimeError("Following dialog did not appear.")

    def scroll_following(self, scroll_box) -> None:
        self._scroll_modal(
            scroll_box,
            scroll_cycles=config.SCROLL_CYCLES_UNFOLLOW,
            pause=config.SCROLL_PAUSE,
            count_fn=self._count_unfollow_buttons,
        )

    def unfollow_all(self, max_unfollows: int | None = None) -> int:
        """
        Click every Following/Requested toggle, confirm the Unfollow dialog,
        and wait for the button to flip back to Follow.

        Returns the total number of unfollows performed.
        """
        total = 0
        empty_runs = 0
        clicks_since_nudge = 0

        def nudge():
            try:
                self.driver.execute_script(
                    "arguments[0].scrollBy(0, Math.floor(arguments[0].clientHeight*0.6));",
                    self.scroll_box,
                )
                time.sleep(config.SCROLL_PAUSE)
                self.driver.execute_script(
                    "arguments[0].scrollBy(0, Math.floor(arguments[0].clientHeight*0.4));",
                    self.scroll_box,
                )
                time.sleep(config.SCROLL_PAUSE)
                self.driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight;", self.scroll_box
                )
                time.sleep(config.SCROLL_PAUSE)
            except Exception:
                pass

        cap = max_unfollows if max_unfollows is not None else config.MAX_UNFOLLOWS

        while True:
            if cap is not None and total >= cap:
                print(f"Reached unfollow cap ({cap}). Stopping.")
                break

            buttons = self.driver.find_elements(By.XPATH, config.XPATH_UNFOLLOW_TOGGLE)
            if not buttons:
                empty_runs += 1
                print(f"No Following buttons visible ({empty_runs}/{config.MAX_EMPTY_RUNS}).")
                if empty_runs >= config.MAX_EMPTY_RUNS:
                    break
                nudge()
                continue
            else:
                empty_runs = 0

            btn = buttons[0]
            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", btn
                )
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
                    self._safe_click(By.XPATH, config.XPATH_CANCEL, timeout=3, pause=0.1)
                except StaleElementReferenceException:
                    toggled = True
                    break
                except Exception:
                    break

            if not toggled:
                time.sleep(0.5)
                continue

            time.sleep(config.MODAL_SETTLE)
            if not self._safe_click(
                By.XPATH, config.XPATH_CONFIRM_UNFOLLOW, timeout=5, pause=0.2
            ):
                self._safe_click(By.XPATH, config.XPATH_CANCEL, timeout=2, pause=0.1)

            def unfollow_state_changed(drv):
                try:
                    _ = btn.is_displayed()
                    label = self.get_text(btn).lower()
                    return any(label == t for t in config.POST_UNFOLLOW_LABELS)
                except StaleElementReferenceException:
                    return True
                except Exception:
                    return False

            try:
                WebDriverWait(self.driver, 6).until(unfollow_state_changed)
            except TimeoutException:
                time.sleep(0.4)

            total += 1
            clicks_since_nudge += 1
            print(f"Unfollowed #{total}.")
            time.sleep(config.UNFOLLOW_DELAY)

            if clicks_since_nudge >= config.NUDGE_EVERY:
                nudge()
                clicks_since_nudge = 0

        print(f"Unfollow pass complete. Total: {total}")
        return total

    def run_unfollow(self, own_account: str) -> None:
        """Full unfollow flow: login → open modal → scroll → unfollow."""
        self.login()
        dialog = self.open_following_modal(own_account)

        self.scroll_box = self._find_scrollbox(dialog)
        if self.scroll_box is None:
            raise RuntimeError("Could not locate the scrollable container in following modal.")

        self.scroll_following(self.scroll_box)
        self.unfollow_all()

    # ------------------------------------------------------------------ #
    # Teardown
    # ------------------------------------------------------------------ #

    def quit(self) -> None:
        try:
            self.driver.quit()
        except Exception:
            pass
