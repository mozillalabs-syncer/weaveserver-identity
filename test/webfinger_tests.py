#!/usr/bin/python

import urllib
import httplib
import hashlib
import unittest
from base64 import b64encode

import random
import weave
import webfinger

SERVER_BASE = "https://pm-weave06.mozilla.org"

OPENID_10_IDP_REL = "http://openid"
HCARD_PROFILE_REL = "http://profile"
OPENSOCIAL_REL = "http://opensocial"

class TestWebfinger(unittest.TestCase):

	def setUp(self):
		self.personBase = 'weaveunittest_' + ''.join([chr(random.randint(ord('a'), ord('z'))) for i in xrange(10)])

	def testAccountManagement(self):
		email = 'testuser@test.com'
		password = 'mypassword'
		userID = self.personBase

		self.failUnless(weave.checkNameAvailable(SERVER_BASE, userID))
		weave.createUser(SERVER_BASE, userID, password, email)

		webfingerUser = webfinger.resolveUser("testuser@test.com", atSite = SERVER_BASE)
		self.failUnless(webfingerUser != None)
		
		# By default, the webfinger should advertise an IdP and an HCard
		self.failUnless(webfingerUser.getLinks() != None)
		links = webfingerUser.getLinks()

		self.failUnless(OPENID_10_IDP_REL in links)
		self.failUnless(HCARD_PROFILE_REL in links)
		self.failUnless(OPENSOCIAL_REL in links)
		
		# Now we should be able to add a new service
		# and it should be advertised
		
		# Another for the same rel and we should get more than one
		
		# Change one of them and it works
		
		# Remove one

		# and the other
		