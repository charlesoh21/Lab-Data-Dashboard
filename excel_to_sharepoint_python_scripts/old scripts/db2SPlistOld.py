from shareplum import Site
from requests_ntlm import HttpNtlmAuth
import sqlite3
import configparser
import os

from shareplum.site import Version

#change workdir to where you keep your .db, .cfg, etc files
workdir = 'C:\\Users\\riley.w\\Documents\\SQLTest'

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
    #get settings from cfg file and put them in appropriate variables
    settings = cfgLoad()
    urlSP = settings.get('SETTINGS', 'urlSP')

    #get login info and establish connection to sharepoint
    auth = HttpNtlmAuth(settings.get('USERS', 'username'), settings.get('USERS', 'password'))
    site = Site(urlSP, verify_ssl=False, version=Version.v365, auth=auth)

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
        try:
            print(listName)
            site.AddList(list_name=listName,description='This is a List. Crazy.', template_id="Custom List")
            newList = True
        except:
            newList = False

        #setup connection to sharepoint list
        curList = site.List(listName)

        #if this is a newlist, initialize the column names.
        print('listName: ' + str(listName))
        print('newList: ' + str(newList))
        if newList:
            #rename default 'title' column to the first column in our db table
            curList.update_field_name(field='Title', new=colNames[0])

            #iterate through db cols
            for i in colNames:

                #inSPlist is a db entry used to determine whether an entry is already in SP. Thus, we skip adding a column for it to the SP list.
                if i == colNames[0] or i == "in_SP_list":
                    continue
                else:
                    #create the column and make it visible in our default view in sharepoint
                    curList.create_field(i)
                    curList.make_field_visible(i)
            
            #re-establish connection to list so that we get updated info, and make the default column not required
            curList = site.List(listName)
            curList.no_require_field(field=colNames[0])

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
                curList.update_list_items([item], kind='New')

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
                    query={'Where': ['And', ('Eq', 'SN', item['SN']), ('Eq', 'Log ID', item['Log ID'])]}
                    fields = ['SN', 'Log ID']
                    if '' in [item['SN'], item['Log ID']]:
                        continue
                elif listName in  ['Completed Aging D1y', 'Completed Aging D1z','Completed Aging D1x']:
                    if item['Batch'] == '':
                        continue
                    query = {'Where': [('Eq', 'Batch', item['Batch'])]}
                    fields = ['Batch']


                #if query is a match, then entry is already in SP, so we continue
                response = curList.GetListItems(fields=fields,query=query)
                if response :
                    dupeCount += 1
                    #print('dupe: ' + str(response))
                    continue

                #otherwise, we add the entry to SP
                else:  
                    newCount += 1
                    print('new item in SP! uploading...')
                    print('query: ' + str(query))
                    item.pop('in_SP_list')
                    curList.update_list_items([item], kind='New')
            else:
                continue

        #update all the in_SP_list entries in the db to true
        print('# of dupes: ' + str(dupeCount))
        print('# of new entries: ' + str(newCount))
        cur.execute("UPDATE \"" + listName +"\" SET in_SP_list = 1 WHERE in_SP_list isNull or in_SP_list = 0")
        con.commit()
    


if __name__ == '__main__':
    db2SPlist()