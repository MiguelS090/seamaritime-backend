import sys
from sqlalchemy.orm import sessionmaker
from app.database.db import engine, get_db
from app.controllers.user_controller import retrivel_service


def main():
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        result = retrivel_service(db)
        print(f"Job completed successfully: {result}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
