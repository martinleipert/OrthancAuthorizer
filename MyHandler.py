
import socket
import sys
from threading import Thread
import json

import SimpleHTTPServer
import SocketServer
from BaseHTTPServer import BaseHTTPRequestHandler
from DatabaseSession import sm
from Database import OrthancUser, Patient
from ACCESSLEVELS import ACCESS_LEVELS

import re

###########
HOST = ''
PORT = 8000
###########


# @TODO maybe implement also "grant access to all students"
E_MAIL_MELLON = 'MELLON_uid'
MOD_E_MAIL_MELLON = 'MOD_%s' % E_MAIL_MELLON
NAME_MELLON = 'MELLON_name'
MOD_NAME_MELLON = 'MOD_%s' % NAME_MELLON


def main():
    # Start the web server
    httpd = SocketServer.TCPServer((HOST, PORT), MyHandler)
    httpd.serve_forever()

    pass


def shutdown():
    httpd.shutdown()

"""
Self implemented webserver which handles requests and gives permissions

* Patient Management
* User Management
* Access Permission Management
* Access Granting
"""

class MyHandler(BaseHTTPRequestHandler):
    PATH_USER_ADMINISTRATION = '/userAdministration/'
    PATH_PATIENT_ADMINISTRATION = '/patientAdministration/'
    PATH_ACCESS_ADMINISTRATION = '/accessAdministration/'
    PATH_PRIVILEGE_ADMINISTRATION = '/privileges/'
    GRANT_ACCESS_PATH = '/grantAccess/'

    TOKEN_ORTHANC_ID = 'orthanc-id'
    TOKEN_ACCESS_LEVEL = 'access-level'

    # <editor-fold desc="RequestManagement">
    def do_GET(self):
        if self.path == MyHandler.PATH_USER_ADMINISTRATION:
            # TODO First query user priviledges

            users = sm.query(OrthancUser).all()
            user_mails_fullnames = list(map(lambda x: (x.e_mail, x.full_name), users))
            response_dict = {'user-ids': dict(user_mails_fullnames)}
            # response_dict = {'user-ids': "Horst"}
            self.sendResponseDict(response_dict)

        elif self.path == MyHandler.PATH_PATIENT_ADMINISTRATION:
            patients = sm.query(Patient).all()
            patient_ids = list(map(lambda x: (x.orthanc_pid), patients))
            response_dict = {MyHandler.TOKEN_ORTHANC_ID + 's': patient_ids}
            self.sendResponseDict(response_dict)

    def do_POST(self):

        content_len = int(self.headers.getheader('content-length', 0))
        post_body = self.rfile.read(content_len)
        json_dict = self.parse_json_dict(post_body)

        if self.path == MyHandler.PATH_USER_ADMINISTRATION:
            self.addUser(json_dict)
            self.send_response(200)

        elif self.path == MyHandler.PATH_ACCESS_ADMINISTRATION:
            self.addAccessPermission(json_dict)
            self.send_response(200)

        elif self.path == MyHandler.PATH_PATIENT_ADMINISTRATION:
            self.addPatient(json_dict)
            self.send_response(200)

        # Check if user may grant permissions
        elif self.path == MyHandler.PATH_PRIVILEGE_ADMINISTRATION:
            e_mail = json_dict[E_MAIL_MELLON]
            user = sm.query(OrthancUser).filter_by(e_mail=e_mail).first()

            response_dict = {
                'access-level': user.access_level,
                'grant-permissions': user.access_level >= user.ACCESS_LVL_PHYSICIAN
            }

            content = json.dumps(response_dict, ensure_ascii=False)
            self.send_response(200)
            self.send_header("Content-Length", len(content))
            self.send_header("Content-Type", "text/json")
            self.end_headers()
            self.wfile.write(content)

        elif self.path == MyHandler.GRANT_ACCESS_PATH:

            level = json_dict["level"]
            e_mail = json_dict[E_MAIL_MELLON]
            name = json_dict[NAME_MELLON]

            response_dict = {
                "granted": False,
                "validity": 5
            }

            if level == "patient":
                orthanc_id = json_dict[MyHandler.TOKEN_ORTHANC_ID]


                # @TODO Get patient
                patient = sm.query(Patient).filter_by(orthanc_pid=orthanc_id).first()
                user = sm.query(OrthancUser).filter_by(e_mail=e_mail).first()

                if patient is None:
                    dict_to_add = {MyHandler.TOKEN_ORTHANC_ID: orthanc_id}
                    self.addPatient(dict_to_add)
                    patient = sm.query(Patient).filter_by(orthanc_pid=orthanc_id).first()

                if user is None:
                    dict_to_add = {
                        MOD_E_MAIL_MELLON: e_mail,
                        MOD_NAME_MELLON: name,
                        MyHandler.TOKEN_ACCESS_LEVEL: ACCESS_LEVELS.GET_DEFAULT()
                    }
                    self.addUser(dict_to_add)
                    user = sm.query(Patient).filter_by(orthanc_pid=orthanc_id).first()

                if user.access_level >= patient.access_lvl:
                    response_dict["granted"] = True
                elif user in patient.permitted_users:
                    response_dict["granted"] = True

            elif level == "system":

                # TODO Access for user administration and user query

                uri = json_dict["uri"]

                user = sm.query(OrthancUser).filter_by(e_mail=e_mail).first()

                uris_admin = ["priviledgeAdministration"]

                if uri in uris_admin:
                    if user.access_level >= ACCESS_LEVELS.PHYSISCIAN:
                        response_dict["granted"] = True

                pass

            else:
                response_dict["granted"] = True

            content = json.dumps(response_dict, ensure_ascii=False)
            self.send_response(200)
            self.send_header("Content-Length", len(content))
            self.send_header("Content-Type", "text/json")
            self.end_headers()
            self.wfile.write(content)

        pass

    def do_DELETE(self):
        content_len = int(self.headers.getheader('content-length', 0))
        post_body = self.rfile.read(content_len)
        json_dict = self.parse_json_dict(post_body)

        if self.path == MyHandler.PATH_USER_ADMINISTRATION:
            self.removeUser(json_dict)
            self.send_response(200)

        elif self.path == MyHandler.PATH_ACCESS_ADMINISTRATION:
            self.removeAccessPermission(json_dict)
            self.send_response(200)

        elif self.path == MyHandler.PATH_PATIENT_ADMINISTRATION:
            self.removePatient(json_dict)
            self.send_response(200)


    def do_PUT(self):
        content_len = int(self.headers.getheader('content-length', 0))
        post_body = self.rfile.read(content_len)
        json_dict = self.parse_json_dict(post_body)

        if self.path == MyHandler.PATH_USER_ADMINISTRATION:
            self.updateUser(json_dict)
            self.send_response(200)

    def do_OPTIONS(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_response(200, "ok")

        """
        if self.path == MyHandler.PATH_USER_ADMINISTRATION:
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
            self.send_header("Access-Control-Allow-Headers", "X-Requested-With")
            self.send_response(200, "ok")
        """
        pass

    # </editor-fold>

    # <editor-fold desc="HTTPHelpers">

    def sendResponseDict(self, response_dict):
        content = json.dumps(response_dict, ensure_ascii=False)
        self.send_response(200)
        self.send_header("Content-Length", len(content))
        self.send_header("Content-Type", "text/json")
        self.end_headers()
        self.wfile.write(content)
    # </editor-fold>

    # <editor-fold desc="UserManagement">
    # Add User Method
    # Helper Methods
    def addUser(self, json_dict):
        uid = list(map(lambda x: x.uid, sm.query(OrthancUser)))
        if len(uid) == 0:
            uid = 0
        else:
            uid = max(uid)
            uid = uid + 1
        e_mail, access_level, full_name = MyHandler.extractUserModification(json_dict)

        user = sm.query(OrthancUser).filter_by(e_mail=e_mail).first()
        if user is None:
            new_user = OrthancUser(uid, full_name, e_mail, access_level)
            sm.add(new_user)
            sm.commit()
        else:
            # UPDATE
            user.access_level = access_level
            user.full_name = full_name
            sm.commit()
            pass

    # Remove User Method
    def removeUser(self, json_dict):
        e_mail, access_level, full_name = MyHandler.extractUserModification(json_dict)
        to_delete = sm.query(OrthancUser).filter_by(e_mail=e_mail).first()

        # @TODO remove associated priviledges

        if to_delete:
            sm.delete(to_delete)
            sm.commit()


    def updateUser(self, json_dict):
        e_mail, access_level, full_name = extractUserModification(json_dict)

        to_update = sm.query(OrthancUser).filter_by(e_mail=e_mail).first()

        if to_update.full_name != full_name :
            return

        if to_update.access_level != access_level:
            to_update.access_level = access_level
            pass

        # Update
        sm.add(to_update)
        sm.commit()

    @classmethod
    def extractUserModification(cls, json_dict):
        e_mail = json_dict[MOD_E_MAIL_MELLON]
        if MyHandler.TOKEN_ACCESS_LEVEL in json_dict:
            access_level = json_dict[MyHandler.TOKEN_ACCESS_LEVEL]
        else:
            access_level = ACCESS_LEVELS.GET_DEFAULT()
        full_name = json_dict[MOD_NAME_MELLON]
        return e_mail, access_level, full_name

    # </editor-fold>

    # <editor-fold desc="PatientManagement">

    def addPatient(self, json_dict):
        patient_id = MyHandler.extractPatient(json_dict)

        if sm.query(Patient).filter_by(orthanc_pid=patient_id).first() is None:
            # ADD PATIENT
            patient = Patient(patient_id, ACCESS_LEVELS.NURSE)
            sm.add(patient)
            sm.commit()
            pass
        else:
            # DO NOTHING
            # @TODO Log this instead of printing
            print "Patient %s already registered" % patient_id
            pass


    def removePatient(self, json_dict):
        patient_id = MyHandler.extractPatient(json_dict)

        to_delete = sm.query(Patient).filter_by(orthanc_pid=patient_id).first()

        # @TODO remove associated priviledges

        if to_delete is not None:
            sm.delete(to_delete)
            sm.commit()
        pass


    @classmethod
    def extractPatient(cls, json_dict):
        patient_id = json_dict[MyHandler.TOKEN_ORTHANC_ID]
        return patient_id
        pass

    # </editor-fold>

    # <editor-fold desc="PermissionManagement">
    def addAccessPermission(self, json_dict):
        if self.checkRights(json_dict[E_MAIL_MELLON]) is False:
            return None

        e_mail, patient_id = MyHandler.extractAccessPermissionParams(json_dict)

        # Patient must exist...
        patient = sm.query(Patient).filter_by(orthanc_pid=patient_id).first()
        user = sm.query(OrthancUser).filter_by(e_mail=e_mail).first()
        patient.permitted_users.append(user)

        sm.add(patient)
        sm.commit()
        pass

    # Remove the access permission
    # The metadata are provided by the json_dict
    def removeAccessPermission(self, json_dict):
        if self.checkRights(json_dict[E_MAIL_MELLON]) is False:
            return None

        e_mail, patient_id = MyHandler.extractAccessPermissionParams(json_dict)

        # Patient must exist...
        patient = sm.query(Patient).filter_by(orthanc_pid=patient_id).first()
        user = filter(lambda x: x.e_mail == e_mail, patient.permitted_users)

        if len(user) == 0:
            # @TODO log this
            print "User %s has no priviledges to remove at patient %s" % (e_mail, patient_id)
        else:
            user = user[0]
            patient.permitted_users.remove(user)

            sm.add(patient)
            sm.commit()

        # to_delete = sm.query(AccessPermission).filter_by(patient_id=patient_id, user_id=user_id).first()
        # sm.delete(to_delete)
        # sm.commit()

        pass

    # Access the parameters of an access permission
    # from the provided json dictionary
    # returns user_id which is normally an e-mail adress
    # patient-id the automatically generated id
    @classmethod
    def extractAccessPermissionParams(cls, json_dict):
        e_mail = json_dict[E_MAIL_MELLON]
        patient_id = json_dict[MyHandler.TOKEN_ORTHANC_ID]
        return e_mail, patient_id
        pass

    def checkRights(self, e_mail):
        user = sm.query(OrthancUser).filter_by(e_mail=e_mail).first()

        # If user does not exist
        if user is None:
            return False

        # Nurses or Students can't grant privileges
        if user.access_level < ACCESS_LEVELS.PHYSISCIAN:
            return False

        return True

    # </editor-fold>

    def parse_json_dict(self, json_string):
        json_dict = json.loads(json_string)

        if "token-value" in json_dict:
            uid, name = re.search("(.*?), (.*?)\.", json_dict["token-value"]).groups()
            uid = uid.strip()
            name = name.strip()

            json_dict[E_MAIL_MELLON] = uid
            json_dict[NAME_MELLON] = name

        return json_dict


if __name__ == '__main__':
    main()
