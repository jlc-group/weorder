
import os

with open("verify_output_final.txt", "rb") as f:
    try:
        f.seek(-2000, os.SEEK_END)
    except OSError:
        pass
    last_lines = f.readlines()
    for line in last_lines[-10:]:
        print(line.decode('utf-8', errors='ignore').strip())
