from sqlalchemy import Column, Integer
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base

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

# создает экземпляр create_engine в конце файла
engine = create_engine('sqlite:///database.db')

Base.metadata.create_all(engine)