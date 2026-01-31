# Script to create all tables in the production database using SQLAlchemy
from sqlalchemy import create_engine
from app.db.models import Base
from app.core.config import settings

# Convert asyncpg URL to sync for table creation
sync_db_url = settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql")

engine = create_engine(sync_db_url)

if __name__ == "__main__":
    print("Creating all tables in the database...")
    Base.metadata.create_all(bind=engine)
    print("Done!")
