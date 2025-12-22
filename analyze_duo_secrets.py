import sqlite3
import json
import time
import hmac
import hashlib
import struct
import base64
import sys
from pathlib import Path

# Paths
PLAYCOVER_DB = Path.home() / "Library/Containers/io.playcover.PlayCover/PlayChain/com.duosecurity.DuoMobile.db"

print(f"Checking DB: {PLAYCOVER_DB}")

def get_digest_mod(algorithm):
    algo = algorithm.upper()
    if algo == 'SHA256': return hashlib.sha256
    if algo == 'SHA512': return hashlib.sha512
    return hashlib.sha1

def hotp(secret_bytes, counter, digits=6, digest=hashlib.sha1):
    try:
        hmac_hash = hmac.new(secret_bytes, struct.pack(">Q", counter), digest).digest()
        offset = hmac_hash[-1] & 0x0F
        binary = struct.unpack(">I", hmac_hash[offset:offset + 4])[0] & 0x7FFFFFFF
        return str(binary % (10 ** digits)).zfill(digits)
    except:
        return "ERROR"

def totp(secret_bytes, digits=6, period=30, algorithm='SHA1', time_offset=0):
    if not secret_bytes: return "EMPTY"
    counter = int(time.time() + time_offset) // period
    digest = get_digest_mod(algorithm)
    return hotp(secret_bytes, counter, digits, digest)

def decode_secret(secret_raw):
    if not secret_raw: return b'', "None"
    
    results = []
    
    # Hex
    try:
        b = bytes.fromhex(secret_raw)
        results.append((b, "Hex"))
    except: pass
    
    # Base32
    try:
        s = secret_raw.upper()
        pad = 8 - len(s) % 8
        if pad != 8: s += '=' * pad
        if all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567=" for c in s):
            results.append((base64.b32decode(s, casefold=True), "Base32"))
    except: pass
    
    # Base64
    try:
        s = secret_raw
        pad = 4 - len(s) % 4
        if pad != 4: s += '=' * pad
        results.append((base64.b64decode(s), "Base64"))
    except: pass
    
    # Raw
    results.append((secret_raw.encode('utf-8'), "Raw"))
    
    return results

if not PLAYCOVER_DB.exists():
    print("DB not found!")
    sys.exit(1)

try:
    conn = sqlite3.connect(str(PLAYCOVER_DB))
    cursor = conn.cursor()
    cursor.execute("SELECT v_Data FROM genp WHERE agrp='group.com.duosecurity.duomobile'")
    rows = cursor.fetchall()

    print(f"\nFound {len(rows)} accounts.")

    for i, row in enumerate(rows):
        try:
            data = json.loads(row[0])
            name = data.get('displayLabel', 'Unknown')
            print(f"\n==================================================")
            print(f"Account {i+1}: {name}")
            print(f"==================================================")
            
            # Print Account Metadata
            print(f"Type: {data.get('otpType')} | Digits: {data.get('otpDigits', 6)} | Period: {data.get('otpPeriod', 30)} | Algo: {data.get('otpAlgorithm', 'SHA1')}")
            
            keys_to_check = ['otpSecretKey', 'otpSecretKeyNew', 'akey', 'pkey', 'secret', 'otpSecret']
            
            for k in keys_to_check:
                val = data.get(k)
                if val:
                    print(f"\n[Key: {k}]")
                    print(f"  Raw Value (masked): {val[:5]}...{val[-5:]} (Len: {len(val)})")
                    
                    decoded_candidates = decode_secret(val)
                    
                    for b, enc_name in decoded_candidates:
                        if not b: continue
                        print(f"  -- Decoding: {enc_name} (Bytes: {len(b)}) --")
                        
                        # Try standard 6 digits
                        c = totp(b)
                        print(f"     Code (6): {c}  (Now)")
                        
                        # Try 8 digits
                        c8 = totp(b, digits=8)
                        print(f"     Code (8): {c8}  (Now)")
                        
                        # Try SHA256
                        c256 = totp(b, algorithm='SHA256')
                        print(f"     Code (SHA256): {c256} (Now)")

                        # Try time offsets for standard 6/SHA1
                        c_prev = totp(b, time_offset=-30)
                        c_next = totp(b, time_offset=30)
                        print(f"     Time Drift: {c_prev} (-30s) | {c} (Now) | {c_next} (+30s)")

                else:
                    pass # Key not present
                    
        except Exception as e:
            print(f"Error parsing row: {e}")

    conn.close()
except Exception as e:
    print(f"DB Error: {e}")