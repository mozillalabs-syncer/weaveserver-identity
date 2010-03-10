#!/usr/bin/python
#
# This is a simple implementation of the Weave storage API,
# using a per-user SQLite database representation.
#

import logging
import time
import json
import storage
import sqlite3
import os.path


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST:
            pass
        else: raise


class WeaveSQLitePerUserStorageContext(object):
  def __init__(self, name):
    self.name = name
    
    if len(name) > 3:
      dbDir = "userdbs/%s/%s/%s" % (name[0], name[1], name[2])
    elif len(name) > 2:
      dbDir = "userdbs/%s/%s/_" % (name[0], name[1])
    elif len(name) > 1:
      dbDir = "userdbs/%s/_/_" % (name[0])

    if not os.path.exists(dbDir):
      mkdir_p(dbDir)

    dbName = dbDir + "/" + name
    if os.path.exists(dbName):
      self.conn = sqlite3.connect(dbName)
    else:
      self.conn = sqlite3.connect(dbName)
      self.create()
    
    self.conn.cursor().execute("PRAGMA synchronous=0")

  def create(self):
    # May throw a sqlite exception.
    c = self.conn.cursor()
    # Note that modified is in centiseconds
    c.execute("""create table data \
            (collection TEXT NOT NULL, \
            id VARBINARY(64) NOT NULL default '', \
            parentid VARBINARY(64) default NULL, \
            predecessorid VARBINARY(64) default NULL, \
            sortindex INT(11) default NULL, \
            modified INT(11) default NULL, \
            payload BLOB, \
            payload_size INT(11) default NULL, \
            PRIMARY KEY ('collection','id'))""")
    self.conn.commit()
    c.close()
  
    
