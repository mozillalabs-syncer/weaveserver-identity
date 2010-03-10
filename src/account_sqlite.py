#
# This is a simple implementation of the Weave user API,
# using a SQLite database representation.
#
import account
import traceback
import logging
import time
import json
import hashlib
import sqlite3
import sys

if __name__ == "__main__":
  dbName = "id_user_unittest.db"
  import os
  try:
    os.unlink(dbName)
  except:
    pass
else:
  dbName = "id_user.db"

CONN = sqlite3.connect(dbName)


# Global setup: make sure the tables we need are in the database
try:
  c = CONN.cursor()
  try:
    # TODO we could describe the table and make sure it looks right
    c.execute("select * from users")
  except:
    try:
      # We depend on the magical sqlite "rowid" table.
      c.execute("""create table users \
              (username VARCHAR(32), \
              md5 VARBINARY(32), \
              email VARBINARY(64), \
              status TINYINT(4) default '1',\
              alert TEXT,\
              reset VARBINARY(32) default null)""")
    except Exception, e:
      raise account.WeaveUserException("Fatal error: Unable to create table 'users': %s" % e)
  c.close()
except account.WeaveUserException, e:
  print e
  sys.exit(1)



def nameIsAvailable(name):
  c = CONN.cursor()
  try:
    c.execute('select count(*) from users where username = ?', (name,))
    res = c.fetchone()
    c.close()
    
    if res[0] == 1:
      return False
    return True
  except Exception,e:
    traceback.print_exc(e)
    print e
    c.close()
    return True
    
def create(name, password, email):
  if name is None or len(name) == 0:
    raise account.WeaveUserException("Invalid username")
  if password is None or len(password) == 0:
    raise account.WeaveUserException("Invalid password")

  c = CONN.cursor()
  try:
    md5 = hashlib.md5(password).hexdigest()
    c.execute("insert into users (username, md5, email, status) values (?, ?, ?, 1)", (name, md5, email))
    c.close()
  except Exception, e:
    traceback.print_exc(e)
    print e
    c.close()
    raise account.WeaveUserException("Unable to create user")

def delete(name):
  if name is None or len(name) == 0:
    raise account.WeaveUserException("Invalid username")
  c = CONN.cursor()
  try:
    c.execute("delete from users where username = ?", (name,))
    c.close()
  except:
    c.close()
    raise account.WeaveUserException("Unable to delete user")

def checkPassword(name, password):
  if name is None or len(name) == 0:
    raise account.WeaveUserException("Invalid username")
  if password is None or len(password) == 0:
    raise account.WeaveUserException("Invalid password")

  c = CONN.cursor()
  try:
    md5 = hashlib.md5(password).hexdigest()	
    c.execute("select status from users where username = ? and md5 = ?", (name, md5))
    res = c.fetchone()
    if res:
      if res[0] != 1:
        return False
      return True
    else:
      return False
  except:
    c.close()
    return False

def getStorageNode(name):
  return None
    
def setPassword(name, password):
  if name is None or len(name) == 0:
    raise account.WeaveUserException("Invalid username")
  if password is None or len(password) == 0:
    raise account.WeaveUserException("Invalid password")

  c = CONN.cursor()
  try:
    md5 = hashlib.md5(password).hexdigest()
    c.execute("update users set md5 = ? where username =?", (md5, name))
    c.close()
  except:
    c.close()
    raise account.WeaveUserException("Unable to change password")


def setEmail(name, email):
  if name is None or len(name) == 0:
    raise account.WeaveUserException("Invalid username")
  if email is None or len(email) == 0:
    raise account.WeaveUserException("Invalid email")

  c = CONN.cursor()
  try:
    c.execute("update users set email = ? where username =?", (email, name))
    c.close()
  except:
    c.close()
    raise account.WeaveUserException("Unable to change email")

