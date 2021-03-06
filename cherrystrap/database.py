from __future__ import with_statement

import os
import sqlite3
import MySQLdb
import cherrypy
import threading
import time

import cherrystrap

from cherrystrap import logger

db_lock = threading.Lock()

def dbFilename(filename="sqlite.db"):

    return os.path.join(cherrystrap.DATADIR, filename)


# class DBConnection:

#     def __init__(self, filename="sqlite.db"):
#         self.filename = filename
#         self.connection = sqlite3.connect(dbFilename(filename), 20)
#         self.connection.row_factory = sqlite3.Row

#     def action(self, query, args=None):
#         with db_lock:

#             if query == None:
#                 return

#             sqlResult = None
#             attempt = 0

#             while attempt < 5:

#                 try:
#                     if args == None:
#                         #logger.debug(self.filename+": "+query)
#                         sqlResult = self.connection.execute(query)
#                     else:
#                         #logger.debug(self.filename+": "+query+" with args "+str(args))
#                         sqlResult = self.connection.execute(query, args)
#                     self.connection.commit()
#                     break

#                 except sqlite3.OperationalError, e:
#                     if "unable to open database file" in e.message or "database is locked" in e.message:
#                         logger.warn('Database Error: %s' % e)
#                         attempt += 1
#                         time.sleep(1)
#                     else:
#                         logger.error('Database error: %s' % e)
#                         raise

#                 except sqlite3.DatabaseError, e:
#                     logger.error('Fatal error executing %s :: %s' % (query, e))
#                     raise

#             return sqlResult

#     def select(self, query, args=None):
#         sqlResults = self.action(query, args).fetchall()

#         if sqlResults == None:
#             return []

#         return sqlResults

#     def upsert(self, tableName, valueDict, keyDict):
#         changesBefore = self.connection.total_changes

#         genParams = lambda myDict : [x + " = ?" for x in myDict.keys()]

#         query = "UPDATE "+tableName+" SET " + ", ".join(genParams(valueDict)) + " WHERE " + " AND ".join(genParams(keyDict))

#         self.action(query, valueDict.values() + keyDict.values())

#         if self.connection.total_changes == changesBefore:
#             query = "INSERT INTO "+tableName+" (" + ", ".join(valueDict.keys() + keyDict.keys()) + ")" + \
#                         " VALUES (" + ", ".join(["?"] * len(valueDict.keys() + keyDict.keys())) + ")"
#             self.action(query, valueDict.values() + keyDict.values())

class DBConnection:

    def __init__(self, filename="sqlite.db"):
        host = cherrystrap.VANILLA_HOST
        port = cherrystrap.VANILLA_PORT
        if port:
            try:
                port = int(cherrystrap.VANILLA_PORT)
            except:
                logger.error("The port number supplied is not an integer")
        else:
            port = 3306
        if not host:
            host = 'localhost'
            
        user = cherrystrap.VANILLA_USER
        passwd = cherrystrap.VANILLA_PASSWORD

        self.connection = MySQLdb.Connection(host=host, port=port, user=user, passwd=passwd, charset='utf8', use_unicode=True)

    def action(self, query, args=None):
        
        with self.connection:
            self.cursor = self.connection.cursor(MySQLdb.cursors.DictCursor)

            if query == None:
                return

            sqlResult = None

            try:
                if args == None:
                    #logger.debug(self.filename+": "+query)
                    self.cursor.execute(query)
                else:
                    #logger.debug(self.filename+": "+query+" with args "+str(args))
                    self.cursor.execute(query,args)
                self.connection.commit()
            except MySQLdb.IntegrityError:
                logger.info("failed to make transaction")

            sqlResult = self.cursor
            return sqlResult

    def select(self, query, args=None):

        sqlResults = self.action(query, args).fetchall()

        if sqlResults == None:
            return []

        return sqlResults

    def upsert(self, tableName, valueDict, keyDict):

        genParams = lambda myDict : [x + " = %s" for x in myDict.keys()]

        entry_query = "SELECT * FROM "+tableName+" WHERE " + " AND ".join(genParams(keyDict))
        entry_count = self.action(entry_query, keyDict.values()).rowcount

        if entry_count != 0:
            query = "UPDATE "+tableName+" SET " + ", ".join(genParams(valueDict)) + " WHERE " + " AND ".join(genParams(keyDict))
            self.action(query, valueDict.values() + keyDict.values())
        else:
            query = "INSERT INTO "+tableName+" (" + ", ".join(valueDict.keys() + keyDict.keys()) + ")" + \
                        " VALUES (" + ", ".join(["%s"] * len(valueDict.keys() + keyDict.keys())) + ")"
            self.action(query, valueDict.values() + keyDict.values())

