"""
Martin Leipert
martin.leipert@fau.de

Access Level definitions for the services of the Orthanc server
according to possible hospital functions

"""


class ACCESS_LEVELS:
    # Administrator -> may access everythin
    ADMIN = 4
    # Physician -> may access also everything
    PHYSISCIAN = 3
    # Nurse -> Probably should be able to see everything which is not specifically protected
    NURSE = 2
    # Student -> who only may have interest in some very particular images
    STUDENT = 1
    # The default level in this case that of a student
    DEFAULT = STUDENT

    # Getter method for the default
    @classmethod
    def GET_DEFAULT(cls):
        return cls.DEFAULT
