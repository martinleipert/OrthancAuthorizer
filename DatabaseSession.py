from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# STORE the session manager
engine = create_engine('sqlite:///dummy.db', echo=True)
session = sessionmaker(bind=engine)
sm = session()
