import sys
import os
sys.path.append(os.getcwd())

from app.core import engine
from app.core.database import Base
from app.models import *
from app.models.stock import Location, StockBalance # Ensure imported

if __name__ == "__main__":
    print("Creating all tables if not exist...")
    Base.metadata.create_all(bind=engine)
    print("Done.")
