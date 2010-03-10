#
# This is an implementation of the Weave storage API that proxies
# everything to services.mozilla.com.
#
import time
import json
import logging

class WeaveStorageException(Exception):
  def __init__(self, value, nestedException=None):
    self.value = value
    self.nested = nestedException
  
  def __repr__(self):
    return "<WeaveStorageException: %s>" % self.value

  def __str__(self):
    return self.value


class WeaveStorage(object):

  def get_context(name):
    pass

  def get(context, collection, id):
    pass

  def add_or_modify(context, collection, item, ifUnmodifiedSince=None):
    pass


class WBO(object):
  # modified is in centiseconds

  def __init__(self, data=None, id=None, parentid=None, predecessorid=None, sortindex=None, payload=None, modified=None):

    if data:
      if type(data) == str or type(data) == unicode:
        data = json.loads(data)
        
      self.id = None
      if 'id' in data:
        id = data['id']
        if not (type(id) == str or type(id) == unicode):
          id = unicode(id)
        if len(id) > 64:
          raise WeaveStorageException("Illegal id value")
        self.id = id

      self.parentid = None
      self.predecessorid = None
      self.sortindex = None
      self.payload = None
      self.modified = None
      
      if 'payload' in data:
        payloadObj = data['payload']
        if type(payloadObj) != str and type(payloadObj) != unicode:
          self.payload = json.dumps(payloadObj)
        else:
          self.payload = payloadObj

      self.update(data, updateModifiedDate='payload' in data)

    else:
      self.id = id
      self.parentid = parentid
      self.predecessorid = predecessorid
      self.sortindex = sortindex
      self.payload = payload
      self.modified = modified
        
  def asjson(self):
    m = {}
    m['id'] = self.id
    if self.parentid: m['parentid'] = self.parentid
    if self.predecessorid: m['predecessorid'] = self.predecessorid
    if self.sortindex: m['sortindex'] = self.sortindex
    if self.payload: m['payload'] = self.payload
    if self.modified: m['modified'] = float(self.modified) / 100
    
    return json.dumps(m)
    
  def __repr__(self):
    return self.asjson()

  def __str__(self):
    return self.asjson()
        
  def update(self, fromMap, updateModifiedDate = False):
  
    # The modification date is only changed if the payload
    # or parentID is changed.  Changes to sortindex and predecessorID do
    # not update the modification date.
  
    if 'parentid' in fromMap:
      if fromMap['parentid'] != None:
        id = str(fromMap['parentid'])
        if len(id) > 64:
          raise WeaveStorageException("Illegal parentid value")
        self.parentid = id
        updateModifiedDate = True

    if 'predecessorid' in fromMap and fromMap['predecessorid'] != None:
      id = str(fromMap['predecessorid'])
      if len(id) > 64:
        raise WeaveStorageException("Illegal predecessorid value")
      self.predecessorid = id

    if 'sortindex' in fromMap:
      val = fromMap['sortindex']
      if type(val) == int:
        if val > 99999999999:
          raise WeaveStorageException("Illegal sortindex value")
        self.sortindex = val
      elif type(val) == str or type(val) == unicode:
        if len(val) > 11:
          raise WeaveStorageException("Illegal sortindex value")
        try:
          self.sortindex = int(val)
        except:
          # Python raises an exception for "5.5", even though it will take "5".
          # See if we can convert through floating point.
          try:
            self.sortindex = int(float(val))
          except:
            raise WeaveStorageException('Illegal sortindex value')

    if updateModifiedDate:
      self.modified = int(time.time() * 100)


