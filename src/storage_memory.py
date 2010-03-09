#
# This is a trivial implementation of the Weave storage API,
# using an in-memory representation.
#

import logging
import time
import json

STORAGE = {}

class WeaveStorageException(Exception):
	def __init__(self, message):
		self.message = message
	
	def __repr__(self):
		return "<WeaveStorageException %s>" % self.message

class WBO(object):
	def __init__(self, data):
		self.parentid = None
		self.predecessorid = None
		self.sortindex = None

		self.payload = data['payload']
		self.update(data)

	def update(self, fromMap):
		self.modified = time.time()
		if 'parentid' in fromMap:
			self.parentid = fromMap['parentid']
		if 'predecessorid' in fromMap:
			self.predecessorid = fromMap['predecessorid']
		if 'sortindex' in fromMap:
			self.sortindex = fromMap['sortindex']

class UserStorage(object):
	def __init__(self, name):
		self.name = name
		self.collections = {}
		
	def put(self, collection, payload):
		obj = json.loads(payload)

		# Validate the WBO
		if not 'id' in obj:
			raise WeaveStorageException("WBO missing required 'id' attribute")

		# Find or create the collection
		if collection in self.collections:
			collMap = self.collections[collection]
		else:
			collMap = {}
			self.collections[collection] = collMap

		if not 'payload' in obj:
			# metadata update
			wbo = collMap[obj['id']]
			if wbo:
				wbo.update(obj)
			else:
				# missing object??
				raise WeaveStorageException("WBO update requested for non-existent object")
		else:
			wbo = WBO(obj)
			collMap[obj['id']] = wbo
		return wbo.modified
	
	def collectionCounts(self):
		ret = {}
		for i in self.collections.items():
			ret[i[0]] = len(i[1])
		return ret

def handle_put(name, collection, payload):
	'''Returns the timestamp of the change'''
	try:
		if not name in STORAGE:
			s = UserStorage(name)
			STORAGE[name] = s
		else:
			s = STORAGE[name]
		return s.put(collection, payload)
	except Exception, e:
		raise WeaveStorageException(e)
		
def getCollectionCounts(name):
	if name in STORAGE:
		return STORAGE[name].collectionCounts()
	return None