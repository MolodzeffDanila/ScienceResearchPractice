import os

from flask_sqlalchemy.session import Session
from sqlalchemy import Column, Integer
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

Base = declarative_base()

class Civilians(Base):
    __tablename__ = 'civilians'

    id = Column(Integer, primary_key=True)
    position = Column(Integer)
    hp = Column(Integer)
    buriness = Column(Integer)

class Burning(Base):
    __tablename__ = 'burning'

    id = Column(Integer, primary_key=True)
    fireness = Column(Integer)

class Visited(Base):
    __tablename__ = 'visited'

    id = Column(Integer, primary_key=True)
    position = Column(Integer)

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
db_path = os.path.join(BASE_DIR, 'database.db')
engine = create_engine(f'sqlite:///{db_path}?check_same_thread=False', echo=True)
Base.metadata.bind = engine
SessionLocal = scoped_session(sessionmaker(bind=engine))

def clear_all_data():
    session = SessionLocal()
    try:
        for model in [Civilians, Burning, Visited]:  # добавь сюда все модели, которые хочешь очищать
            session.query(model).delete()
        session.commit()
        print("[✔] Все таблицы очищены.")
    except Exception as e:
        session.rollback()
        print(f"[✘] Ошибка при очистке БД: {e}")
    finally:
        session.close()