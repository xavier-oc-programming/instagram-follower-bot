# Instagram Follower Bot

A Selenium bot that logs into Instagram, mass-follows the followers of a target account, and cleans up with a smart unfollow script.

Given a target Instagram account (e.g. a competitor or similar creator), the bot opens their followers modal, scrolls through it to load entries, and clicks every visible **Follow** button — waiting for each button to flip to "Following" before moving on. A companion unfollow pass opens your own Following list and systematically unfollows everyone up to a configurable cap. For example: point it at `@chefsteps`, and it will follow hundreds of food-interested users who are likely to follow back.

This repo contains two builds. The **original build** is a direct consolidation of the course step files — verbatim code with only credential redaction and a path fix. The **advanced build** replaces standard Selenium with `undetected-chromedriver` (bypasses Instagram's bot fingerprinting), extracts every constant and XPath to `config.py`, and refactors the code into a clean `InstaBot` class with shared scroll and click helpers — so a single XPath change in `config.py` propagates everywhere.

No external API is used. The bot interacts directly with the Instagram web interface via Selenium. Instagram credentials are required and loaded from a `.env` file.

---

## Table of Contents

0. [Prerequisites](#0-prerequisites)
1. [Quick start](#1-quick-start)
2. [Builds comparison](#2-builds-comparison)
3. [Usage](#3-usage)
4. [Data flow](#4-data-flow)
5. [Features](#5-features)
6. [Navigation flow](#6-navigation-flow)
7. [Architecture](#7-architecture)
8. [Module reference](#8-module-reference)
9. [Configuration reference](#9-configuration-reference)
10. [Environment variables](#10-environment-variables)
11. [Design decisions](#11-design-decisions)
12. [Course context](#12-course-context)
13. [Dependencies](#13-dependencies)

---

## 0. Prerequisites

- A **dedicated / throwaway Instagram account** — do not use your personal account.
  Instagram may temporarily restrict accounts that follow many people quickly.
- Python 3.10+ (uses `X | Y` union type hints)
- Google Chrome installed — match `CHROME_VERSION` in `advanced/config.py` to your major version.

---

## 1. Quick start

```bash
# Clone
git clone https://github.com/xavier-oc-programming/instagram-follower-bot.git
cd instagram-follower-bot

# Install dependencies
pip install -r requirements.txt

# Configure credentials
cp .env.example .env
# Edit .env with your Instagram username, password, and target account

# Run
python menu.py
```

---

## 2. Builds comparison

| Feature | Original | Advanced |
|---|---|---|
| Driver | `selenium.webdriver.Chrome` | `undetected-chromedriver` |
| Bot-detection bypass | No | Yes |
| Credentials | Hardcoded `*****` | `.env` file |
| Constants | Inline | `advanced/config.py` |
| XPaths | Inline | Grouped in `config.py` |
| Scroll logic | Per-method | Shared `_scroll_modal()` |
| Click logic | Inline fallback | `_js_click()` helper |
| Unfollow | Separate class | `run_unfollow()` method |
| Mode selection | Edit source | Interactive menu prompt |

---

## 3. Usage

### Menu

```
python menu.py
```

```
  _____                _                           ____        _
 |_   _|              | |                         |  _ \      | |
   ...                              Day 52 — Instagram Follower Bot

  [1] Original  — course script (follow flow)
  [2] Advanced  — refactored bot with follow + unfollow modes
  [q] Quit
```

### Advanced mode prompt

```
Instagram Follower Bot — Advanced Build
----------------------------------------
  [1] Follow followers of a target account
  [2] Unfollow everyone (cleanup pass)

Select mode (1 / 2): 1
Enter target account username: chefsteps
Opening profile: https://www.instagram.com/chefsteps/
Followers dialog open.
Scroll start — height: 480, items: 12
Cycle 1/4 — height: 480→1340  items: 12→38  progress
...
Follow buttons visible after scroll: 38
Followed #1.
Followed #2.
...
Follow pass complete. Total: 38
```

---

## 4. Data flow

```
Input (.env)
    INSTAGRAM_USERNAME / PASSWORD / TARGET
         │
         ▼
    InstaBot.__init__()
    ├── undetected-chromedriver (Chrome, version 146)
    └── Persistent Chrome profile (./advanced/chrome_profile/)
         │
         ▼
    login()  ──► is_logged_in() ──► skip if session active
         │         else ──► fill form ──► handle post-login dialogs
         │
         ├──[Follow mode]──► open_followers_modal()
         │                       ──► scroll_followers()
         │                       ──► follow_all()
         │                             for each Follow button:
         │                               click → wait state-change
         │
         └──[Unfollow mode]──► open_following_modal()
                                  ──► scroll_following()
                                  ──► unfollow_all()
                                        for each Following button:
                                          click toggle → confirm → wait state-change
```

---

## 5. Features

### Both builds
- Persistent Chrome profile — login session survives restarts
- Smart session detection — skips login if already authenticated
- Followers modal scrolling — loads all entries before following
- Follow loop with state-change wait — no double-clicks
- Periodic nudge scrolling — surfaces buttons deep in the list
- ElementClickInterceptedException recovery via JS click fallback
- StaleElementReferenceException handling — treats re-render as success
- Unfollow cleanup script — opens Following list, unfollows with confirmation

### Advanced only
- `undetected-chromedriver` — removes Selenium fingerprint that triggers Instagram bot detection
- `ChromeOptions` prefs to suppress notification and geolocation dialogs
- Shared `_scroll_modal()` — one scroll loop for both follow and unfollow flows
- Shared `_js_click()` helper — consistent click pattern across all buttons
- All XPaths and tunables in `config.py` — one file to update when Instagram DOM changes
- `.env`-based credentials — no hardcoded values
- `InstaBot.quit()` called in `finally` block — clean browser teardown

---

## 6. Navigation flow

```
menu.py
├── [1] original/main.py
│         InstaFollower.run()
│         ├── ensure_logged_in()
│         ├── open_followers_modal()
│         ├── find_scrollbox() → scroll_followers()
│         └── follow_all_no_left_behind()
│
└── [2] advanced/main.py
          ├── [1] Follow mode
          │     InstaBot.run_follow()
          │     ├── login()
          │     ├── open_followers_modal()
          │     ├── _find_scrollbox() → scroll_followers()
          │     └── follow_all()
          │
          └── [2] Unfollow mode
                InstaBot.run_unfollow(own_account)
                ├── login()
                ├── open_following_modal()
                ├── _find_scrollbox() → scroll_following()
                └── unfollow_all()
```

---

## 7. Architecture

```
instagram-follower-bot/
│
├── menu.py                   # Top-level menu — launches original or advanced
├── art.py                    # LOGO ASCII art
├── requirements.txt          # pip dependencies + Python version note
├── .env.example              # Template for credentials
├── .gitignore
│
├── docs/
│   └── COURSE_NOTES.md       # Original exercise description + key challenges
│
├── original/
│   └── main.py               # Verbatim course code (steps 01–06 merged)
│                             # InstaFollower + InstaUnfollower classes
│
└── advanced/
    ├── config.py             # All constants, tunables, XPaths, CSS selectors
    ├── bot.py                # InstaBot class — all Selenium logic
    ├── main.py               # Orchestrator — loads .env, presents mode menu
    └── chrome_profile/       # Persistent Chrome session (gitignored)
```

---

## 8. Module reference

### `advanced/bot.py` — class `InstaBot`

| Method | Returns | Description |
|---|---|---|
| `__init__(username, password, target_account)` | — | Init undetected-chromedriver with persistent Chrome profile |
| `_js_click(element)` | — | Click normally, fall back to JS click if intercepted |
| `element_exists(by, value, timeout)` | `bool` | Presence check with short timeout |
| `_safe_click(by, value, timeout, pause)` | `bool` | Wait for clickable + JS click |
| `get_text(el)` | `str` | Safe text extraction (`.text` or `innerText`) |
| `_focus_scrollbox(scroll_box)` | — | Focus and click the scrollable container |
| `_find_scrollbox(dialog_el)` | `WebElement\|None` | CSS selector + JS fallback for scroll container |
| `_scroll_modal(scroll_box, cycles, pause, count_fn)` | — | Generic scroll loop with stagnation detection |
| `is_logged_in()` | `bool` | Check auth indicators on the home page |
| `login()` | — | Skip if session active; else fill form + handle dialogs |
| `_count_follow_buttons()` | `int` | Count visible Follow/Seguir buttons in dialog |
| `open_followers_modal()` | `WebElement` | Navigate to target profile and open followers dialog |
| `scroll_followers(scroll_box)` | — | Scroll follow modal using shared scroll helper |
| `follow_all(max_follows)` | `int` | Click Follow buttons with state-change wait |
| `run_follow()` | — | Full follow orchestration |
| `_count_unfollow_buttons()` | `int` | Count Following/Requested buttons in dialog |
| `open_following_modal(own_account)` | `WebElement` | Navigate to own profile and open following dialog |
| `scroll_following(scroll_box)` | — | Scroll following modal using shared scroll helper |
| `unfollow_all(max_unfollows)` | `int` | Click toggle + confirm unfollow with state-change wait |
| `run_unfollow(own_account)` | — | Full unfollow orchestration |
| `quit()` | — | Close the browser cleanly |

---

## 9. Configuration reference

All in `advanced/config.py`.

| Constant | Default | Description |
|---|---|---|
| `CHROME_VERSION` | `146` | Must match installed Chrome major version |
| `WAIT_TIMEOUT` | `20` | Global explicit wait (seconds) |
| `SHORT_WAIT` | `3` | Per-candidate fallback selector wait |
| `OPTIONAL_WAIT` | `4` | Non-deterministic popup wait |
| `SCROLL_CYCLES_FOLLOW` | `4` | Scroll passes when loading followers modal |
| `SCROLL_CYCLES_UNFOLLOW` | `6` | Scroll passes when loading following modal |
| `SCROLL_PAUSE` | `1.1` | Seconds between scroll nudges |
| `FOLLOW_DELAY` | `1.0` | Seconds between follow clicks |
| `UNFOLLOW_DELAY` | `0.9` | Seconds between unfollow actions |
| `MAX_EMPTY_RUNS` | `3` | Consecutive empty passes before giving up |
| `NUDGE_EVERY` | `5` | Clicks between periodic scroll nudges |
| `MAX_UNFOLLOWS` | `25` | Safety cap on unfollow pass (set `None` to remove) |
| `MODAL_SETTLE` | `0.3` | Sleep after opening a modal before interacting |

---

## 10. Environment variables

Copy `.env.example` to `.env` and fill in real values. Never commit `.env`.

| Variable | Description |
|---|---|
| `INSTAGRAM_USERNAME` | Instagram username for the automation account |
| `INSTAGRAM_PASSWORD` | Instagram password |
| `INSTAGRAM_TARGET` | Target account whose followers to follow (follow mode) |

---

## 11. Design decisions

**`undetected-chromedriver` over `selenium.webdriver.Chrome`**
Standard ChromeDriver sets automation flags in the browser binary that Instagram detects and uses to restrict or block the session. `undetected-chromedriver` patches the binary to remove these signatures.

**`CHROME_VERSION` pinned in `config.py`**
`undetected-chromedriver` needs the exact installed Chrome major version to patch the correct binary. It cannot reliably auto-detect this. Update `CHROME_VERSION` whenever Chrome auto-updates.

**`ChromeOptions` prefs for notifications and geolocation**
Chrome's native OS-level permission dialogs (notifications, location) cannot be dismissed by Selenium XPath — they are rendered outside the browser DOM. Suppressing them via `ChromeOptions` prefs at driver init prevents them from ever appearing.

**JS click with normal click fallback**
Overlapping elements, CSS animations, and elements at the edge of the viewport all cause `ElementClickInterceptedException` on normal clicks. Every button click in the bot uses `_js_click()`: try normal click, catch the exception, fall back to `driver.execute_script("arguments[0].click()", el)`.

**`presence_of_element_located` for buttons that start disabled**
Some buttons (e.g. Next after typing) start in a disabled state and enable after user input. `element_to_be_clickable` times out on disabled buttons. The bot uses `presence_of_element_located` and then JS-clicks.

**Short per-candidate wait (3s) in selector fallback lists**
The followers modal scroll container detection tries a CSS selector first with a 10s timeout, then falls back to JS inspection. Using the global 20s wait for the first candidate would add a 20s hang on every run where the CSS selector misses.

**Short wait (4s) for optional popups**
Instagram's post-login popup sequence is non-deterministic — different dialogs appear depending on account state. Using the global 20s wait for each optional popup causes silent multi-minute hangs when the popup doesn't appear.

**Proactive `clear_popup()` before each loop action**
`send_keys()` and `element.click()` silently do nothing when a popup is blocking the page — no exception is raised. The scroll nudge helper is called proactively at the start of empty-button runs so the loop recovers without waiting for an exception that will never come.

**Modal animation sleep (0.3s) after opening modal before interacting**
After clicking a button that opens a confirmation dialog (e.g. the unfollow toggle), the modal may not be interactable immediately. A short `time.sleep(MODAL_SETTLE)` before the confirm-button click prevents `NoSuchElementException` during animation.

**State-change wait after each Follow/Unfollow click**
Rather than sleeping a fixed delay, the bot waits for the button label to change away from "Follow/Seguir" or "Following/Siguiendo" (or for the element to go stale) before moving to the next entry. This adapts to network latency and prevents double-clicking.

**Persistent Chrome profile (`./chrome_profile/`)**
Storing the Chrome profile inside the project directory means login cookies, dismissed popups, and preference flags persist between script runs. The user only needs to complete 2FA or CAPTCHA once.

---

## 12. Course context

**Course:** 100 Days of Code — The Complete Python Pro Bootcamp  
**Day:** 52  
**Topic:** Selenium web automation — practical bot project  
**Instructor:** Angela Yu

The course project introduces Selenium by building a real Instagram automation bot:
log in, navigate to a target account, scroll the followers modal, and follow users.
A bonus step (added in this repo) adds a cleanup script to unfollow everyone.

---

## 13. Dependencies

| Module | Used in | Purpose |
|---|---|---|
| `undetected-chromedriver` | `advanced/bot.py` | Selenium driver without bot-detection fingerprint |
| `selenium` | `original/main.py`, `advanced/bot.py` | Browser automation framework |
| `python-dotenv` | `advanced/main.py` | Load credentials from `.env` |
