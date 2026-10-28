from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker


def build_engine(database_url: str, **kwargs) -> Engine:
    return create_engine(database_url, pool_pre_ping=True, **kwargs)


def build_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
