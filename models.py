from sqlalchemy import create_engine, Column, Integer, String, Boolean, LargeBinary, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL")

Base = declarative_base()

class Piece(Base):
    __tablename__ = "pieces"
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    driveFolderId = Column(String)
    composer = Column(String)
    arranger = Column(String)
    isCurrentRepertoire = Column(Boolean)
    sourceFile = Column(LargeBinary)
    created = Column(DateTime)
    updated = Column(DateTime)
    
    def __repr__(self):
        return f"<Piece(name={self.name}, arranger={self.arranger}, current={self.isCurrentRepertoire})>"

class Instrument(Base):
    __tablename__ = "instruments"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    variants = Column(String)

    def __repr__(self):
        return f"<Instrument(name={self.name}, variants={self.variants})>"

engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()