import logging

ACCOUNTS = {}

def get(username, password):
  return storage.get(username, "profile", "root")
	

class WeaveException(Exception):
  def __init__(self, message):
    self.message = message
  def __repr__(self):
    return "<WeaveException %s>" % self.message
  def __str__(self):
    return self.message

def nameIsAvailable(name):
  return not name in ACCOUNTS

def create(name, password, email):
  if name in ACCOUNTS:
    raise WeaveError("Account '%s' already exists." % name)
  ACCOUNTS[name] = {'password':password, 'email':email, 'storage':"http://localhost"}	

def delete(name):
  if name in ACCOUNTS:
    del ACCOUNTS[name]

def checkPassword(name, password):
  if name in ACCOUNTS:
    logging.debug("Checking %s password: %s =? %s" % (name, ACCOUNTS[name]['password'], password))
    return ACCOUNTS[name]['password'] == password
  return False

def getStorageNode(name):
  if name in ACCOUNTS:
    return ACCOUNTS[name]['storage']
  else:
    raise WeaveException("Unknown account")
    
def setPassword(name, password):
  if name in ACCOUNTS:
    logging.debug("Changed %s password to %s" % (name, password))
    ACCOUNTS[name]['password'] = password
  else:
    raise WeaveException("Unknown account")


def setEmail(name, email):
  if name in ACCOUNTS:
    logging.debug("Changed %s email to %s" % (name, email))
    ACCOUNTS[name]['email'] = email
  else:
    raise WeaveException("Unknown account")
