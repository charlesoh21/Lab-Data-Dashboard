from requests_ntlm import HttpNtlmAuth
import sqlite3
import configparser
import os
import requests
import json
from lxml import etree

#change workdir to where you keep your .db, .cfg, etc files
workdir = 'C:\\Users\\riley.w\\Documents\\SQLTest'
start_str = b"""<?xml version="1.0" encoding="utf-8"?>"""
global urlSP

#basic_SOAP builds the skeleton for a SOAP API request for sharepoint.
def basic_SOAP(command):
    #make envelope and namespace map wrappers
    envelope = etree.Element("{http://schemas.xmlsoap.org/soap/envelope/}" + "Envelope", 
    nsmap={"SOAP-ENV": "http://schemas.xmlsoap.org/soap/envelope/",
     "ns0": "http://schemas.xmlsoap.org/soap/envelope/",
      "ns1": "http://schemas.microsoft.com/sharepoint/soap/",
       "xsi": "http://www.w3.org/2001/XMLSchema-instance"})

    #make header and command wrappers
    header = etree.SubElement(envelope, "{http://schemas.xmlsoap.org/soap/envelope/}Body")
    command = etree.SubElement(header, "{http://schemas.microsoft.com/sharepoint/soap/}" + command)
    return command, envelope

#get form digest value for REST API call validation
def get_form_digest_value(session):
    #make rest call and return reponse
    response = session.post(url=str(urlSP + "/_api/contextinfo"))
    response.raise_for_status()
    return response.json()['FormDigestValue']

#adds item to SP list via SOAP call
def add_item_to_SP_list(session, listName, items, kind):
    #get website url and soap envelope
    urlSite = urlSP + '/_vti_bin/lists.asmx'
    command, envelope = basic_SOAP('UpdateListItems')

    #add command and listname to soap call
    etree.SubElement(command, "{http://schemas.microsoft.com/sharepoint/soap/}" + 'listName').text  = listName
    updates = etree.SubElement(command, "{http://schemas.microsoft.com/sharepoint/soap/}updates")
    batch = etree.SubElement(updates, "Batch")
    batch.set("OnError", "Return")
    batch.set("ListVersion", "1")

    #add each item in items by making an ID and CMD for soap call
    for index, row in enumerate(items, 1):
        method = etree.SubElement(batch, "Method")
        method.set("ID", str(index))
        method.set("Cmd", kind)

        #add each key and value of each item to soap call by adding them as fields
        for key, value in row.items():
            field = etree.SubElement(method, "Field")
            field.set("Name", key)
            field.text = str(value)

    #make soap request and header
    soap_request = (start_str + etree.tostring(envelope)).decode("utf-8")
    header = {
            "Content-Type": "text/xml; charset=UTF-8",
            "SOAPAction": "http://schemas.microsoft.com/sharepoint/soap/UpdateListItems",
    }

    #make soap call and return reponse
    response = session.post(urlSite, headers=header, data=str(soap_request).encode("utf-8"), verify=False, timeout=None)
    response.raise_for_status()
    return response

#query a SP list to see whether item(s) exist in it or not
def query_SP_list_items(session, listName, query, fields, cols, fieldsInternal):
    #get website url and soap envelope
    urlSite = urlSP + '/_vti_bin/lists.asmx'
    command, envelope = basic_SOAP('GetListItems')

    #add listname
    etree.SubElement(command, "{http://schemas.microsoft.com/sharepoint/soap/}" + 'listName').text  = listName

    #get internal field names for field names we want to query
    for i, val in enumerate(fields):
        for j in range(len(cols)):
            if val == cols[j]:
                fields[i] = fieldsInternal[j]
    
    #set fields we want to query in SOAP request
    viewFields = etree.SubElement(command, "{http://schemas.microsoft.com/sharepoint/soap/}viewFields")
    viewFields.set("ViewFieldsOnly", "true")
    ViewFields = etree.SubElement(viewFields, "ViewFields")
    for field in fields:
        view_field = etree.SubElement(ViewFields, "FieldRef")
        view_field.set("Name", field)

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
            for i in range(len(cols)):
                if field[1] == cols[i]:
                    if fieldsInternal[i] == "LinkTitle":
                        fieldRef.set("Name", "Title")
                    else:
                        fieldRef.set("Name", fieldsInternal[i])
            value = etree.SubElement(type, "Value")
            value.set("Type", "Text")
            value.text = field[2]
        modified_query["Where"] = where

        #insert modified query into soap request
        queryTree = etree.SubElement(command, "{http://schemas.microsoft.com/sharepoint/soap/}query")
        Query = etree.SubElement(queryTree, "Query")
        Query.append(modified_query["Where"])

    #set rowlimit to 0 so we can search every row in SP list
    etree.SubElement(command, "{http://schemas.microsoft.com/sharepoint/soap/}" + 'rowLimit').text  = "0"

    #make soap request and header
    soap_request = (start_str + etree.tostring(envelope)).decode("utf-8")
    header = {
            "Content-Type": "text/xml; charset=UTF-8",
            "SOAPAction": "http://schemas.microsoft.com/sharepoint/soap/GetListItems",
    }

    #make soap call and return reponse
    response = session.post(urlSite, headers=header, data=str(soap_request).encode("utf-8"), verify=False, timeout=None)
    envelope = etree.fromstring(response.text.encode("utf-8"),parser=etree.XMLParser(huge_tree=False,recover=True))
    listitems = envelope[0][0][0][0][0]
    listcount = listitems.attrib['ItemCount']

    #if no items for the query were found or there was an error with the soap call, we return nothing. Otherwise, return response.
    if listcount == '0' or response.status_code in [400, 404, 500]:
        return None
    else:
        return response

