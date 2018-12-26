"""
Martin Leipert
martin.leipert@fau.de

"""
class ACCESS_LEVELS:

    # Administrator may access everythin
    ADMIN = 4

    # Physician may access also everything
    PHYSISCIAN = 3

    # Nurse and Students
    NURSE = 2
    STUDENT = 1

    DEFAULT = STUDENT

    # Getter method for the default
    @classmethod
    def GET_DEFAULT(cls):
        return cls.STUDENT
