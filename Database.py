from sqlalchemy import Table, Column, Integer, String, ForeignKey, create_engine
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from DatabaseSession import engine

"""
Martin Leipert
martin.leipert@fau.de

Setup and declaration script for the SQLAlchemy ORM and Database
"""

# Create the Database
Base = declarative_base()

# Association table for the Permissions
association_table = Table('accessPermissions',
    Base.metadata,
    Column('patient_orthanc_pid', String, ForeignKey('patients.orthanc_pid')),
    Column('orthancuser_uid', Integer, ForeignKey('orthanc_users.uid'))
)


"""
Class to store the User data and the mod mellon tokens
"""
class OrthancUser(Base):
    __tablename__ = 'orthanc_users'

    uid = Column(Integer, primary_key=True)
    full_name = Column(String)
    e_mail = Column(String)
    access_level = Column(Integer)
    allowed_patients = relationship("Patient", secondary=association_table, back_populates="permitted_users")

    def __init__(self, uid, full_name, e_mail, access_level):
        # UID is just the number of creation
        self.uid = uid
        self.full_name = full_name
        self.e_mail = e_mail
        self.access_level = access_level

    def __repr__(self):
        return "<User(uid='%i', name='%s', e_mail='%s', access_lvl='%i')>" % \
               (self.uid, self.full_name, self.e_mail, self.access_level)


class Patient(Base):
    __tablename__ = 'patients'

    orthanc_pid = Column(String, primary_key=True)
    access_lvl = Column(Integer)
    permitted_users = relationship("OrthancUser", secondary=association_table, back_populates="allowed_patients")


    def __init__(self, orthanc_pid, access_lvl):
        self.orthanc_pid = orthanc_pid
        self.access_lvl = access_lvl
        self.permitted_users = []
    
    def __repr__(self):
        return "<Patient(orthanc_patient_id='%s', access_lvl='%i')>" % (self.orthanc_pid, self.access_lvl)

"""
class AccessPermission(Base):
    __tablename__ = 'accessPermissions'

    exception_id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey('users.e_mail'))
    patient_id = Column(String, ForeignKey('patients.orthanc_pid'))

    def __init__(self, user_id, patient_id):
        self.user_id = user_id
        self.patient_id = patient_id

        pass

    def __repr__(self):
        return "<Patient(orthanc_patient_id='%s', access_lvl='%i')>" % (self.user_id, self.parent_id)
"""


class AccessLevels:
    ADMIN = 4
    PHYSICIAN = 3
    NURSE = 2
    STUDENT = 1



# session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)



