from requests_ntlm import HttpNtlmAuth
import configparser
import os
import requests
import json
from lxml import etree

class SPlist:
    '''Initializes a Sharepoint List object and tries to 
    create it in sharepoint if it does not exist already.
    If said Sharepoint list does already exist,
    we pull its relevant list info from Sharepoint.'''
    def __init__(self, listName: str, config: configparser.ConfigParser = None) -> None:
        '''Initializes a session with the sharepoint website
        for the given list. Gets said list's field names from Sharepoint.
        
        :param str listName: Name of list to be found in Sharepoint website.

        :return None'''
        self.listName = listName
        self.workdir = 'C:\\Users\\riley.w\\Documents\\SQLTest'
        os.chdir(self.workdir)
        if not config:
            self.settings = self._cfg_load()
        else:
            self.settings = config
        self.urlSP = self.settings.get('SETTINGS', 'urlSP')
        self.urlSite = self.urlSP
        self.start_str = b"""<?xml version="1.0" encoding="utf-8"?>"""
        self.session = requests.Session()
        self._session_SP()
        if self.add_list(self.listName) is not None:
            self.newList = True
        else:
            self.newList = False
        self.fields = []
        if not self.newList:
            self.list = self.get_list()

    def _cfg_load(self) -> configparser.ConfigParser:
        '''loads config file settings for the following using the set work directory:
        - Sharepoint username/password
        - Sharepoint website URL
        - xlsx file locations'''
        os.chdir(self.workdir)
        cfg = configparser.ConfigParser()
        cfg.read('settings.cfg')
        return cfg

    def _basic_SOAP(self, command: str) -> None:
        '''Creates a basic envelope, namespace, and command for a new SOAP API call.
        
        :param str command: name of command to be executed in soap api call.
        
        :return None'''
        #make envelope and namespace map wrappers
        self.envelope = etree.Element("{http://schemas.xmlsoap.org/soap/envelope/}" + "Envelope", 
        nsmap={"SOAP-ENV": "http://schemas.xmlsoap.org/soap/envelope/",
        "ns0": "http://schemas.xmlsoap.org/soap/envelope/",
        "ns1": "http://schemas.microsoft.com/sharepoint/soap/",
        "xsi": "http://www.w3.org/2001/XMLSchema-instance"})

        #make header and command wrappers
        header = etree.SubElement(self.envelope, "{http://schemas.xmlsoap.org/soap/envelope/}Body")
        self.command = etree.SubElement(header, "{http://schemas.microsoft.com/sharepoint/soap/}" + command)

    @property
    def _get_form_digest_value(self) -> str:
        '''get form digest value for REST API call validation
        
        :return None'''
        #make rest call and return reponse
        response = self.session.post(url=str(self.urlSP + "/_api/contextinfo"))
        response.raise_for_status()
        return response.json()['FormDigestValue']

    def _add_command_param(self, param: str, value: str) -> None:
        '''Adds a single paramater and value to a SOAP API call request.
        
        :param str param: parameter name of SOAP command query.
        :param str value: accomanying value for parameter of SOAP command query.
        
        :return None'''
        subCommand = etree.SubElement(self.command, "{http://schemas.microsoft.com/sharepoint/soap/}" + str(param))
        if value != None:
            subCommand.text = str(value)

    def _add_command_params(self, params: list[str], values: list[str]) -> None:
        '''Adds a list of paramaters and values to a SOAP API call request.
        
        :param list[str] params: list of parameter names of SOAP command query.
        :param list[str] values: Accompanying list of values for parameters of SOAP command query.
        
        :return None'''
        for i, param in enumerate(params):
            subCommand = etree.SubElement(self.command, "{http://schemas.microsoft.com/sharepoint/soap/}" + str(param))
            if values != None and values[i] != None:
                subCommand.text = str(values[i])

    def _build_soap_request(self) -> str:
        '''Builds and returns string for SOAP API call.
        
        :return str: string built from XML of soap request.'''
        self.soap_request = (self.start_str + etree.tostring(self.envelope)).decode("utf-8")
        return self.soap_request

    def _session_SP(self) -> None:
        '''Uses SOAP API CALL to create a network session with the specified sharepoint URL in the provided config file.
        
        :return None'''
        #load settings

        #create session and its general parameters. This is used for both REST and SOAP APIs. Requires a user login!!!
        http_adaptor = requests.adapters.HTTPAdapter()
        self.session.mount("http://", http_adaptor)
        self.session.mount("https://", http_adaptor)
        self.session.headers.update({"user-agent": "db2SPlist/1.0"})
        self.session.headers.update({'Accept': 'application/json','Content-Type': 'application/json;odata=nometadata'})
        self.session.auth = HttpNtlmAuth(self.settings.get('USERS', 'username'), self.settings.get('USERS', 'password'))

        #get website url and soap envelope
        self.urlSite = self.urlSP + '/_vti_bin/Sites.asmx'
        self._basic_SOAP('GetListItems')

        #make parameters for SOAP call
        self._add_command_params(['listName', 'rowLimit'], ['Title', '0'])

        #make soap call to generate cookies
        self.session.post(self.urlSite, headers=self._SOAP_header('GetSite'), data=str(self._build_soap_request()).encode("utf-8"), verify=False, timeout=None)

        #get api context info from rest call and return it
        response = self.session.post(url=str(self.urlSP + "/_api/contextinfo"))
        response.raise_for_status()

    def add_list(self, listName: str) -> requests.Response:
        '''Uses SOAP API call to add a new list to the current sharepoint website.

        :param str listName: name of list we want to add to sharepoint.
        
        :return requests.Response: response from SOAP API call'''
        #get website url and soap envelope
        self.listName = listName
        self.urlSite = self.urlSP + '/_vti_bin/lists.asmx'
        self._basic_SOAP('AddList')

        #make parameters for SOAP call
        self._add_command_params(['listName', 'description', 'templateID'], [self.listName, 'ListTime', '100'])

        #make soap call and return reponse, as long as there is not an error
        response = self.session.post(self.urlSite, headers=self._SOAP_header('AddList'), data=str(self._build_soap_request()).encode("utf-8"), verify=False, timeout=None)
        if response.status_code not in  [400, 404, 500]:
            self.get_list()
            return response
        else:
            print('error with adding list')
            return None

    def _SOAP_header(self, action: str) -> dict[str, str]:
        '''Creates a soap header for the given SOAP action call.
        
        :return dict[str, str]: returns header dict that contains two strings: the Content-Type and SOAPAction.'''
        header = {
                "Content-Type": "text/xml; charset=UTF-8",
                "SOAPAction": "http://schemas.microsoft.com/sharepoint/soap/" + str(action),
        }
        return header

    def change_list(self, listName: str) -> None:
        '''Changes current Sharepoint list to the specified Sharepoint list and gets new list's info.
        
        :param str listName: name of list we want to switch to
        
        :return None'''
        self.listName = listName
        self.list = self.get_list()

    def get_list(self) -> list[str, requests.Response, list[dict]]:
        '''Uses SOAP API call to get all relevant info of a list, such as its field names and rows.

        :return list[str, requests.Response, list[dict]]: returns a list of the following:

        - str of original soap request
        - soap response
        - dict of all the rows in the Sharepoint list'''
        #get website url and soap envelope
        self.urlSite = self.urlSP + '/_vti_bin/lists.asmx'
        self._basic_SOAP('GetList')

        #make parameters for SOAP call
        self._add_command_param('listName', self.listName)

        #make soap call and return reponse, as long as there is not an error
        response = self.session.post(self.urlSite, headers=self._SOAP_header('GetList'), data=str(self._build_soap_request()).encode("utf-8"), verify=False, timeout=None)
        envelope = etree.fromstring(response.text.encode("utf-8"), parser=etree.XMLParser(huge_tree=False, recover=True))
        listSP = envelope[0][0][0][0]
        l = []
        for row in listSP.xpath("//*[re:test(local-name(), '.*Fields.*')]", namespaces={"re": "http://exslt.org/regular-expressions"})[0].getchildren():
            l.append({key: value for (key, value) in row.items()})
        self.fields={i["DisplayName"]: {"name": i["Name"], "type": i["Type"]} for i in l}
        #self.fields += fields
        if response.status_code not in  [400, 404, 500]:
            return [self._build_soap_request(), response, l]
        else:
            print('error with getting list')
            return [self._build_soap_request(), response, l]

    def add_item_to_SP_list(self, items: list[str]) -> list[str, requests.Response]:
        '''Uses SOAP API call to add items to the current Sharepoint list.
        
        :param list[str] items: list containing items as strings that we want to add to sharepoint.
        
        :return list[str, requests.Response]: returns a list of the following:

        - str of original soap request
        - soap response'''
        #get website url and soap envelope
        self.urlSite = self.urlSP + '/_vti_bin/lists.asmx'
        self._basic_SOAP('UpdateListItems')

        #add command and listname to soap call
        self._add_command_param('listName', self.listName)
        updates = etree.SubElement(self.command, "{http://schemas.microsoft.com/sharepoint/soap/}updates")
        batch = etree.SubElement(updates, "Batch")
        batch.set("OnError", "Return")
        batch.set("ListVersion", "1")

        #add each item in items by making an ID and CMD for soap call
        for index, row in enumerate(items, 1):
            method = etree.SubElement(batch, "Method")
            method.set("ID", str(index))
            method.set("Cmd", 'New')

            #add each key and value of each item to soap call by adding them as fields
            for key, value in row.items():
                field = etree.SubElement(method, "Field")
                field.set("Name", key)
                field.text = str(value)

        #make soap call and return reponse
        response = self.session.post(self.urlSite, headers=self._SOAP_header('UpdateListItems'), data=str(self._build_soap_request()).encode("utf-8"), verify=False, timeout=None)
        response.raise_for_status()
        return [self._build_soap_request(), response]

    def query_SP_list_items(self, query:dict[str, list[str]], fields:list[str]) -> list[requests.Response, int]:
        '''Uses SOAP API call to query the current Sharepoint list and see whether it contains certain items related to the query.

        :param dict[list[str]] query: a dict containing the following:
        
        - query type as a string
        - list of items

        :param dict[list[str]] fields: a dict containing a list of the field names for said query.
        
        :return list[requests.Response, int]: returns a list of the following:

        - soap response
        - number of items in query'''
        #get website url and soap envelope
        self.urlSite = self.urlSP + '/_vti_bin/lists.asmx'
        self._basic_SOAP('GetListItems')

        #add listname
        self._add_command_param('listName', self.listName)
        
        #set fields we want to query in SOAP request
        viewFields = etree.SubElement(self.command, "{http://schemas.microsoft.com/sharepoint/soap/}viewFields")
        viewFields.set("ViewFieldsOnly", "true")
        ViewFields = etree.SubElement(viewFields, "ViewFields")
        for field in fields:
            view_field = etree.SubElement(ViewFields, "FieldRef")
            view_field.set("Name", self.fields[field]['name'])

        #convert our query into SOAP request format
        modified_query = dict()
        where = etree.Element('Where')
        parents = [where]
        for field in query["Where"]:

            #add and query
            if field == "And":
                parents.append(etree.SubElement(parents[-1], "And"))

            #add or query
            elif field == "Or":
                if parents[-1].tag == "Or":
                    parents.pop()
                parents.append(etree.SubElement(parents[-1], "Or"))
            
            #add data we want to search for to SOAP request
            else:
                type = etree.SubElement(parents[-1], field[0])
                fieldRef = etree.SubElement(type, "FieldRef")
                if "LinkTitle" in self.fields[field[1]]['name']:
                    fieldRef.set("Name", "Title")
                else:
                    fieldRef.set("Name", self.fields[field[1]]['name'])
                value = etree.SubElement(type, "Value")
                value.set("Type", "Text")
                value.text = field[2]
            modified_query["Where"] = where

            #insert modified query into soap request
            queryTree = etree.SubElement(self.command, "{http://schemas.microsoft.com/sharepoint/soap/}query")
            Query = etree.SubElement(queryTree, "Query")
            Query.append(modified_query["Where"])

        #set rowlimit to 0 so we can search every row in SP list
        self._add_command_param('rowLimit', '0')

        #make soap call and return reponse
        soap = self._build_soap_request()
        response = self.session.post(self.urlSite, headers=self._SOAP_header('GetListItems'), data=str(self._build_soap_request()).encode("utf-8"), verify=False, timeout=None)
        envelope = etree.fromstring(response.text.encode("utf-8"),parser=etree.XMLParser(huge_tree=False,recover=True))
        listitems = envelope[0][0][0][0][0]
        listcount = listitems.attrib['ItemCount']

        #if no items for the query were found or there was an error with the soap call, we return nothing. Otherwise, return response.
        if listcount == '0' or response.status_code in [400, 404, 500]:
            return None
        else:
            return [response, listcount]

    def create_field(self, fieldName: str, field_type=2, required="false", unique="false", static_name:str=None) -> requests.Response.json:
        '''Uses Rest API call to create a Sharepoint list field in the current Sharepoint list.
        
        :param str fieldName: name of field to create
        :param int field_type: field type as indicated by number. Check sharepoint API for which each number indicates for the field type.
        :param str required: marks whether field is a required field for a new item entry.
        :param str unique: marks whether field name should be unique.
        :param str static_name: gives the field name an additional static name that cannot be changed.

        :return requests.Response.json: json of response from soap call
        '''
        #add parameters for REST API call to json
        update_data = {}
        update_data['__metadata'] = {'type': 'SP.Field'}
        update_data['Title'] = fieldName
        update_data['FieldTypeKind'] = field_type
        update_data['Required'] = required
        update_data['EnforceUniqueValues'] = unique
        update_data['StaticName'] = static_name
        update_data['TypeDisplayName'] = fieldName
        body = json.dumps(update_data)

        #make url and header
        self.urlSite = self.urlSP + f"/_api/lists/getbytitle('{self.listName}')/Fields"
        headers = {'Accept': 'application/json;odata=verbose',
                    'Content-Type': 'application/json;odata=verbose',
                    'X-RequestDigest': self._get_form_digest_value}

        #make REST api call and return response
        response = self.session.post(self.urlSite, headers=headers, data=body)
        response.raise_for_status()
        return response.json()

    def get_view_internal_ID(self, viewName: str) -> str:
        '''Uses REST API call to make get internal ID of a Sharepoint list view.
        
        :param str viewName: name of view we want the internal ID of
        
        :return str: view ID'''
        #make url and header
        headers = {'Accept': 'application/json;odata=verbose',
                    'Content-Type': 'application/json;odata=verbose',
                    'X-RequestDigest': self._get_form_digest_value}
        self._urlSite = self.urlSP + f"/_api/web/lists/getbytitle('{self.listName}')/Views/getbytitle('{viewName}')"

        #make REST api call and return internal view ID
        response = self.session.post(self._urlSite, headers=headers)
        response.raise_for_status()
        responseText = json.loads(response.text)
        viewID = responseText["d"]["Id"]
        return viewID

    #makes field visible to frontend sharepoint user via REST API call
    def make_field_visible(self, fieldName: str) -> requests.Response.json:
        '''Uses REST API call to make Sharepoint List field visible to frontend sharepoint user.
        
        :param str fieldName: name of field we want to make visible
        
        :return requests.Response.json: json response of SOAP request'''
        #make url and header
        headers = {'Accept': 'application/json;odata=verbose',
                    'Content-Type': 'application/json;odata=verbose',
                    'X-RequestDigest': self._get_form_digest_value}
        self.urlSite = self.urlSP + f"/_api/web/lists/getbytitle('{self.listName}')/Views('{str(self.get_view_internal_ID('All Items'))}')/ViewFields/AddViewField('{fieldName}')"

        #make REST api call and return response
        response = self.session.post(self.urlSite, headers=headers)
        response.raise_for_status()
        return response.json()

    #makes a field to not be required for a list. Uses REST API
    def no_require_field(self, fieldName: str) -> requests.Response.json:
        '''Uses REST API call to mark a sharepoint list field as a non required entry.
        
        :param str fieldName: name of field we want to mark as not being required for the current list.

        :return requests.Response.json: json response of SOAP request'''
        #add parameters for REST API call to json
        update_data = {}
        update_data['__metadata'] = {'type': 'SP.Field'}
        update_data['Required'] = 'false'
        body = json.dumps(update_data)

        #make url and header
        headers = {'Accept': 'application/json;odata=verbose',
                    'Content-Type': 'application/json;odata=verbose',
                    "IF-MATCH": "*",
                    "X-HTTP-Method": "PATCH",
                    'X-RequestDigest': self._get_form_digest_value}
        self.urlSite = self.urlSP + f"/_api/web/lists/getbytitle('{self.listName}')/Fields/getbytitle('{fieldName}')"

        #make REST api call and return response
        response = self.session.post(self.urlSite, headers=headers, data=body)
        response.raise_for_status()
        if response.status_code != 204:
            return response.json()

    def get_fields(self) -> list[str]:
        '''Uses REST API call to get fields of SharePoint list.
        
        :return list[str]: list of internal field names.'''
        #make url and header
        headers = {'Accept': 'application/json;odata=verbose',
                    'Content-Type': 'application/json;odata=verbose',
                    'X-RequestDigest': self._get_form_digest_value}
        self.urlSite = self.urlSP + f"/_api/web/lists/getbytitle('{self.listName}')/Views/getbytitle('{'All Items'}')/viewFields"

        #make REST api call and return internal field names
        response = self.session.post(self.urlSite, headers=headers)
        response.raise_for_status()
        responseText = json.loads(response.text)
        fieldsInternalNames = responseText["d"]["Items"]["results"]
        return fieldsInternalNames

    def delete_field(self, fieldName: str) -> requests.Response.json:
        '''Uses REST API call to delete SharePoint list field. DOES NOT WORK, NEED API KEY.

        :param str fieldName: name of field we want to delete.
        
        :return requests.Response.json: json response of SOAP request'''
        #make url and header
        headers = {'Accept': 'application/json;odata=verbose',
                    'Content-Type': 'application/json;odata=verbose',
                    "IF-MATCH": "*",
                    "X-HTTP-Method-Override": "DELETE",
                    'X-RequestDigest': self._get_form_digest_value}
        self.urlSite = self.urlSP + f"/_api/web/lists/getbytitle('{self.listName}')/Fields/getbytitle('{fieldName}')"
        response = self.session.post(self.urlSite, headers=headers)
        response.raise_for_status()
        if response.status_code != 204:
            return response.json()

    def update_field_name(self, fieldNameOld: str, fieldNameNew: str) -> requests.Response.json:
        '''Uses REST API call to update name of field in SharePoint list.

        :param str fieldNameOld: name of field we want to rename
        :param str fieldNameNew: new name of field
        
        :return requests.Response.json: json response of SOAP request'''
        #add parameters for REST API call to json
        update_data = {}
        update_data['__metadata'] = {'type': 'SP.Field'}
        update_data['Title'] = fieldNameNew
        update_data['TypeDisplayName'] = fieldNameNew
        body = json.dumps(update_data)

        #make url and header
        headers = {'Accept': 'application/json;odata=verbose',
                    'Content-Type': 'application/json;odata=verbose',
                    "IF-MATCH": "*",
                    "X-HTTP-Method": "PATCH",
                    'X-RequestDigest': self._get_form_digest_value}
        self.urlSite = self.urlSP + f"/_api/web/lists/getbytitle('{self.listName}')/Fields/getbytitle('{fieldNameOld}')"

        #make REST api call and return response
        response = self.session.post(url=self.urlSite, headers=headers, data=body)
        if response.status_code != 204:
            return response.json()