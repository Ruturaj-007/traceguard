from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Engine betn app & db
engine = create_engine(settings.database_url)

# Factory basically is a factory that creates database sessions  
SessionLocal = sessionmaker(
    autocommit = False,
    autoflush = False,
    bind = engine
)

# * Fucn creates a session & gives it to ur API 
# * yield is similar to return but it gives value like return then continue later 
# * Creates DB session -> yield DB -> API Uses the database -> API req finishes -> finally runs -> db.close()
def get_db():
    db = SessionLocal()
    try:
        yield db 
    finally:
        db.close()