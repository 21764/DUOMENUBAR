#!/usr/bin/env python3
"""
Duo Mobile Menu Bar App
Displays TOTP codes from PlayCover's Duo Mobile in the macOS menu bar.
"""

import sqlite3
import json
import time
import hmac
import hashlib
import struct
import subprocess
import os
from pathlib import Path

try:
    import rumps
    from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
    HAS_RUMPS = True
except ImportError:
    HAS_RUMPS = False

PLAYCOVER_DB = Path.home() / "Library/Containers/io.playcover.PlayCover/PlayChain/com.duosecurity.DuoMobile.db"
MENUBAR_ICON = Path(__file__).parent / "duo_icon.png"
DUO_APP_PATH = Path.home() / "Library/Containers/io.playcover.PlayCover/Applications/com.duosecurity.DuoMobile.app"


def hotp(secret_bytes: bytes, counter: int, digits: int = 6) -> str:
    """Generate HOTP code."""
    hmac_hash = hmac.new(secret_bytes, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = hmac_hash[-1] & 0x0F
    binary = struct.unpack(">I", hmac_hash[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(binary % (10 ** digits)).zfill(digits)


def totp(secret: str, digits: int = 6, period: int = 30) -> str:
    """Generate TOTP code using Raw/6 method (secret as UTF-8 bytes)."""
    secret_bytes = secret.encode('utf-8')
    counter = int(time.time()) // period
    return hotp(secret_bytes, counter, digits)


def time_remaining(period: int = 30) -> int:
    """Get seconds remaining until next TOTP refresh."""
    return period - (int(time.time()) % period)


def copy_to_clipboard(text: str):
    """Copy text to macOS clipboard."""
    subprocess.run(['pbcopy'], input=text.encode('utf-8'))


def is_duo_running() -> bool:
    """Check if Duo Mobile app is running."""
    result = subprocess.run(
        ['pgrep', '-f', 'com.duosecurity.DuoMobile'],
        capture_output=True
    )
    return result.returncode == 0


def open_duo_app():
    """Open Duo Mobile via PlayCover using AppleScript and cliclick."""
    # First, open and activate PlayCover
    subprocess.run(['open', '-a', 'PlayCover'])
    time.sleep(1)

    # Use AppleScript to get Duo element position
    script = '''
    tell application "PlayCover"
        activate
    end tell

    delay 0.5

    tell application "System Events"
        tell process "PlayCover"
            try
                set duoElement to UI element 1 of scroll area 1 of group 2 of splitter group 1 of group 1 of window 1
                set {xPos, yPos} to position of duoElement
                set {xSize, ySize} to size of duoElement
                set centerX to (xPos + (xSize / 2)) as integer
                set centerY to (yPos + (ySize / 2)) as integer
                return (centerX as text) & "," & (centerY as text)
            on error
                return "error"
            end try
        end tell
    end tell
    '''

    result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    position = result.stdout.strip()

    if position and position != "error" and "," in position:
        # Use cliclick to double-click at position
        subprocess.run(['cliclick', f'dc:{position}'])


def close_duo_and_playcover():
    """Close Duo Mobile and PlayCover apps."""
    # Kill Duo Mobile process
    subprocess.run(['pkill', '-f', 'com.duosecurity.DuoMobile'], capture_output=True)
    time.sleep(0.5)

    # Quit PlayCover gracefully using AppleScript
    script = '''
    tell application "PlayCover"
        quit
    end tell
    '''
    subprocess.run(['osascript', '-e', script], capture_output=True)


def ensure_duo_running():
    """Make sure Duo app is running, open it if not."""
    if not is_duo_running():
        open_duo_app()
        # Wait a bit for app to start and populate database
        time.sleep(3)


def get_duo_accounts() -> list:
    """Read Duo accounts from PlayCover database."""
    accounts = []

    if not PLAYCOVER_DB.exists():
        return accounts

    try:
        conn = sqlite3.connect(str(PLAYCOVER_DB))
        cursor = conn.cursor()
        cursor.execute("SELECT v_Data FROM genp WHERE agrp='group.com.duosecurity.duomobile'")

        for row in cursor.fetchall():
            try:
                data = json.loads(row[0])
                secret = data.get('otpSecretKeyNew') or data.get('otpSecretKey')

                if secret:
                    accounts.append({
                        'name': data.get('displayLabel', data.get('accountName', 'Unknown')),
                        'secret': secret,
                    })
            except (json.JSONDecodeError, KeyError):
                continue

        conn.close()
    except sqlite3.Error:
        pass

    return accounts


if HAS_RUMPS:
    class DuoMenuBarApp(rumps.App):
        def __init__(self):
            icon_path = str(MENUBAR_ICON) if MENUBAR_ICON.exists() else None
            super().__init__("", icon=icon_path, quit_button=None, template=False)

            # Ensure Duo is running on startup to populate database
            ensure_duo_running()

            self.accounts = get_duo_accounts()

            # Close Duo and PlayCover after getting accounts
            if self.accounts:
                close_duo_and_playcover()

            self.timer = rumps.Timer(self.refresh_codes, 1)
            self.timer.start()
            self.refresh_codes(None)

        def refresh_codes(self, _):
            """Refresh all TOTP codes."""
            remaining = time_remaining()
            menu_items = []

            # Check if we have accounts, if not try to refresh
            if not self.accounts:
                if is_duo_running():
                    self.accounts = get_duo_accounts()

                if not self.accounts:
                    menu_items.append(rumps.MenuItem("No Accounts Found"))
                    menu_items.append(rumps.MenuItem("Open PlayCover", callback=self.open_duo))

            for account in self.accounts:
                code = totp(account['secret'])
                formatted_code = f"{code[:3]} {code[3:]}"

                item = rumps.MenuItem(
                    f"{account['name']}: {formatted_code}",
                    callback=lambda _, c=code: self.copy_code(c)
                )
                menu_items.append(item)

            menu_items.append(None)  # Separator
            menu_items.append(rumps.MenuItem(f"Refreshes in {remaining}s"))
            menu_items.append(None)  # Separator
            menu_items.append(rumps.MenuItem("Open PlayCover", callback=self.open_duo))
            menu_items.append(rumps.MenuItem("Refresh Accounts", callback=self.manual_refresh))
            menu_items.append(rumps.MenuItem("Quit", callback=rumps.quit_application))

            self.menu.clear()
            for item in menu_items:
                self.menu.add(item)

            # Just show the icon, no text
            self.title = ""

        def copy_code(self, code):
            """Copy code to clipboard."""
            copy_to_clipboard(code)
            rumps.notification("Duo Code Copied", "", f"Code {code} copied to clipboard")

        def open_duo(self, _):
            """Open Duo app, refresh accounts, then close."""
            open_duo_app()
            # Wait and refresh accounts
            time.sleep(3)
            self.accounts = get_duo_accounts()

            # Close after getting accounts
            if self.accounts:
                close_duo_and_playcover()

            self.refresh_codes(None)

        def manual_refresh(self, _):
            """Manually refresh accounts from database."""
            ensure_duo_running()
            self.accounts = get_duo_accounts()

            # Close after getting accounts
            if self.accounts:
                close_duo_and_playcover()

            self.refresh_codes(None)


def run_terminal_mode():
    """Run in terminal mode without rumps."""
    print("Duo TOTP Codes (Terminal Mode)")
    print("Press Ctrl+C to exit\n")

    ensure_duo_running()
    accounts = get_duo_accounts()

    # Close Duo and PlayCover after getting accounts
    if accounts:
        close_duo_and_playcover()

    if not accounts:
        print("No Duo accounts found!")
        print(f"Database path: {PLAYCOVER_DB}")
        return

    while True:
        os.system('clear')
        remaining = time_remaining()

        print("Duo TOTP Codes")
        print("=" * 40)

        for account in accounts:
            code = totp(account['secret'])
            formatted_code = f"{code[:3]} {code[3:]}"
            print(f"{account['name']}: {formatted_code}")

        print(f"\nRefreshes in {remaining}s")
        print("\nPress Ctrl+C to exit")

        time.sleep(1)


def main():
    if HAS_RUMPS:
        # Hide dock icon - make this an accessory app (menu bar only)
        NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        app = DuoMenuBarApp()
        app.run()
    else:
        print("rumps not installed. Install with: pip3 install rumps")
        print("Running in terminal mode instead...\n")
        run_terminal_mode()


if __name__ == "__main__":
    main()
