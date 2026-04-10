# Course Notes — Day 52: Instagram Follower Bot

## Original exercise description

Build a Selenium bot that automatically follows the followers of a similar/competitor Instagram
account (the "target" account). The idea is to get those users' attention so they follow back.

Steps covered in the course:

1. **Get credentials** — store your Instagram username, password, and target account as constants.
2. **Create a class** — define `InstaFollower` with `login()`, `find_followers()`, and `follow()`
   as placeholder methods.
3. **Login to Instagram** — automate the login form, handle cookie popups, save-info dialog,
   and notification prompts. Add persistent Chrome profile so sessions survive restarts.
4. **Find followers** — navigate to the target account profile, click the Followers link, scroll
   the modal to load entries, and collect visible `Follow` buttons.
5. **Follow all followers** — iterate through collected buttons, click each, wait for state-change
   confirmation, and periodically scroll to surface more rows.
6. **Unfollow cleanup** — bonus script: open your own Following list, scroll it, and unfollow
   everyone using the same state-change pattern.

## Key challenges encountered

- Instagram's DOM is an SPA that changes frequently — XPaths need regular updates.
- Standard `selenium.webdriver.Chrome` is fingerprinted by Instagram's bot detection.
  The advanced build uses `undetected-chromedriver` to bypass this.
- The followers modal has a non-obvious scrollable container; a CSS selector for
  `overflow-y: hidden auto` with a JS fallback was required.
- `send_keys()` and `element.click()` silently do nothing when a popup is blocking.
  The follow loop uses proactive popup clearing at each iteration.
- Chrome OS-level permission dialogs (notifications, geolocation) cannot be dismissed
  via Selenium — they must be suppressed up-front via `ChromeOptions` prefs.

## Credentials note

Hardcoded `USERNAME` and `PASSWORD` were redacted with `*****` in all committed files.
Copy `.env.example` to `.env`, fill in real values, and never commit `.env`.

If you used a real password in any commit, rotate it immediately and run `git-filter-repo`
to scrub it from history before pushing.
