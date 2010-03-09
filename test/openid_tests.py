#!/usr/bin/python

# Tests that exercise the OpenID Identity Provider features of the server.

import random
import logging
import hmac
import urllib2
import httplib
import hashlib
import unittest
import urlparse
from base64 import b64encode, b64decode
import test_config

httplib.HTTPConnection.debuglevel = 1

from BeautifulSoup import BeautifulSoup
import cookielib

import weave
import test_config

SERVER_BASE = test_config.SERVER_BASE
# = "https://auth.services.mozilla.com"

IDENTIFIER_PREFIX = test_config.OPENID_IDENTIFIER_PREFIX
# "https://services.mozilla.com/openid/"

# Convenience opener...
class SmartRedirectHandler(urllib2.HTTPRedirectHandler):
	handler_order = 999
	def http_error_301(self, req, fp, code, msg, headers):
		self.status = code
		self.headers = headers
		return self

	def http_error_302(self, req, fp, code, msg, headers):   
		self.status = code
		self.headers = headers
		return self

cj = cookielib.LWPCookieJar()
opener = urllib2.build_opener(SmartRedirectHandler, urllib2.HTTPCookieProcessor(cj))

class TestAuthentication(unittest.TestCase):

	def setUp(self):
		email = 'testuser@test.com'