def session_SP():
    #load settings
    settings = cfgLoad()

    #create session and its general parameters. This is used for both REST and SOAP APIs. Requires a user login!!!
    http_adaptor = requests.adapters.HTTPAdapter()
    session = requests.Session()
    session.mount("http://", http_adaptor)
    session.mount("https://", http_adaptor)
    session.headers.update({"user-agent": "db2SPlist/1.0"})
    session.headers.update({'Accept': 'application/json','Content-Type': 'application/json;odata=nometadata'})
    session.auth = HttpNtlmAuth(settings.get('USERS', 'username'), settings.get('USERS', 'password'))

    #get website url and soap envelope
    urlSite = urlSP + '/_vti_bin/Sites.asmx'
    command, envelope = basic_SOAP('GetListItems')

    #make parameters for SOAP call
    etree.SubElement(command, "{http://schemas.microsoft.com/sharepoint/soap/}" + 'listName').text  = 'Title'
    etree.SubElement(command, "{http://schemas.microsoft.com/sharepoint/soap/}" + 'rowLimit').text = '0'

    #make soap request and header
    soap_request = (start_str + etree.tostring(envelope)).decode("utf-8")
    header = {
            "Content-Type": "text/xml; charset=UTF-8",
            "SOAPAction": "http://schemas.microsoft.com/sharepoint/soap/GetSite",
    }

    #make soap call to generate cookies
    session.post(urlSite, headers=header, data=str(soap_request).encode("utf-8"), verify=False, timeout=None)

    #get api context info from rest call and return it
    response = session.post(url=str(urlSP + "/_api/contextinfo"))
    response.raise_for_status()
    return session

def add_list(session, listName):
    #get website url and soap envelope
    urlSite = urlSP + '/_vti_bin/lists.asmx'
    command, envelope = basic_SOAP('AddList')

    #make parameters for SOAP call
    etree.SubElement(command, "{http://schemas.microsoft.com/sharepoint/soap/}" + 'listName').text  = listName
    etree.SubElement(command, "{http://schemas.microsoft.com/sharepoint/soap/}" + 'description').text = 'ListTime'
    etree.SubElement(command, "{http://schemas.microsoft.com/sharepoint/soap/}" + 'templateID').text = '100'

    #make soap request and header
    soap_request = (start_str + etree.tostring(envelope)).decode("utf-8")
    header = {
            "Content-Type": "text/xml; charset=UTF-8",
            "SOAPAction": "http://schemas.microsoft.com/sharepoint/soap/AddList",
    }

    #make soap call and return reponse, as long as there is not an error
    response = session.post(urlSite, headers=header, data=str(soap_request).encode("utf-8"), verify=False, timeout=None)
    if response.status_code not in  [400, 404, 500]:
        return response
    else:
        print('error with adding list')
        return None

def create_field(session, listName, title, field_type=2, required="false", unique="false", static_name=None):

    #add parameters for REST API call to json
    update_data = {}
    update_data['__metadata'] = {'type': 'SP.Field'}
    update_data['Title'] = title
    update_data['FieldTypeKind'] = field_type
    update_data['Required'] = required
    update_data['EnforceUniqueValues'] = unique
    update_data['StaticName'] = static_name
    update_data['TypeDisplayName'] = title
    body = json.dumps(update_data)

    #make url and header
    url = urlSP + f"/_api/lists/getbytitle('{listName}')/Fields"
    headers = {'Accept': 'application/json;odata=verbose',
                'Content-Type': 'application/json;odata=verbose',
                'X-RequestDigest': get_form_digest_value(session)}

    #make REST api call and return response
    response = session.post(url, headers=headers, data=body)
    response.raise_for_status()
    return response.json()

