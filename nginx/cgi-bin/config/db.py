import mysql.connector
import time

# Configuration
LOCAL = False
DEBUG = False  # Debug mode: True for debugging, False for production

# MySQL DB data
if LOCAL:
    db_config = {
        "user": "root",
        "password": "aman",
        "host": "localhost"
    }
else:
    db_config = {
        "user": "root",
        "password": "aman",
        "host": "localhost"
    }

# Global variables
dbh = None
last_query = None

# MySQL subroutines

def db_open(dbname):
    global dbh
    if not dbname:
        return 1
    sleepcnt = 0
    try_count = 0
    while try_count < 3:
        try:
            try_count += 1
            dbh = mysql.connector.connect(database=dbname, **db_config)
            cursor = dbh.cursor()
            cursor.execute("SET NAMES utf8;")
            print('SUCCESS:: CONNECT TO MYSQL')
            break
        except mysql.connector.Error as err:
            time.sleep(1)
            sleepcnt += 1
            print(err)
            print('ERROR:: DID NOT CONNECT TO MYSQL')
            if sleepcnt > 120:
                print("DB Access error")
                break
    return dbh

def db_close():
    if dbh:
        dbh.close()

def db_select(query, additional_where=None):
    global last_query
    if additional_where:
        query = modify_query(query, additional_where)
    
    if DEBUG:
        print(query)

    if last_query == query:
        if DEBUG:
            print("Same execution")
        return []

    last_query = query
    cursor = dbh.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    return rows

def db_select_row(query, prefix="", limit=""):
    global last_query
    if prefix != "nowhere":
        query = modify_query(query, prefix)

    if limit:
        query = f"{query} {limit};"

    if DEBUG:
        print(query)

    if last_query == query:
        if DEBUG:
            print("Same execution")
        return []

    last_query = query
    cursor = dbh.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    return rows

def db_prepare_from_form(edit_flag, form_data, table_names):
    dbstrt, dbstrh = "", ""
    for field_name, table_name in zip(form_data.keys(), table_names):
        if table_name != "none":
            if edit_flag:
                dbstrt += f"{table_name}='{form_data[field_name]}',"
            else:
                dbstrh += f"{table_name},"
                dbstrt += f"'{form_data[field_name]}',"
    
    dbstrh = dbstrh.rstrip(',')
    dbstrt = dbstrt.rstrip(',')

    if dbstrh:
        dbstrt = f"( {dbstrh} ) VALUES ( {dbstrt} )"
    return dbstrt

def db_execute(query):
    cursor = dbh.cursor()
    result = cursor.execute(query)
    cursor.close()
    return result

def db_get_lastid():
    cursor = dbh.cursor()
    cursor.execute("SELECT LAST_INSERT_ID()")
    last_id = cursor.fetchone()[0]
    cursor.close()
    return last_id

# Helper function to modify SQL query
def modify_query(query, additional_where):
    query = query.rstrip(';')
    if "where" in query.lower():
        query = f"{query} AND {additional_where};"
    elif "order by" in query.lower():
        query = query.replace("ORDER BY", f"WHERE {additional_where} ORDER BY")
    else:
        query += f" WHERE {additional_where};"
    return query

# Debugging utility
def _print(message, cur=""):
    if DEBUG:
        cur = cur if cur else "debug_cur"
        print(f"<FONT COLOR=red>[Debug][{cur}]</FONT> {message}<BR>\n")

# Example usage:
# dbh = db_open('my_database')
# result = db_select("SELECT * FROM my_table;")
# db_close()
