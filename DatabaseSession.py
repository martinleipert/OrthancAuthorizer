from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

"""
Database which session -> The access string may be exchanged by any session type
Its sqlite for experiment purposes
-> Session can be imported by other scripts
"""

# STORE the session manager
engine = create_engine('sqlite:///dummy.db', echo=True)
session = sessionmaker(bind=engine)
sm = session()
