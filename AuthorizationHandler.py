import json
import SocketServer
from BaseHTTPServer import BaseHTTPRequestHandler
from DatabaseSession import sm
from Database import OrthancUser, Patient
import re
from ACCESSLEVELS import ACCESS_LEVELS

"""
By Martin Leipert
martin.leipert@fau.de

This serves as web service for the Orthanc Authorization Plugin 

-> To access some orthanc ressources post requests are sent 
to a web service which does grant access or refuses it
therefore a request is sent containing metadata about the ressource

in this project environment variables from the Apache modification 
mod mellon are sent as additional metadata 
to allow access management via single sign on
in an educational environment by token-value as 
MELLON_uid, MELLON_name
"""

HOST = ''
PORT = 8000

# The mellon environment variables which are forwarded
# @TODO maybe implement also "grant access to all students"
E_MAIL_MELLON = 'MELLON_uid'
MOD_E_MAIL_MELLON = 'MOD_%s' % E_MAIL_MELLON
NAME_MELLON = 'MELLON_name'
MOD_NAME_MELLON = 'MOD_%s' % NAME_MELLON
TOKEN_ORTHANC_ID = 'orthanc-id'
TOKEN_ACCESS_LEVEL = 'access-level'

"""
Main Method that starts the httpd server
the server may only be killed by force at the moment (e.g. shutting down the script)
"""
def main():
    # Start the web server
    httpd = SocketServer.TCPServer((HOST, PORT), AuthorizationHandler)
    httpd.serve_forever()


"""
Self implemented webserver which handles requests and gives permissions

* Patient Management
* User Management
* Access Permission Management
* Access Granting
"""

