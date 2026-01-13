
import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True
)

logging.info("Step 1: Script started")
time.sleep(1)
logging.info("Step 2: Slept for 1s")
print("Standard print output", flush=True)
