from sqlalchemy import create_engine, Column, Integer, String, Float, JSON
from sqlalchemy.orm import declarative_base, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./switches.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Switch(Base):
    __tablename__ = "switches"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    switch_type = Column(String)  # Linear, Tactile, Clicky, Silent
    force_actuation = Column(Float)  # gf
    force_bottom = Column(Float)     # gf
    manufacturer = Column(String)
    travel_actuation = Column(Float) # mm
    travel_bottom = Column(Float)    # mm
    tester_machine = Column(String)  # Which tester rig was used
    location = Column(String)        # e.g., "Tray 1, R4-C2"

    # Media and Data
    image_path = Column(String, nullable=True)
    force_curve_data = Column(JSON, nullable=True) # Stores the raw points: [[dist, force], [dist, force]]

# Create the tables
Base.metadata.create_all(bind=engine)
