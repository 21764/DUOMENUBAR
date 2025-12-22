#!/usr/bin/env python3
"""
Duo Mobile Menu Bar App - Diagnostic Mode
Generates multiple TOTP variants to identify correct parameters.
"""

import sqlite3
import json
import time
import hmac
import hashlib
import struct
import subprocess
import os
import base64
from pathlib import Path

try:
    import rumps
    HAS_RUMPS = True
except ImportError:
    HAS_RUMPS = False

PLAYCOVER_DB = Path.home() / "Library/Containers/io.playcover.PlayCover/PlayChain/com.duosecurity.DuoMobile.db"
MENUBAR_ICON = Path(__file__).parent / "duo_icon_v3.png"


def get_digest_mod(algorithm: str):
    algo = algorithm.upper()
    if algo == 'SHA256': return hashlib.sha256
    if algo == 'SHA512': return hashlib.sha512
    return hashlib.sha1


def hotp(secret_bytes: bytes, counter: int, digits: int = 6, digest=hashlib.sha1) -> str:
    try:
        hmac_hash = hmac.new(secret_bytes, struct.pack(">Q", counter), digest).digest()
        offset = hmac_hash[-1] & 0x0F
        binary = struct.unpack(">I", hmac_hash[offset:offset + 4])[0] & 0x7FFFFFFF
        return str(binary % (10 ** digits)).zfill(digits)
    except:
        return "ERROR"


def totp(secret_bytes: bytes, digits: int = 6, period: int = 30, algorithm: str = 'SHA1') -> str:
    counter = int(time.time()) // period
    digest = get_digest_mod(algorithm)
    return hotp(secret_bytes, counter, digits, digest)


def time_remaining(period: int = 30) -> int:
    return period - (int(time.time()) % period)


def copy_to_clipboard(text: str):
    subprocess.run(['pbcopy'], input=text.encode('utf-8'))


def get_db_accounts() -> list:
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
                secret_raw = data.get('otpSecretKeyNew') or data.get('otpSecretKey')

                if secret_raw:
                    name = data.get('displayLabel', 'Unknown')
                    accounts.append({
                        'name': name,
                        'raw_secret': secret_raw,
                        'period': int(data.get('otpPeriod', 30))
                    })
            except:
                continue
        conn.close()
    except:
        pass
    return accounts


if HAS_RUMPS:
    class DuoMenuBarApp(rumps.App):
        def __init__(self):
            icon_path = str(MENUBAR_ICON) if MENUBAR_ICON.exists() else None
            super().__init__("", icon=icon_path, quit_button=None, template=False)
            self.accounts = get_db_accounts()
            self.timer = rumps.Timer(self.refresh_codes, 1)
            self.timer.start()
            self.refresh_codes(None)

        def refresh_codes(self, _):
            rem = time_remaining(30)
            menu_items = []

            if not self.accounts:
                menu_items.append(rumps.MenuItem("No Accounts Found"))

            for acc in self.accounts:
                s_raw = acc['raw_secret']

                # Variant 1: Hex Decode (Standard)
                try:
                    b_hex = bytes.fromhex(s_raw)
                    c_hex_6 = totp(b_hex, digits=6)
                    c_hex_8 = totp(b_hex, digits=8)
                    c_hex_256 = totp(b_hex, algorithm='SHA256')

                    menu_items.append(rumps.MenuItem(f"{acc['name']} [Hex/6]: {c_hex_6[:3]} {c_hex_6[3:]}",
                                                     callback=lambda _, c=c_hex_6: self.copy_code(c)))
                    menu_items.append(rumps.MenuItem(f"{acc['name']} [Hex/8]: {c_hex_8}",
                                                     callback=lambda _, c=c_hex_8: self.copy_code(c)))
                    menu_items.append(rumps.MenuItem(f"{acc['name']} [Hex/SHA256]: {c_hex_256}",
                                                     callback=lambda _, c=c_hex_256: self.copy_code(c)))
                except:
                    pass

                # Variant 2: Raw Bytes (Treat string as bytes)
                b_raw = s_raw.encode('utf-8')
                c_raw_6 = totp(b_raw, digits=6)
                menu_items.append(rumps.MenuItem(f"{acc['name']} [Raw/6]: {c_raw_6[:3]} {c_raw_6[3:]}",
                                                 callback=lambda _, c=c_raw_6: self.copy_code(c)))

                # Variant 3: Base64 (if it looks plausible)
                try:
                    s_b64 = s_raw + '=' * ((4 - len(s_raw) % 4) % 4)
                    b_b64 = base64.b64decode(s_b64)
                    if len(b_b64) > 8:
                        c_b64_6 = totp(b_b64, digits=6)
                        menu_items.append(rumps.MenuItem(f"{acc['name']} [B64/6]: {c_b64_6[:3]} {c_b64_6[3:]}",
                                                         callback=lambda _, c=c_b64_6: self.copy_code(c)))
                except:
                    pass

                menu_items.append(None)  # Separator

            menu_items.append(rumps.MenuItem(f"Refreshes in {rem}s"))
            menu_items.append(rumps.MenuItem("Refresh", callback=self.manual_refresh))
            menu_items.append(rumps.MenuItem("Quit", callback=rumps.quit_application))

            self.menu.clear()
            for item in menu_items:
                self.menu.add(item)

            # Just show the icon, no text
            self.title = ""

        def copy_code(self, code):
            copy_to_clipboard(code)
            rumps.notification("Duo Code Copied", "", f"Code {code} copied to clipboard")

        def manual_refresh(self, _):
            self.accounts = get_db_accounts()
            self.refresh_codes(None)


def run_simple_mode():
    print("Running in Diagnostic Mode")
    while True:
        os.system('clear')
        accounts = get_db_accounts()

        if not accounts:
            print("No accounts found in database")
            print(f"Database: {PLAYCOVER_DB}")

        for acc in accounts:
            s_raw = acc['raw_secret']
            print(f"--- {acc['name']} ---")

            try:
                b_hex = bytes.fromhex(s_raw)
                print(f"Hex/6: {totp(b_hex)}")
            except:
                pass

            print(f"Raw/6: {totp(s_raw.encode('utf-8'))}")

        print(f"\nRefreshes in {time_remaining()}s")
        time.sleep(1)


def main():
    if HAS_RUMPS:
        DuoMenuBarApp().run()
    else:
        run_simple_mode()


if __name__ == "__main__":
    main()
