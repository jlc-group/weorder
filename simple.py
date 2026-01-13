print("Hello from simple.py")
import sys
import os
sys.path.append(os.getcwd())

print("Importing sqlalchemy...")
from sqlalchemy import text
print("Importing sqlalchemy done")

print("Importing app.core...")
from app.core import SessionLocal
print("Importing app.core done")

