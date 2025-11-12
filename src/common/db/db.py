

from typing import Annotated
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from configurations.settings import db_conn
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


engine = create_engine(db_conn)

default_base = declarative_base()

SessionDefault = sessionmaker(autocommit=False, autoflush=False, bind=engine)

asyncengine = create_async_engine(
    url=db_conn,
    echo=True,
    pool_size=10,
    max_overflow=20,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=asyncengine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


def get_default_db():
    db = SessionDefault()
    try:
        yield db
    finally:
        db.close()


def execute_query(sql):
    try:
        db = sessionmaker(bind=engine)
        db_session = db()
        print(sql)
        result = db_session.execute(text(sql)).all()
        return result
    except Exception as e:
        print(e)
        return None
    finally:
        db_session.close()


def execute_non_query(sql):
    try:
        db = sessionmaker(bind=engine)
        db_session = db()
        print(sql)
        result = db_session.execute(text(sql))
        db_session.commit()
        return result
    except Exception as e:
        print(e)
        return None
    finally:
        db_session.close()


async def async_get_default_db():
    async with AsyncSessionLocal() as session:
        yield session

async def async_execute_query(sql: str):
    async with AsyncSessionLocal() as session:
        try:
            print(sql)
            result = await session.execute(text(sql))
            return result.fetchall()
        except Exception as e:
            print(f"Query Error: {e}")
            return None
        
async def async_execute_non_query(sql: str):
    async with AsyncSessionLocal() as session:
        try:
            print(sql)
            await session.execute(text(sql))
            await session.commit()
            return True
        except Exception as e:
            print(f"Non-Query Error: {e}")
            return None