def get_view_internal_ID(session, viewName, listName):
    #make url and header
    headers = {'Accept': 'application/json;odata=verbose',
                'Content-Type': 'application/json;odata=verbose',
                'X-RequestDigest': get_form_digest_value(session)}
    url = urlSP + f"/_api/web/lists/getbytitle('{listName}')/Views/getbytitle('{viewName}')"

    #make REST api call and return internal view ID
    response = session.post(url, headers=headers)
    response.raise_for_status()
    responseText = json.loads(response.text)
    viewID = responseText["d"]["Id"]
    return viewID


def make_field_visible(session, title, listName, viewID):
    #make url and header
    headers = {'Accept': 'application/json;odata=verbose',
                'Content-Type': 'application/json;odata=verbose',
                'X-RequestDigest': get_form_digest_value(session)}
    url = urlSP + f"/_api/web/lists/getbytitle('{listName}')/Views('{viewID}')/ViewFields/AddViewField('{title}')"

    #make REST api call and return response
    response = session.post(url, headers=headers)
    response.raise_for_status()
    return response.json()


def no_require_field(session, listName, field):
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
                'X-RequestDigest': get_form_digest_value(session)}
    url = urlSP + f"/_api/web/lists/getbytitle('{listName}')/Fields/getbytitle('{field}')"

    #make REST api call and return response
    response = session.post(url, headers=headers, data=body)
    response.raise_for_status()
    if response.status_code != 204:
        return response.json()

def get_fields(session, listName):
    #make url and header
    headers = {'Accept': 'application/json;odata=verbose',
                'Content-Type': 'application/json;odata=verbose',
                'X-RequestDigest': get_form_digest_value(session)}
    url = urlSP + f"/_api/web/lists/getbytitle('{listName}')/Views/getbytitle('{'All Items'}')/viewFields"

    #make REST api call and return internal field names
    response = session.post(url, headers=headers)
    response.raise_for_status()
    responseText = json.loads(response.text)
    fieldsInternalNames = responseText["d"]["Items"]["results"]
    return fieldsInternalNames

def delete_field(session, listName, field):
    #make url and header
    headers = {'Accept': 'application/json;odata=verbose',
                'Content-Type': 'application/json;odata=verbose',
                "IF-MATCH": "*",
                "X-HTTP-Method-Override": "DELETE",
                'X-RequestDigest': get_form_digest_value(session)}
    url = urlSP + f"/_api/web/lists/getbytitle('{listName}')/Fields/getbytitle('{field}')"
    response = session.post(url, headers=headers)
    response.raise_for_status()
    if response.status_code != 204:
        return response.json()

def update_field_name(session, field, new, listName):
    #add parameters for REST API call to json
    update_data = {}
    update_data['__metadata'] = {'type': 'SP.Field'}
    update_data['Title'] = new
    update_data['TypeDisplayName'] = new
    body = json.dumps(update_data)

    #make url and header
    headers = {'Accept': 'application/json;odata=verbose',
                'Content-Type': 'application/json;odata=verbose',
                "IF-MATCH": "*",
                "X-HTTP-Method": "PATCH",
                'X-RequestDigest': get_form_digest_value(session)}
    url = urlSP + f"/_api/web/lists/getbytitle('{listName}')/Fields/getbytitle('{field}')"

    #make REST api call and return response
    response = session.post(url=url, headers=headers, data=body)
    if response.status_code != 204:
        return response.json()

#function that converts rows in database into a single dict
def db2dict(cur, row):
    dict = {}
    for idx, col in enumerate(cur.description):
        dict[col[0]] = row[idx]
    return dict

#used to get various env variables from .cfg file
def cfgLoad():
    os.chdir(workdir)
    cfg = configparser.ConfigParser()
    cfg.read('settings.cfg')
    return cfg

