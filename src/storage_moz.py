#
# This is an implementation of the Weave storage API that proxies
# everything to services.mozilla.com.
#

import storage
import logging
import time
import json
import weave

MOZ_SERVICES_BASE = "https://pm-weave06.mozilla.org"

# THIS IS INCOMPLETE AND DOES NOT WORK

class MozServicesStorageContext(object):
	def __init__(self, node, username, password):
		self.username = username
		self.password = password
		self.node = node

class MozServicesStorage(WeaveStorage):

	def get_context(name, password):
		node = getUserStorageNode(MOZ_SERVICES_BASE, name, password)
		if node:
			return MozServicesStorageContext(node, name, password)
		raise IOError("Unable to set up storage context for user")

	def get(context, collection, id):
		return weave.get_item(context.node, context.name, context.password, collection, id)

	def add_or_modify(context, collection, item, ifUnmodifiedSince=None):
		return weave.add_or_modify(context.node, context.name, context.password, collection, item, ifUnmodifiedSince=ifUnmodifiedSince)

