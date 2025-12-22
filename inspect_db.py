import sqlite3
import json
import plistlib
import os
from pathlib import Path

# PlayCover database path
PLAYCOVER_DB = Path.home() / "Library/Containers/io.playcover.PlayCover/PlayChain/com.duosecurity.DuoMobile.db"

print(f"Inspecting DB: {PLAYCOVER_DB}")

if not PLAYCOVER_DB.exists():
    print("DB does not exist!")
    exit(1)

conn = sqlite3.connect(str(PLAYCOVER_DB))
cusor = conn.cursor()

tables = ['genp', 'inet', 'idnt', 'cert', 'keys']

for table in tables:
    print(f"\n--- Table: {table} ---")
    try:
        cusor.execute(f"SELECT rowid, * FROM {table}")
        columns = [description[0] for description in cusor.description]
        rows = cusor.fetchall()
        print(f"Row count: {len(rows)}")
        
        for row in rows:
            print(f"\nRow {row[0]}:")
            row_dict = dict(zip(columns, row))
            
            # Print metadata
            print(f"  agrp: {row_dict.get('agrp')}")
            print(f"  svce: {row_dict.get('svce')}")
            print(f"  acct: {row_dict.get('acct')}")
            print(f"  labl: {row_dict.get('labl')}")
            
            # Inspect v_Data
            v_data = row_dict.get('v_Data')
            if v_data:
                print("  v_Data analysis:")
                # Try JSON
                try:
                    data = json.loads(v_data)
                    print("    Type: JSON")
                    print(f"    Keys: {list(data.keys())}")
                    if 'otpSecretKey' in data:
                        print(f"    FOUND OTP KEY! displayLabel: {data.get('displayLabel')}")
                except:
                    # Try Plist
                    try:
                        # v_Data might be string representation of bytes or actual bytes?
                        # In sqlite3 python, TEXT columns return str. 
                        # If it's bplist, it might be garbled str.
                        # But typically it's stored as BLOB or encoded string.
                        # The previous output showed b'bplist...' which suggests it came out as bytes or we saw repr().
                        
                        # If it's a string, we might need to encode it to bytes to parse as plist
                        if isinstance(v_data, str):
                            data_bytes = v_data.encode('latin1') # Try to recover bytes? 
                            # Or if it starts with 'bplist', it's binary.
                            if v_data.startswith('bplist'):
                                data_bytes = v_data.encode('utf-8') # Unlikely to work directly if binary data 
                                # Actually, checking the previous output: 
                                # v_Data (raw): b'bplist00\xd4...'
                                # It seems it was returned as bytes?
                                pass
                        
                        if isinstance(v_data, bytes):
                             data_bytes = v_data
                        else:
                             # If it's a string that looks like binary, encoding it is tricky.
                             # Let's try simple encode
                             data_bytes = v_data.encode('utf-8')

                        try:
                            plist_data = plistlib.loads(data_bytes)
                            print("    Type: Binary Plist")
                            print(f"    Content: {plist_data}")
                        except:
                            print("    Type: Unknown (Raw)")
                            # print(f"    First 50 chars: {v_data[:50]}")
                    except Exception as e:
                        print(f"    Plist check failed: {e}")

    except sqlite3.Error as e:
        print(f"Error reading table {table}: {e}")

conn.close()
