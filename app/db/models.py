from sqlalchemy import Column, Integer, String, Boolean, Float
from geoalchemy2 import Geography
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Pincode(Base):
    __tablename__ = "pincodes"
    id = Column(Integer, primary_key=True, index=True)
    pincode = Column(String(6), unique=True, index=True, nullable=False)
    office_name = Column(String)
    district = Column(String)
    state = Column(String)
    tier = Column(String(10))
    serviceable = Column(Boolean, default=True)
    lat = Column(Float)
    lon = Column(Float)
    location = Column(Geography(geometry_type="POINT", srid=4326))