class AuthorizationHandler(BaseHTTPRequestHandler):

    # Paths for the HTTP service
    # According to REST
    # -> GET to list all values
    # -> POST to modify
    # -> DELETE to remove

    # Paths for the direct management of priviledges via REST
    # Administer the privileges of users
    PATH_USER_ADMINISTRATION = '/userAdministration/'
    # Administer patients -> Grant access to specific users
    PATH_PATIENT_ADMINISTRATION = '/patientAdministration/'
    # Administrate the access levels
    PATH_ACCESS_ADMINISTRATION = '/accessAdministration/'

    # Paths which are for granting access to ressources
    # Access the user priviledges / access levels
    GRANT_PRIVILEGE_ACCESS = '/privileges/'
    # Path for access granting by post request
    # -> By the Authorisation plugin
    GRANT_ACCESS_PATH = '/grantAccess/'


	# GET requests are mainly for privilege listing
    # <editor-fold desc="RequestManagement">
    def do_GET(self):
	    
	    # List all the users 
	    # Respond with their e-mail adresses and full names
        if self.path == AuthorizationHandler.PATH_USER_ADMINISTRATION:
            # TODO First query user priviledges
            # Query the users in the database
            users = sm.query(OrthancUser).all()

			# Extract their mail and fullname and convert this into tuples
            user_mails_fullnames = list(map(lambda x: (x.e_mail, x.full_name), users))
            # Pack to a dict and respond
            response_dict = {'user-ids': dict(user_mails_fullnames)}
            self.sendResponseDict(response_dict)

		# List all patients registered in the service
        elif self.path == AuthorizationHandler.PATH_PATIENT_ADMINISTRATION:
            # Respond with a dict full of patient ids
            patients = sm.query(Patient).all()
            patient_ids = list(map(lambda x: (x.orthanc_pid), patients))
            response_dict = {AuthorizationHandler.TOKEN_ORTHANC_ID + 's': patient_ids}
            self.sendResponseDict(response_dict)

	# Post request for settign and modification
    def do_POST(self):

		# Get the json dict which is included in all post requests
        content_len = int(self.headers.getheader('content-length', 0))
        post_body = self.rfile.read(content_len)
        json_dict = self.parse_json_dict(post_body)

		# Call the methods which are for setting the corresponding object

		# Adding Permissions / objects to the service
		# Add user to the Server with specified attributes
        if self.path == AuthorizationHandler.PATH_USER_ADMINISTRATION:
            self.addUser(json_dict)
            self.send_response(200)

		# Add an access permission to a patient for a user
        elif self.path == AuthorizationHandler.PATH_ACCESS_ADMINISTRATION:
            self.addAccessPermission(json_dict)
            self.send_response(200)

		# Add patient to the service with the specified access level
        elif self.path == AuthorizationHandler.PATH_PATIENT_ADMINISTRATION:
            self.addPatient(json_dict)
            self.send_response(200)

        # Check if user may grant permissions
        elif self.path == AuthorizationHandler.GRANT_PRIVILEGE_ACCESS:
            e_mail = json_dict[E_MAIL_MELLON]
            user = sm.query(OrthancUser).filter_by(e_mail=e_mail).first()

			# Acess to priviledge adminstration granted?
            # -> For adminstration of this service
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

		# For access to a ressource requests by Orthanc
	    # Access requests in the PACS
        elif self.path == AuthorizationHandler.GRANT_ACCESS_PATH:

			# Level defines the type of ressource
            level = json_dict["level"]

			# Extract the mail and name of accessing user
            e_mail = json_dict[E_MAIL_MELLON]
            name = json_dict[NAME_MELLON]

			# Grant the access
            response_dict = {
                "granted": False,
                "validity": 5
            }

			# If the level is patient -> Check if the user may access the patient
            if level == "patient":

	            # Orthanc id of the patient
                orthanc_id = json_dict[TOKEN_ORTHANC_ID]

				# Query patient and user
                # @TODO Get patient
                patient = sm.query(Patient).filter_by(orthanc_pid=orthanc_id).first()
                user = sm.query(OrthancUser).filter_by(e_mail=e_mail).first()

				# Add patient to access managment if he / she is not registered
                if patient is None:

                    dict_to_add = {
	                    AuthorizationHandler.TOKEN_ORTHANC_ID: orthanc_id
                    }
                    self.addPatient(dict_to_add)

                    # Query the stored patient for further proceeding
                    patient = sm.query(Patient).filter_by(orthanc_pid=orthanc_id).first()

				# Add the user if he / she is not registered
                if user is None:

	                # Add the user with default access level
                    dict_to_add = {
                        MOD_E_MAIL_MELLON: e_mail,
                        MOD_NAME_MELLON: name,
                        TOKEN_ACCESS_LEVEL: ACCESS_LEVELS.GET_DEFAULT()
                    }
                    self.addUser(dict_to_add)

	                # Query for further proceeding
                    user = sm.query(Patient).filter_by(orthanc_pid=orthanc_id).first()

				# If the patient may be accessed because of the general privileges
                if user.access_level >= patient.access_lvl:
                    response_dict["granted"] = True
                # If the patient may be accessed by specific privileges
                elif user in patient.permitted_users:
                    response_dict["granted"] = True

            # Access -> System in general
            elif level == "system":

                # Extract the uri
                uri = json_dict["uri"]

                # Get the user to assess the privileges
                user = sm.query(OrthancUser).filter_by(e_mail=e_mail).first()

                # TODO Access for user administration and user query
                uris_admin = ["priviledgeAdministration"]

                if uri in uris_admin:
                    if user.access_level >= ACCESS_LEVELS.PHYSISCIAN:
                        response_dict["granted"] = True

                # Generally grant access to Orthanc browser to everyone in the System
                elif uri is "/":
                    response_dict["granted"] = True
                pass

            else:
                response_dict["granted"] = True

			# Write the json into a string and send it as response
            content = json.dumps(response_dict, ensure_ascii=False)
            self.send_response(200)
            self.send_header("Content-Length", len(content))
            self.send_header("Content-Type", "text/json")
            self.end_headers()
            self.wfile.write(content)

        pass

    # Delete requests -> To eliminate privileges, users and
    def do_DELETE(self):
        content_len = int(self.headers.getheader('content-length', 0))
        post_body = self.rfile.read(content_len)
        json_dict = self.parse_json_dict(post_body)

        # Delete the user
        if self.path == AuthorizationHandler.PATH_USER_ADMINISTRATION:
            self.removeUser(json_dict)

        # Delete permission
        elif self.path == AuthorizationHandler.PATH_ACCESS_ADMINISTRATION:
            self.removeAccessPermission(json_dict)

        # Delete patient
        elif self.path == AuthorizationHandler.PATH_PATIENT_ADMINISTRATION:
            self.removePatient(json_dict)

        self.send_response(200)


    # Put intended for updates
    # Problem: Not working properly
    def do_PUT(self):
        content_len = int(self.headers.getheader('content-length', 0))
        post_body = self.rfile.read(content_len)
        json_dict = self.parse_json_dict(post_body)

        # Update a user -> The only object that may require updates
        if self.path == AuthorizationHandler.PATH_USER_ADMINISTRATION:
            self.updateUser(json_dict)

        self.send_response(200)

    # Options for Cross-Site-Scripting
    def do_OPTIONS(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_response(200, "ok")
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
        e_mail, access_level, full_name = AuthorizationHandler.extractUserModification(json_dict)

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
        e_mail, access_level, full_name = AuthorizationHandler.extractUserModification(json_dict)
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
        if AuthorizationHandler.TOKEN_ACCESS_LEVEL in json_dict:
            access_level = json_dict[AuthorizationHandler.TOKEN_ACCESS_LEVEL]
        else:
            access_level = ACCESS_LEVELS.GET_DEFAULT()
        full_name = json_dict[MOD_NAME_MELLON]
        return e_mail, access_level, full_name

    # </editor-fold>

    # <editor-fold desc="PatientManagement">

    def addPatient(self, json_dict):
        patient_id = AuthorizationHandler.extractPatient(json_dict)

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
        patient_id = AuthorizationHandler.extractPatient(json_dict)

        to_delete = sm.query(Patient).filter_by(orthanc_pid=patient_id).first()

        # @TODO remove associated priviledges

        if to_delete is not None:
            sm.delete(to_delete)
            sm.commit()
        pass


    @classmethod
    def extractPatient(cls, json_dict):
        patient_id = json_dict[AuthorizationHandler.TOKEN_ORTHANC_ID]
        return patient_id
        pass

    # </editor-fold>

    # <editor-fold desc="PermissionManagement">
    def addAccessPermission(self, json_dict):
        if self.checkRights(json_dict[E_MAIL_MELLON]) is False:
            return None

        e_mail, patient_id = AuthorizationHandler.extractAccessPermissionParams(json_dict)

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

        e_mail, patient_id = AuthorizationHandler.extractAccessPermissionParams(json_dict)

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
        patient_id = json_dict[AuthorizationHandler.TOKEN_ORTHANC_ID]
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