class WeavePerUserSQLiteStorage(object):
  """Implements the Weave Storage API using a sqlite database.
  
  >>> storage = WeavePerUserSQLiteStorage()
  >>> ctx = storage.get_context("unit_test")

  Normally you will create an object with an id and a payload, which
  can be a string or a JSON-encodable object.  The return value
  from add_or_modify will be a timestamp.
  
  If an object is passed int as the payload, it will be serialized as JSON
  automatically, and deserialized on the way back out.

  >>> timestamp = storage.add_or_modify(ctx, "collection", {'id':'def','payload':{'a':'1','b':2}})
  >>> type(timestamp)
  <type 'float'>
  >>> wbo = storage.get(ctx, "collection", 'def')
  >>> wbo.payload
  u'{"a": "1", "b": 2}'

  Calls to an object with the same ID replace it.
  >>> ts = storage.add_or_modify(ctx, "collection", {'id':'replaceme','payload':{'a':'1'}})
  >>> ts = storage.add_or_modify(ctx, "collection", {'id':'replaceme','payload':{'a':'2'}})
  >>> wbo = storage.get(ctx, "collection", 'replaceme')
  >>> wbo.payload
  u'{"a": "2"}'

  You can update the metadata by calling again without a payload
  >>> ts = storage.add_or_modify(ctx, "collection", {'id':'updateme','sortindex':5,'payload':{'a':'1'}})
  >>> ts = storage.add_or_modify(ctx, "collection", {'id':'updateme','sortindex':4})
  >>> wbo = storage.get(ctx, "collection", 'updateme')
  >>> wbo.sortindex
  4

  #>>> storage.add_or_modify(ctx, "collection", {'id':'hello'})
  #Traceback (most recent call last):
  #			...
  #WeaveStorageException: Item passed to add_or_modify must have an 'payload' value


  Attempts to create an object without an id or payload will fail.

  >>> storage.add_or_modify(ctx, "collection", {'payload':{'a':'1','b':2}})
  Traceback (most recent call last):
      ...
  WeaveStorageException: Item passed to add_or_modify must have an 'id' value

  """

  def get_context(self, name):
    return WeaveSQLitePerUserStorageContext(name)

  def convertQueryToSQL(self, query):
    """Given a map of parameters, creates a SQL statement fragment encoding the parameters
    as WHERE, LIMIT, and/or OFFSET clauses.  Returns a tuple of (sql fragment, values tuple)"""

    # TODO refactor this to use named arguments.  Input validation
    # should be performed at the web layer.

    statements = []
    values = []
    
    if 'ids' in query:
      statements.append(" and id in (")
      idVals = query['ids'][0].split(',')
      values += split
      statements.append(",".join(["?" for i in idVals]))
      statements.append(")")

    if 'parentid' in query:
      statements.append(" and parentid = ?")
      values.append(query['parentid'][0])
    
    if 'predecessorid' in query:
      statements.append(" and predecessorid = ?")
      values.append(query['predecessorid'][0])

    if 'index_above' in query:
      statements.append(" and sortindex > ?")
      values.append(query['index_above'][0])
      
    if 'index_below' in query:
      statements.append(" and sortindex < ?")
      values.append(query['index_below'][0])
      
    if 'newer' in query:
      statements.append(" and modified > ?")
      values.append(float(query['newer'][0])*100)
      
    if 'older' in query:
      statements.append(" and modified < ?")
      values.append(float(query['older'][0])*100)

    if 'sort' in query:
      s = query['sort'][0]
      if s == "index":
        statements.append(" order by sortindex desc ")
      elif s == "newest":
        statements.append(" order by modified desc ")
      elif s == "oldest":
        statements.append(" order by modified ")
  
    if 'limit' in query:
      statements.append(" limit %d" % int(query['limit'][0]))
      if 'offset' in query:
        statements.append(" offset %d" % int(query['offset'][0]))

    return ("".join(statements), values)




  def get(self, context, collection, id, query=None):
    """Gets an object from the database."""
    
    c = context.conn.cursor()
    if id and type(id) != str and type(id) != unicode:
      id = unicode(id)

    fullObject = (id != None)

    if fullObject:		
      statement = "select * from data where collection=? "
    else:
      statement = "select id from data where collection=? "

    values = [collection]
    if id:
      statement += " and id=?"
      values.append(id)

    if query:
      clauses, valueAdds = self.convertQueryToSQL(query)
      if len(clauses):
        statement += clauses
      if len(valueAdds):
        values += valueAdds
      
    c.execute(statement, values)
    try:
    
      if fullObject:
        result = c.fetchone()
        if result:
          parentid = None
          if result[2]: parentid = unicode(result[2])
          predecessorid = None
          if result[3]: predecessorid = unicode(result[3])
          
          wbo = storage.WBO(id=id, parentid=parentid, predecessorid=predecessorid, sortindex=result[4], payload=result[6], modified=result[5])
          c.close()
          return wbo
        else:
          return None
      else:
        result = c.fetchall()
        c.close()
        return json.dumps([str(r[0]) for r in result])
    except Exception, e: 
      import traceback
      traceback.print_exc(e)
      raise storage.WeaveStorageException("Error while accessing storage: %s" % e, e)

  def collection_modification_date(self, context, collection):
    try:
      c = self.conn.cursor()
      c.execute("select max(modified) from data where collection=?", (collection))
      result = c.fetchone()
      c.close()
      return float(result[0])/100
    except Exception, e:
      import traceback
      traceback.print_exc(e)
      raise storage.WeaveStorageException("Error while accessing storage: %s" % e, e)

  def collection_timestamps(self, context):
    try:
      c = context.conn.cursor()
      c.execute("select collection, max(modified) as timestamp from data group by collection")
      result = c.fetchall()
      c.close()
      retMap = {}
      for r in result:
        retMap[r[0]] = float(r[1])/100
      return retMap
    except Exception, e:
      import traceback
      traceback.print_exc(e)
      raise storage.WeaveStorageException("Error while accessing storage: %s" % e, e)

  def collection_counts(self, context):
    try:
      c = context.conn.cursor()
      c.execute("select collection, count(*) as ct from data group by collection")
      result = c.fetchall()
      c.close()
      retMap = {}
      for r in result:
        retMap[r[0]] = str(r[1]) # making this into a string because that's what the suite says to do.
      return retMap
    except Exception, e:
      import traceback
      traceback.print_exc(e)
      raise storage.WeaveStorageException("Error while accessing storage: %s" % e, e)


  def add_or_modify(self, context, collection, item, id=None, query=None):
    c = context.conn.cursor()
    wbo = storage.WBO(item)
    try:
      if id:
        if wbo.id and id != wbo.id:
          raise storage.WeaveStorageException("ID mismatch: URL must match ID in JSON-encoded object")
      else:
        if not wbo.id:
          raise storage.WeaveStorageException("Item passed to add_or_modify must have an 'id' value")
        else:
          id = wbo.id

      if wbo.payload:
        c.execute("insert or replace into data values(?,?,?,?,?,?,?,?)", (collection, id, wbo.parentid, wbo.predecessorid, wbo.sortindex,
          wbo.modified, wbo.payload, len(wbo.payload)))
      else:
        params, vals = getWBOUpdateStatement(wbo)
        if len(params) != 0:
          # Make sure metadata update has something to do!
          statement = "update data set " + params + " where collection = ? and id = ?"
          vals.append(collection)
          vals.append(wbo.id)
          c.execute(statement, vals)

          c.execute("select * from data where collection=? and id=?", (collection, wbo.id))
          result = c.fetchone()

      context.conn.commit()
    except storage.WeaveStorageException, we:
      c.close()
      raise we
    except Exception, e:
      c.close()
      import traceback
      traceback.print_exc(e)
      raise storage.WeaveStorageException("Error accessing object for add_or_modify: %s" % e, e)
    c.close()
    
    if wbo.modified:
      return float(wbo.modified)/100
    else:
      return float(int(time.time() * 100)) / 100

  def delete(self, context, collection=None, id=None, query=None):
    c = context.conn.cursor()
    try:

      if not collection:
        statement = "delete from data"
        c.execute(statement)
      else:
        statement = "delete from data where collection=? "
        values = [collection]
        if id:
          statement += " and id=?"
          values.append(id)

        if query:
          clauses, valueAdds = self.convertQueryToSQL(query)
          if len(clauses):
            statement += clauses
          if len(valueAdds):
            values += valueAdds

        logging.error(statement)
        logging.error(values)

        c.execute(statement, values)
      c.close()
      context.conn.commit()
    except storage.WeaveStorageException, we:
      c.close()
      raise we
    except sqlite3.OperationalError, sqe:
      c.close()
      raise storage.WeaveStorageException("Operational error while performing delete: Was SQLite3 compiled with support for DELETE_LIMIT?: %s" % sqe, sqe)
    
    except Exception, e:
      c.close()
      import traceback
      traceback.print_exc(e)
      raise storage.WeaveStorageException("Error accessing object for delete: %s" % e, e)


def getWBOUpdateStatement(wbo):
  """Returns a tuple containing the update clause of a SQL statement, and the values
  needed for that statement, to update a WBO.

  e.g. for {'id':'abc', 'parentid': 'def', 'sortindex': 5}, 
    ('parentid = ?,sortindex = ?,modified = ?', ['def', 5, ...])

  """
  updates = []
  params = []
  if wbo.parentid:
    updates.append("parentid = ?")
    params.append(wbo.parentid)
  if wbo.predecessorid:
    updates.append("predecessorid = ?")
    params.append(wbo.predecessorid)
  if wbo.sortindex:
    updates.append("sortindex = ?")
    params.append(wbo.sortindex)
  #Under standard weave semantics, update will not be called if there's no payload. 
  #However, this is included for functional completion
  if wbo.payload:
    updates.append("payload = ?")
    updates.append("payloadSize = ?")
    params.append(wbo.payload)
    params.append(len(wbo.payload))
  
  # Don't modify the timestamp on a weight-only change. It's purely for sorting trees.
  if (wbo.parentid or wbo.payload) and wbo.modified:
    updates.append("modified = ?")
    params.append(wbo.modified)
  
  return (",".join(updates), params)
    



if __name__ == '__main__':
  import doctest
  doctest.testmod()