#		self.password = 'mypassword'
#		self.userID = 'weaveunittest_' + ''.join([chr(random.randint(ord('a'), ord('z'))) for i in xrange(10)])
#		self.failUnless(weave.checkNameAvailable(SERVER_BASE, self.userID))
#		weave.createUser(SERVER_BASE, self.userID, self.password, email)
#		self.failIf(weave.checkNameAvailable(SERVER_BASE, self.userID))

		self.userID = "michaelrhanson"
		self.password = "ma$tic8"
		self.id = "%s%s" % (IDENTIFIER_PREFIX, self.userID)
		
	def test11Discovery(self):
		# No XRDS or Yadis support.  HTML-based discovery only.
		req = urllib2.Request(self.id)
		f = opener.open(req)
		result = f.read()
		soup = BeautifulSoup(result)
		
		# The OpenID 1.1 spec strongly suggests that the LINK element MUST be a child
		# of the HTML/HEAD element.  Here, we require that:
		linkList = soup.html.head.findAll('link', rel='openid.server')
		self.failIf(linkList is None or len(linkList) == 0, "Should have an openid.server LINK in the OpenID endpoint HTML")
		self.failIf(len(linkList) > 1, "Should have only one openid.server LINK in the OpenID endpoint HTML")

		link = linkList[0]
		href = link['href']
		self.assert_(href) # not null
		
		# I used to assertEqual(href, IDENTIFIER_PREFIX) but that's not right -
		# the server could use a different prefix than the identifier.

	def get11Endpoint(self):
		'Same as test11Discovery but not instrumented; used by other tests'
		req = urllib2.Request(self.id)
		f = opener.open(req)
		result = f.read()
		soup = BeautifulSoup(result)
		linkList = soup.html.head.findAll('link', rel='openid.server')
		return linkList[0]['href']


	def skiptest20Discovery(self):
		# No XRDS or Yadis support.  HTML-based discovery only.
		req = urllib2.Request(self.id)
		f = opener.open(req)
		result = f.read()
		soup = BeautifulSoup(result)
		
		# 7.3.3 A LINK element MUST be included with attributes "rel" set to "openid2.provider" and "href" set to an OP Endpoint URL
		linkList = soup.html.head.findAll('link', rel='openid2.provider')
		self.failIf(linkList is None or len(linkList) == 0, "Should have an openid2.provider LINK in the OpenID endpoint HTML")
		self.failIf(len(linkList) > 1, "Should have only one openid2.provider LINK in the OpenID endpoint HTML")

		# A LINK element MAY be included with attributes "rel" set to "openid2.local_id" and "href" set to the end user's OP-Local Identifier


	def test11CheckImmediate_DumbMode_ImmedateFailure(self):
		op = self.get11Endpoint()
		logging.debug("%s?openid.mode=checkid_immediate&openid.identity=%s&openid.return_to=http://return.to.me/" % (op, self.id))		
		req = urllib2.Request("%s?openid.mode=checkid_immediate&openid.identity=%s&openid.return_to=http://return.to.me/here" % (op, self.id))		
		f = opener.open(req)

		# Response should be a 302 back to return.to.me
		# Response is formatted as a query string
		self.failUnlessEqual(302, f.status)
		self.failUnless('Location' in f.headers)

		l = f.headers['Location']
		url = urlparse.urlparse(l.strip())
		responseParams = urlparse.parse_qs(url.query, strict_parsing=True)
		self.failUnlessEqual(url.scheme, "http")
		self.failUnlessEqual(url.netloc, "return.to.me")
		self.failUnlessEqual(url.path, "/here")

		# check_immediate without an association handle in the input should return:
		# a user_setup_url
		self.failUnlessEqual(responseParams['openid.mode'], ["id_res"])
		self.failUnless('openid.user_setup_url' in responseParams)
		
		# The contents of user_setup_url are idiosyncratic to the implementation.
		# But we can be pretty sure that it should be the openID server, and that the mode should be checkid_setup
		setupURL = urlparse.urlparse(responseParams['openid.user_setup_url'][0])
		setupParams = urlparse.parse_qs(setupURL.query, strict_parsing=True)
		self.failUnlessEqual(op, "%s://%s%s" % (setupURL.scheme, setupURL.netloc, setupURL.path))
		self.failUnlessEqual(setupParams['openid.mode'], ["checkid_setup"])
		self.failUnlessEqual(setupParams['openid.return_to'], ["http://return.to.me/here"])
		self.failUnlessEqual(setupParams['openid.trust_root'], ["http://return.to.me/here"])
	

	def test11CheckImmediate_DumbMode_ImmediateOK(self):
		cj = cookielib.LWPCookieJar()
		opener = urllib2.build_opener(SmartRedirectHandler, urllib2.HTTPCookieProcessor(cj))
		op = self.get11Endpoint()
		
		# For immediate to succeed we have to have a session already established.
		# This is entirely implementation-specific.
		req = urllib2.Request(SERVER_BASE + "/loginsubmit?success_to=/&fail_to=/&user=" + self.userID + "&submit=Log+In")
		logging.debug(req.get_full_url())

		f = opener.open(req)
		for index, cookie in enumerate(cj):
			logging.debug("%d %s" % (index, cookie))
		l = f.headers['Location']
		logging.debug(l)
		logging.debug(f.headers['Set-Cookie'])
	
		logging.debug("%s?openid.mode=checkid_immediate&openid.identity=%s&openid.return_to=http://return.to.me/" % (op, self.id))		
		req = urllib2.Request("%s?openid.mode=checkid_immediate&openid.identity=%s&openid.return_to=http://return.to.me/here" % (op, self.id))		
		f = opener.open(req)
		for index, cookie in enumerate(cj):
			logging.debug("%d %s" % (index, cookie))

		# Response should be a 302 back to return.to.me
		# Response is formatted as a query string
		self.failUnlessEqual(302, f.status)
		self.failUnless('Location' in f.headers)

		l = f.headers['Location']
		logging.debug(l)
		url = urlparse.urlparse(l.strip())
		responseParams = urlparse.parse_qs(url.query, strict_parsing=True)
		self.failUnlessEqual(url.scheme, "http")
		self.failUnlessEqual(url.netloc, "return.to.me")
		self.failUnlessEqual(url.path, "/here")

		# check_immediate without an association handle in the input should return:
		# user_setup_url
		# mode = id_res, identity=identifier, assoc_handle=<handle>, return_to=<verbatim copy>, signed=list, sig=base64(hmac(secret(assoc_handle), token_contents), 
		
		logging.debug(responseParams)
		self.failUnlessEqual(responseParams['openid.mode'], ["id_res"])
		self.failUnless('openid.assoc_handle' in responseParams, "Technically optional but this test suite requires it")
		self.failUnless('openid.signed' in responseParams)
		signed = responseParams['openid.signed'][0]
		signedList = signed.split(',')
		self.failUnless('mode' in signedList)
		self.failUnless('assoc_handle' in signedList)
		self.failUnless('signed' in signedList)
		# python-openid returns user_setup_url here (and signs it)
		self.failUnless('claimed_id' in responseParams) # 2.0?
		
		
		

	def test11CheckIDSetup_DumbMode(self):
		op = self.get11Endpoint()
		req = urllib2.Request("%s?openid.mode=checkid_setup&openid.identity=%s&openid.return_to=http://return.to.me/" % (op, self.id))		
		f = opener.open(req)
		result = f.read()
		
		# Response is formatted as a query string
		q = urlparse.parse_qs(result, strict_parsing=True)

		self.failUnless("openid.mode" in q)

	def test11AuthorizeSite(self):
		# This is a proprietary Weave method.  Note the different parameter names.
		op = self.get11Endpoint()

		req = urllib2.Request("%s?openid_mode=authorize_site&openid_identity=%s&openid_return_to=https://return.to.me/where&weave_pwd=%s" % 
				(op, self.userID, self.password))		

		f = opener.open(req)
		result = f.read()
		
		# Response is a URL
		url = urlparse.urlparse(result.strip())
		q = urlparse.parse_qs(url.query, strict_parsing=True)
		self.failUnlessEqual(url.scheme, "https")
		self.failUnlessEqual(url.netloc, "return.to.me")
		self.failUnlessEqual(url.path, "/where")

		self.failUnless("openid.mode" in q)
		self.failUnlessEqual(len(q["openid.mode"]), 1)
		self.failUnlessEqual(q["openid.mode"][0], "id_res")

		self.failUnless("openid.identity" in q)
		self.failUnlessEqual(len(q["openid.identity"]), 1)
		self.failUnlessEqual(q["openid.identity"][0], self.id)

		self.failUnless("openid.assoc_handle" in q)
		self.failUnlessEqual(len(q["openid.assoc_handle"]), 1)
		# and it's a big long string

		self.failUnless("openid.sig" in q)
		self.failUnlessEqual(len(q["openid.sig"]), 1)
		# and it's a big long string

		self.failUnless("openid.return_to" in q)
		self.failUnlessEqual(len(q["openid.return_to"]), 1)
		self.failUnlessEqual(q["openid.return_to"][0], "https://return.to.me/where")
		
		self.failUnless("openid.signed" in q)
		self.failUnlessEqual(len(q["openid.signed"]), 1)
		self.failUnlessEqual(q["openid.signed"][0], "mode,identity,assoc_handle,return_to")


	def test11AuthorizeSite_BadTrustRoot(self):
		# This is a proprietary Weave method.  Note the different parameter names.
		op = self.get11Endpoint()

		try:
			root = "https://different.root"
			url = "%s?openid_mode=authorize_site&openid_identity=%s&openid_return_to=https://return.to.me/where&weave_pwd=%s&openid_trust_root=%s" % (op, self.userID, self.password, root)
			f = urllib2.urlopen(url)
			result = f.read()

			self.fail("Should have thrown an error with an invalid trust root")
		except urllib2.HTTPError, e:
			pass
		
				
	def testAuthorizeSiteWithAssociation_Plaintext(self):
		# Establish an association
		op = self.get11Endpoint()
		payload = "openid.mode=associate&openid.assoc_type=HMAC-SHA1&openid.session_type="
		f = opener.open(urllib2.Request(op, data=payload))
		result = f.read()

		q = self.parseKeyValueEncoding(result)
		self.failIf('session_type' in q)
		self.failUnlessEqual(q['assoc_type'], "HMAC-SHA1")
		self.failUnlessEqual(int(q['expires_in']), test_config.EXPECTED_OPENID_EXPIRATION)
		assocHandle = q['assoc_handle']
		mac_key_b64 = q['mac_key']
		mac_key = b64decode(mac_key_b64)
		
		# Now authenticate
		req = urllib2.Request("%s?openid_mode=authorize_site&openid_identity=%s&openid_return_to=https://return.to.me/where&weave_pwd=%s&openid_assoc_handle=%s" % 
				(op, self.userID, self.password, assocHandle))		

		f = opener.open(req)
		result = f.read()
		url = urlparse.urlparse(result.strip())
		q = urlparse.parse_qs(url.query, strict_parsing=True)
	
		self.failUnlessEqual(q["openid.mode"][0], "id_res")
		self.failUnlessEqual(q["openid.assoc_handle"][0], assocHandle)
	
		# Verify the signature
		signedBytes = ""
		for key in q["openid.signed"][0].split(','):
			signedBytes += "%s:%s\n" % (key, q["openid." + key][0])
		
		hmacval = hmac.new(key=mac_key, msg=signedBytes, digestmod=hashlib.sha1).digest()
		expectedSig = b64encode(hmacval)
		self.failUnlessEqual(expectedSig, q["openid.sig"][0])



	def testAuthorizeSiteWithExpiredAssociation(self):
		# We'll just lie about the assocation; the server can't tell the difference.
		# We should get back a new association handle.
		op = self.get11Endpoint()
		return_to = "https://return.to.me/where"
		req = urllib2.Request("%s?openid_mode=authorize_site&openid_identity=%s&openid_return_to=%s&weave_pwd=%s&openid_assoc_handle=%s" % 
				(op, self.userID, return_to, self.password, "not-a-real-assoc-handle"))		

		f = opener.open(req)
		result = f.read()
		logging.debug(result)	
		url = urlparse.urlparse(result.strip())
		q = urlparse.parse_qs(url.query, strict_parsing=True)
		logging.debug(q)
	
		self.failUnlessEqual(q["openid.mode"][0], "id_res")
		self.failUnless("openid.invalidate_handle" in q)
		self.failUnless("openid.assoc_handle" in q)
		assocHandle = q["openid.assoc_handle"][0]
		self.failUnlessEqual(q["openid.invalidate_handle"][0], "not-a-real-assoc-handle")
		invalidateHandle = q["openid.invalidate_handle"][0]

		# and now we can go verify that signature.
		logging.debug("%s?openid_mode=check_authentication&openid_identity=%s&openid_assoc_handle=%s&openid_signed=%s&openid_sig=%s&openid_return_to=%s&openid_invalidate_handle=%s" % 
				(op, self.userID, assocHandle, q["openid.signed"][0], q["openid.sig"][0], return_to, invalidateHandle))

		req = urllib2.Request("%s?openid_mode=check_authentication&openid_identity=%s&openid_assoc_handle=%s&openid_signed=%s&openid_sig=%s&openid_return_to=%s&openid_invalidate_handle=%s" % 
				(op, self.userID, assocHandle, q["openid.signed"][0], q["openid.sig"][0], return_to, invalidateHandle))
		f = opener.open(req)
		result = f.read()
		
		logging.debug(result)
		q = self.parseKeyValueEncoding(result)
		self.failUnlessEqual(q['openid.mode'], "id_res")

		#self.failUnlessEqual(q['openid.is_valid'], "true")
		self.failUnlessEqual(q['is_valid'], "true") # note no openid prefix


	def skiptestAuthenticationWithAssociation_DH(self):
		op = self.get11Endpoint()
		req = urllib2.Request("%s?openid.mode=associate&openid.assoc_type=HMAC-SHA1&openid.session_type=DH-SHA1&openid.dh_modulus=%s&openid.dh_gen=%s&openid.dh_consumer_public=%s" % 
				(op, self.userID, self.password))		
		f = opener.open(req)
		result = f.read()




	# 2.0 tests follow.........
		
	def test11CompatibilityAuthentication(self):
		pass
	
	def testBadRequestContentType(self):
		# 4.1.2 if the "Content-Type" header is included in the request headers, its value MUST also be such an encoding. 
		pass
	
	def testBadUnicodeEncoding(self):
		# 4.1 When the keys and values need to be converted to/from bytes, they MUST be encoded using UTF-8.
		pass

	def testBadKeyPrefix(self):
		# 4.1.2 All of the keys in the request message MUST be prefixed with "openid.".
		pass
	
	def testParameterInGetWithPost(self):
	 # 4.1.2 When a message is sent as a POST, OpenID parameters MUST only be sent in, and extracted from, the POST body. 
	 pass
	
	def testMissingNS(self):
		# 4.1.2 All messages MUST contain an 'openid.ns' field
		pass
	
	def testMissingMode(self):
		# 4.1.2 All messages MUST contain an 'openid.mode' field
		pass

	def testUnknownNS(self):
		# If we don't recognize the namespace we should... ?
		pass


	# TODO Need to test expired association somehow.

	# Can we test btwoc?  How about the zero-padding?


	# Helper methods
	def parseKeyValueEncoding(self, s):
		res = {}
		q = s.strip().split('\n')
		for l in q:
			p = l.split(':', 2)
			res[p[0]] = p[1]
		return res