#convert db entries to sp list entries.
def db2SPlist():
    global urlSP
    #get settings from cfg file and put them in appropriate variables
    settings = cfgLoad()
    urlSP = settings.get('SETTINGS', 'urlSP')
    session = session_SP()

    #setup and get connection to db
    con = sqlite3.connect(str(workdir + "\\AgingLogDB.db"))
    con.row_factory = db2dict
    cur = con.cursor()

    #get table names and put them in a list
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    enumTables = cur.fetchall()
    dbTableNames = []
    for tableName in enumTables:
        dbTableNames.append(tableName['name'])

    #iterate through tables and upload them to a SP list for each table
    for listName in dbTableNames:

        #get all entries and column names from current table
        cur.execute("SELECT * FROM \"" + listName + "\"")
        colNames = list(map(lambda x: x[0], cur.description))
        enumItems = cur.fetchall()

        #try to make a new list. If we succeed, set newList to true, else false.
        if add_list(session=session,listName=listName) is not None:
            newList = True
        else:
            newList = False

        #if this is a newlist, initialize the column names.
        print(listName)
        viewID = get_view_internal_ID(session, 'All Items', listName)
        if newList:
            #rename default 'title' column to the first column in our db table
            update_field_name(session, field='Title', new=colNames[0], listName=listName)

            #iterate through db cols
            for i in colNames:

                #inSPlist is a db entry used to determine whether an entry is already in SP. Thus, we skip adding a column for it to the SP list.
                if i == colNames[0] or i == "in_SP_list":
                    continue
                else:
                    #create the column and make it visible in our default view in sharepoint
                    create_field(session=session, listName = listName, title = i)
                    make_field_visible(session=session, listName = listName, title = i, viewID=viewID)
            
            #re-establish connection to list so that we get updated info, and make the default column not required
            #curList = site.List(listName)
            no_require_field(session=session, listName = listName, field=colNames[0])

        fieldsInternal = get_fields(session, listName)
        fieldsInternal.append('in_SP_list')

        for d in enumItems:
            for i in range(len(fieldsInternal)):
                if i == 0:
                    d['Title'] = d.pop(colNames[i])
                else:
                    d[fieldsInternal[i]] = d.pop(colNames[i])

        #space notation: _x0020_
        #iterate through items in db
        dupeCount = 0
        newCount = 0
        for item in enumItems:

            #if this is a newlist, we add all the items to the SP list
            if newList:

                #change empty db entry to empty sp entry
                for k in item:
                    if item[k] == None:
                        item[k] = ''
                
                #remove in_SP_list entry since it isn't in SP list
                item.pop('in_SP_list')

                if listName == 'Aging Error Log' and len(str(item['DQ'])) >= 250:
                    item['DQ'] = item['DQ'][0:250]

                #upload entry
                newCount += 1
                add_item_to_SP_list(session=session, listName=listName, items=[item], kind='New')

            #if item is marked as not being in SP, we do another check to see if it is a duplicate entry
            elif item['in_SP_list'] == None or int(item['in_SP_list']) == 0:

                #change empty db entry to empty sp entry
                for k in item:
                    if item[k] == None:
                        item[k] = ''
                
                #query the SP list to see if this is a dupe item by checking the Serial Number (SN) and Log ID
                query = {}
                fields = []
                if listName == 'Aging Error Log':
                    query={'Where': ['And', ('Eq', 'SN', item['SN']), ('Eq', 'Log ID', item['Log_x0020_ID'])]}
                    fields = ['SN', 'Log ID']
                    if '' in [item['SN'], item['Log_x0020_ID']]:
                        continue
                elif listName in  ['Completed Aging D1y', 'Completed Aging D1z','Completed Aging D1x']:
                    if item['Batch'] == '':
                        continue
                    query = {'Where': [('Eq', 'Batch', item['Batch'])]}
                    fields = ['Batch']


                #if query is a match, then entry is already in SP, so we continue
                response = query_SP_list_items(session=session, listName=listName, fields=fields,query=query, cols=colNames, fieldsInternal=fieldsInternal)
                if response:
                    dupeCount += 1
                    #print('dupe: ' + str(response))
                    continue

                #otherwise, we add the entry to SP
                else:  
                    newCount += 1
                    print('new item in SP! uploading...')
                    print('query: ' + str(query))
                    item.pop('in_SP_list')
                    add_item_to_SP_list(session=session, listName=listName, items=[item], kind='New')
            else:
                dupeCount += 1
                continue

        #update all the in_SP_list entries in the db to true
        print('# of dupes: ' + str(dupeCount))
        print('# of new entries: ' + str(newCount))
        cur.execute("UPDATE \"" + listName +"\" SET in_SP_list = 1 WHERE in_SP_list isNull or in_SP_list = 0")
        con.commit()
    


if __name__ == '__main__':
    db2SPlist()