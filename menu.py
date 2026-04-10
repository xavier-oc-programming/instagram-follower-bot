import os
import subprocess
import sys
from pathlib import Path

from art import LOGO

ROOT = Path(__file__).parent

MENU = """
  [1] Original  — course script (follow flow)
  [2] Advanced  — refactored bot with follow + unfollow modes
  [q] Quit
"""


def main():
    clear = True
    while True:
        if clear:
            os.system("cls" if os.name == "nt" else "clear")
            print(LOGO)
            print(MENU)
        clear = True

        choice = input("Select an option: ").strip().lower()

        if choice == "1":
            path = ROOT / "original" / "main.py"
            subprocess.run([sys.executable, str(path)], cwd=str(path.parent))
            input("\nPress Enter to return to menu...")
        elif choice == "2":
            path = ROOT / "advanced" / "main.py"
            subprocess.run([sys.executable, str(path)], cwd=str(path.parent))
            input("\nPress Enter to return to menu...")
        elif choice == "q":
            break
        else:
            print("Invalid choice. Try again.")
            clear = False


if __name__ == "__main__":
    main()
