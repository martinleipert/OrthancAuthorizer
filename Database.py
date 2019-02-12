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

# Access permission store which user may access which patient
# -> The access permissions associate patients with users
# Association table for the Permissions
association_table = Table('accessPermissions',
    Base.metadata,
    Column(
        'patient_orthanc_pid',
        String,
        ForeignKey('patients.orthanc_pid')
    ),
    Column(
        'orthancuser_uid',
        Integer,
        ForeignKey('orthanc_users.uid')
    )
)


# Class to store the User data and the mod mellon tokens
class OrthancUser(Base):
    __tablename__ = 'orthanc_users'

    # -> Uid an integer
    uid = Column(Integer, primary_key=True)
    # Full name string like "Max Mustermann"
    full_name = Column(String)
    # Email adress the most important key -> Used for SSO account
    e_mail = Column(String)

    # User group -> Admin, Physician, Nurse, Student
    access_level = Column(Integer)

    # List of associations
    allowed_patients = relationship("Patient", secondary=association_table, back_populates="permitted_users")

    # Constructor -> All parameters
    def __init__(self, uid, full_name, e_mail, access_level):
        # UID is just the ordinal number of the user, order of creation
        self.uid = uid
        self.full_name = full_name
        self.e_mail = e_mail
        self.access_level = access_level

    # For printing
    def __repr__(self):
        return "<User(uid='%i', name='%s', e_mail='%s', access_lvl='%i')>" % \
               (self.uid, self.full_name, self.e_mail, self.access_level)


# Represents a patient
class Patient(Base):
    __tablename__ = 'patients'

    # The unique Orthanc id the patient get's assigned to
    orthanc_pid = Column(String, primary_key=True)

    # The required minimal id of the user group which is allowed to access the patient
    access_lvl = Column(Integer)

    # Specific users which are allowed to access the patient
    permitted_users = relationship("OrthancUser", secondary=association_table, back_populates="allowed_patients")

    # Constructor which requires a user group and the id of the ressource
    def __init__(self, orthanc_pid, access_lvl):
        self.orthanc_pid = orthanc_pid
        self.access_lvl = access_lvl
        self.permitted_users = []
    
    def __repr__(self):
        return "<Patient(orthanc_patient_id='%s', access_lvl='%i')>" % (self.orthanc_pid, self.access_lvl)


# Create the tables in the Database
Base.metadata.create_all(engine)



