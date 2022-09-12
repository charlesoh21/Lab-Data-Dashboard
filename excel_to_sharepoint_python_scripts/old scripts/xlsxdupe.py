import pandas as pd
import pymysql
import sqlite3
import os
import time

def main():
    ds = pd.read_excel("5.16_Aging_Status.xlsx", sheet_name = "Aging Error Log")
    ds = ds.dropna(how='all')
    ds = ds.replace('\n', ' - ', regex=True)
    ds = ds.fillna(method='ffill')
    #print(ds)
    return
    con = sqlite3.connect("test.db")
    cur = con.cursor()
    myDB = ds.to_sql(con=con, name='testDB', index=False)
    con.commit()

if __name__ == '__main__':
    T1 = time.time()
    if not os.path.isfile('test.db'):
        main()
    con = sqlite3.connect("test.db")
    cur = con.cursor()
    cur.execute("SELECT * FROM testDB WHERE rowid in (1, 880, 881, 960)")
    names = list(map(lambda x: x[0], cur.description))
    #print(names)
    for line in cur.fetchall():
        #print(line)
    T2 = time.time()
    print("time elapsed: " + str(T2 - T1 * 1000) + " seconds!")
    #Git push test