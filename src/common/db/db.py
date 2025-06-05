


from typing import Annotated
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from configurations.settings import db_conn



engine = create_engine(db_conn)

default_base = declarative_base()

SessionDefault = sessionmaker(autocommit = False, autoflush=False, bind=engine)


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