import plistlib
import json
import os
import base64
import string
from pathlib import Path

PLIST_PATH = Path.home() / "Library/Containers/com.duosecurity.DuoMobile/Data/Library/Preferences/com.duosecurity.DuoMobile.plist"

print(f"Reading plist: {PLIST_PATH}")

if not PLIST_PATH.exists():
    print("Plist not found!")
    exit(1)

def analyze_string(s, label):
    if not s or not isinstance(s, str):
        return

    print(f"  Field: {label}")
    mask_val = s
    if len(s) > 6:
        mask_val = s[:3] + "..." + s[-3:]
    print(f"    Value: {mask_val}")
    print(f"    Length: {len(s)}")
    
    unique_chars = set(s)
    is_hex = all(c in string.hexdigits for c in unique_chars)
    is_b32 = all(c in string.ascii_uppercase + "234567=" for c in unique_chars)
    is_b64 = all(c in string.ascii_letters + string.digits + "+/=" for c in unique_chars)
    
    print(f"    Char set matches: Hex={is_hex}, Base32={is_b32}, Base64={is_b64}")
    
    # Try Decodes
    try:
        if len(s) % 2 == 0:
            bytes.fromhex(s)
            print("    Valid Hex: Yes")
    except:
        pass
        
    try:
        base64.b32decode(s + "=" * ((8 - len(s) % 8) % 8), casefold=True)
        print("    Valid Base32: Yes")
    except:
        pass
        
    try:
        if len(s) > 8: # Short strings might accidentally be valid b64
            base64.b64decode(s + "=" * ((4 - len(s) % 4) % 4))
            print("    Valid Base64: Yes")
    except:
        pass

try:
    with open(PLIST_PATH, 'rb') as f:
        plist_data = plistlib.load(f)
        
    accounts_blob = plist_data.get('DUOSortedAccountInfoArrayKey')
    
    if not accounts_blob:
        print("DUOSortedAccountInfoArrayKey not found in plist.")
        exit(0)
        
    print(f"Found {len(accounts_blob)} items in DUOSortedAccountInfoArrayKey")
    
    for i, blob in enumerate(accounts_blob):
        print(f"\n--- Item {i} ---")
        try:
            json_str = blob.decode('utf-8')
            data = json.loads(json_str)
            
            # Print booleans/ints first
            for k, v in data.items():
                if isinstance(v, (bool, int)):
                    print(f"  {k}: {v}")
            
            # Analyze strings
            for k, v in data.items():
                if isinstance(v, str) and len(v) > 5:
                    if k in ['logoFileData', 'logoMd5']: continue # Skip obvious non-secrets
                    analyze_string(v, k)
            
        except Exception as e:
            print(f"Error decoding item {i}: {e}")

except Exception as e:
    print(f"Error reading plist: {e}")
