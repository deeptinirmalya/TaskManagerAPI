
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import OperationalError, InternalError
from core.config import settings

# ============================= fro aiven ========================================================
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SSL_CA_PATH = os.path.join(BASE_DIR, "ca.pem")

DATABASE_URL = settings.DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=0,
    pool_recycle=3600,
    pool_pre_ping=True,

    connect_args={
        "ssl": {
            "ssl_ca": SSL_CA_PATH
        }
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# ===============================================================================================

# DATABASE_URL = settings.DATABASE_URL


# engine = create_engine(
#     DATABASE_URL,
#     pool_size=5,
#     max_overflow=0,
#     pool_recycle=3600,
#     pool_pre_ping=True
# )

# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base = declarative_base()

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

def test_db_connection():
    print(f"🔄 Testing connection to MySQL database standard host'...")
    try:
        with engine.connect() as connection:
            query = text("SELECT 1")
            result = connection.execute(query).mappings().fetchone()
            
            if result and result['1'] == 1:
                print("✅ Success! Database connected perfectly.")
                return True
                
    except OperationalError as e:
        print("\n❌ Operational Error: Could not connect to the MySQL server.")
        print(f"👉 Check if your MySQL service is running or if host/port configuration is correct.")
        print(f"Details: {e.orig}\n")
        return False
        
    except InternalError as e:
        print("\n❌ Internal Error: The server is active but rejected the authentication or credentials.")
        print(f"👉 Check your DB_USER, DB_PASSWORD, and ensure DB_NAME actually exists.")
        print(f"Details: {e.orig}\n")
        return False
        
    except Exception as e:
        print(f"\n❌ Unexpected Database Connection Failure: {e}\n")
        return False

if __name__ == "__main__":
    test_db_connection()