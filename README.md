# Orthanc Authorization 

Developed for the University of La Serena with the purpose of a prototypic educational PACS fulfilling the following criteria:
* Works as a normal hospital PACS in the Odontology
* Could be used additionally with Single Sign On for educational purposes -> allows to protect ressources and authorize access to specific users

## Summary 

The service is based on the [Orthanc Advanced Authorization Plugin](http://book.orthanc-server.com/plugins/authorization.html): If an Orthanc ressource or site of the browser is accessed a request is sent to a specified web-service.

This POST request consists of a json file which transmits important parameters of the request. This request and the parameters used for access are recived by the web service. In our case the environment variables of mod mellon are also sent via the **token-value** variable.



> {\
  "dicom-uid" : "123ABC",\
  "level" : "patient",\
  "method" : "get",\
  "orthanc-id" : "6eeded74-75005003-c3ae9738-d4a06a4f-6beedeb8",\
  "token-value" : "world"\
} 

The token value in our case is a combination of e-mail and name seperated by commas: 
**max@mustermail.com, Max Mustermann**.
It is used to identify users. 
Users and patients are added automatically to the Database if a request is sent.

The database is organised by an Object Relational Mapper which facilitates the administration of the database.

## Server paths

### Modification of access
- **userAdministration** Administer the privileges of users 
- **patientAdministration** Grant access to specific users
- **accessAdministration** Administrate the access for user groups

### Granting access to certain paths
- **privileges** Path for access granting for the privilege administration
- **grantAccess** Path for access granting for resources