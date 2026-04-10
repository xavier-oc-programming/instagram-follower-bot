import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

import config
from bot import InstaBot


def main():
    username = os.environ.get(config.ENV_USERNAME, "")
    password = os.environ.get(config.ENV_PASSWORD, "")
    target   = os.environ.get(config.ENV_TARGET, "")

    if not username or not password:
        print("Error: INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD must be set in .env")
        sys.exit(1)

    print("Instagram Follower Bot — Advanced Build")
    print("----------------------------------------")
    print("  [1] Follow followers of a target account")
    print("  [2] Unfollow everyone (cleanup pass)")
    print()

    choice = input("Select mode (1 / 2): ").strip()

    if choice == "1":
        if not target:
            target = input("Enter target account username: ").strip()
        if not target:
            print("No target account provided. Exiting.")
            sys.exit(1)
        bot = InstaBot(username=username, password=password, target_account=target)
        try:
            bot.run_follow()
        except Exception as e:
            print(f"Error: {e}")
        finally:
            bot.quit()

    elif choice == "2":
        bot = InstaBot(username=username, password=password, target_account="")
        try:
            bot.run_unfollow(own_account=username)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            bot.quit()

    else:
        print("Invalid choice. Exiting.")
        sys.exit(1)


if __name__ == "__main__":
    main()
