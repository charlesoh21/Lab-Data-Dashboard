import sqlite3
import SPlist

#change workdir to where you keep your .db, .cfg, etc files
workdir = 'C:\\Users\\riley.w\\Documents\\SQLTest'

def db2dict(cur, row) -> dict:
    '''Row factory for sqlite3 connection. 
    Converts rows in database into a single dict.'''
    dict = {}
    for idx, col in enumerate(cur.description):
        dict[col[0]] = row[idx]
    return dict

def db2SPlist() -> None:
    '''converts local database entries to online Sharepoint list entries.'''

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
        print()
        curList = SPlist.SPlist(listName)
        cur.execute("SELECT * FROM \"" + listName + "\"")
        colNames = list(map(lambda x: x[0], cur.description))
        enumItems = cur.fetchall()

        #try to make a new list. If we succeed, set newList to true, else false.

        #if this is a newlist, initialize the column names.
        print('listName: ' + str(listName))
        print('newList: ' + str(curList.newList))
        if curList.newList:
            #rename default 'title' column to the first column in our db table
            curList.update_field_name(fieldNameOld='Title', fieldNameNew=colNames[0])

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
            r = curList.get_list()
            curList.no_require_field(colNames[0])

        #iterate through items in db and change their column names to internal sharepoint names
        for d in enumItems:
            for val in colNames:
                if val == 'in_SP_list':
                    continue
                elif val == 'Customer' or val== 'Server No':
                    d["Title"] = d.pop(val)
                else:
                    d[curList.fields[val]['name']] = d.pop(val)

        #iterate through items in DB table
        dupeCount = 0
        newCount = 0
        for item in enumItems:

            #if this is a newlist, we add all the items to the SP list
            if curList.newList:

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
                response = curList.add_item_to_SP_list([item])
                test = 1

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
                response = curList.query_SP_list_items(fields=fields,query=query)
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
                    curList.add_item_to_SP_list([item])
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