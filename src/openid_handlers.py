#!/usr/bin/env python
#
import tornado.httpserver
import tornado.ioloop
import tornado.web
import base64
import cgi
import server_config
import logging
account = server_config.account

from openid.server import server
from openid.message import Message, OPENID2_NS

# Create the Server object

# Instantiate OpenID consumer store and OpenID consumer.  If you
# were connecting to a database, you would create the database
# connection and instantiate an appropriate store here.
from openid.store.filestore import FileOpenIDStore

# Tornado always passes arguments as lists (which is a good thing).
# The OpenID library expects single values (which is naive).  This
# class makes it work.
class TornadoArgumentDecoder(server.Decoder):
	def decode(self, arguments):
		q = {}
		for key, values in arguments .items():
			q[key] = values[0]
		return server.Decoder.decode(self, q)

store = FileOpenIDStore("openid_data")

SERVER_ENDPOINT = server_config.external_base_url + '/openid'
USER_ID_PATH_PREFIX = "/openid/"
USER_ID_BASE = server_config.external_base_url + USER_ID_PATH_PREFIX + "%s"

OpenIDServer = server.Server(store, SERVER_ENDPOINT)
OpenIDServer.decoder = TornadoArgumentDecoder(OpenIDServer)


def quoteattr(s):
	"""Helper function to escape and quote a value for inclusion in HTML.
	
	>>> quoteattr("a b < > & c d")
	'"a b &lt; &gt; &amp; c d"'
	"""
	if s:
		qs = cgi.escape(s, 1)
		return '"%s"' % (qs,)
	else:
		return '""'



class OpenIDHandler(tornado.web.RequestHandler):

	def getBasicAuth(self):
		auth = self.request.headers.get("Authorization")
		if auth:
			tokens = auth.split(" ")
			if len(tokens) >= 2:
				upstr = base64.decodestring(tokens[1])
				up = upstr.split(":")
				return up
		return None

	def displayResponse(self, response):
		"""Encode an OpenID response and write it out"""
		try:
				webresponse = OpenIDServer.encodeResponse(response)
		except server.EncodingError, why:
				text = why.response.encodeToKVForm()
				self.showErrorPage('<pre>%s</pre>' % cgi.escape(text))
				return

		self.set_status(webresponse.code)
		for header, value in webresponse.headers.iteritems():
				self.set_header(header, value)
		#$self.writeUserHeader()
		#self.end_headers()

		if webresponse.body:
				self.write(webresponse.body)



class OpenIDServerEndpoint(OpenIDHandler):
	def get(self):

		# If self.user is not None, this request has been properly 
		# authenticated by the user whose ID is contained by the attribute.
		
		userpass = self.getBasicAuth()
		self.user = userpass[0] if userpass else None # just trust it 
		logging.error("Got user %s", userpass)

		# We can resolve the user in a couple ways.
		# We could use a cookie, and do a long-running session, which means
		#   we need to ask for the username/pw every now and then.
		# We could use HTTP auth, and shoot back a 401 challenge when
		#   the user arrives at an ID-mediated page without one.

		try:
			request = OpenIDServer.decodeRequest(self.request.arguments)
		except server.ProtocolError, why:
				self.displayResponse(why)
				return

		if request is None:
				# Display text indicating that this is an endpoint.
				self.showAboutPage()
				return

		if request.mode in ["checkid_immediate", "checkid_setup"]:
				self.handleCheckIDRequest(request)
		else:
				response = OpenIDServer.handleRequest(request)
				self.displayResponse(response)


	def handleCheckIDRequest(self, request):
		is_authorized = self.isAuthorized(request.identity, request.trust_root)

		if is_authorized:
				logging.error("Request for %s by %s is authorized" % (request.trust_root, request.identity))
				response = self.approved(request)
				self.displayResponse(response)
		elif request.immediate:
				logging.error("Immediate request for %s by %s is not authorized: answering false" % (request.trust_root, request.identity))
				response = request.answer(False)
				self.displayResponse(response)
		else:
				logging.error("Setup request for %s by %s is not authorized: showing decide page" % (request.trust_root, request.identity))
				# OpenIDServer.lastCheckIDRequest[self.user] = request No no no no!
				self.showDecidePage(request)


	def isAuthorized(self, identity_url, trust_root):
		"""Given an identity and a trust root, return True if that identity has
		already indicated authorization approval for the given trust root."""
		
		if self.user is None:
				return False

		if identity_url != USER_ID_BASE % self.user:
				return False

		key = (identity_url, trust_root)
		logging.error("self.server.approved.get(%s) is %s" % (key, OpenIDServer.approved.get(key)))
		return OpenIDServer.approved.get(key) is not None



	def showAboutPage(self):
		endpoint_url = server_config.external_base_url + 'openidserver'

		def link(url):
				url_attr = quoteattr(url)
				url_text = cgi.escape(url)
				return '<a href=%s><code>%s</code></a>' % (url_attr, url_text)

		def term(url, text):
				return '<dt>%s</dt><dd>%s</dd>' % (link(url), text)

		resources = [
				(server_config.external_base_url, "Mozilla Weave Identity Server"),
				('http://www.openid.net/', 'the official OpenID Web site'),
				]

		resource_markup = ''.join([term(url, text) for url, text in resources])

		self.write("<html><head><title>Mozilla Weave Identity Server</title></head><body><p>This is the Mozilla Weave Identity Server.<p></body></html>")


	def sendAuthenticationChallenge(self):
		self.set_header("WWW-Authenticate", "Basic realm=\"weave\"")
		self.set_status(401)

	
	def showDecidePage(self, request):
		"""The user has been directed to the IdP by another site,
		and will be asked to make an authorization decision.  He may not
		have an active session, so we may not know who he is.  The RP
		may have sent him to us with a different identity than the one
		we think he holds.  We need to deal with all of that.  The RP
		may have sent him with the IDENTIFIER_SELECT identity, which
		means that the user should be allowed to choose one.
		"""
	
		# We need to make sure the openid.identity (request.identity) matches the identity
		# associated with the request.
		# identityFrom = self.request.path[len(USER_ID_PATH_PREFIX):]


		# TODO: We need to persist the permission ask so that we can return to
		# it when the user comes back to the Allow endpoint.  Or... we need
		# to sign the permission ask data and put it into the POST.

		logging.error("Showing decide page")

		if request.idSelect(): # We are being asked to select an ID
		
			if self.user: # we have an identity from our HTTP session
				# this goes to /allow and from there back to the RP
				# do it right here
				raise tornado.http.HTTPError("500", "IDSelect isn't supported yet")
			else: # we don't know who the user is
				logging.error("Reached decide page for ID select but no active user: sending challenge")
				self.sendAuthenticationChallenge()
				return

		elif not self.user:
			logging.error("Reached decide page without a current user: sending challenge")
			self.sendAuthenticationChallenge()
			return

		elif request.identity == self.user:

			self.write("<html><head><title>Mozilla Weave Identity Server: Authorize Site</title></head><body>")
			self.write("""<p>The website at</p><p style='margin-left:64px'><b>%s</b></p>has asked for permission
			to confirm your identity as <b>%s</b>.\n""" % (request.trust_root, request.identity))
			self.write("<form method='POST' action='/openid/allow'>\n")
			self.write("<input type='hidden' name='root' value=" + quoteattr(request.trust_root) + ">\n")
			self.write("<input type='hidden' name='id' value=" + quoteattr(request.identity) + ">\n")
			self.write("<input type='hidden' name='return_to' value=" + quoteattr(request.return_to) + ">\n")
			self.write("<input type='hidden' name='assoc_handle' value=" + quoteattr(request.assoc_handle) + ">\n")
			self.write("<input type='hidden' name='op_endpoint' value=\"" + SERVER_ENDPOINT + "\">\n")
			# TODO: Should we also put the op_endpoint and claimed_id in here?


			self.write("<input type='submit' name='go' value='Yes, allow this site to know who I am'><br>\n")
			self.write("<input type='checkbox' id='remember' value='yes' name='remember'><label for='remember'>allow this site to know on all future visits</label><br>\n")
			self.write("<br>\n")
			self.write("<input type='submit' name='go' value='No, I do not want this site to know who I am'><br>\n")
			self.write("</form>\n")

		else:

			self.write("<html><head><title>Mozilla Weave Identity Server: Authorize Site</title></head><body>")
			self.write("""<p>The website at</p><p style='margin-left:64px'><b>%s</b></p>has asked for permission
			to confirm your identity as <b>%s</b>.  You are currently logged into Weave as <b>%s</b>.""" % (request.trust_root, request.identity, self.user))

			self.write("""<p>Uh oh!  There's no way to tell your browser to change over.  Bummer!</p>""")


class OpenIDAllowEndpoint(OpenIDHandler):
	def approved(self, request, identifier=None):
		response = request.answer(True, identity=identifier)
		#self.addSRegResponse(request, response)
		return response

	def addSRegResponse(self, request, response):
		sreg_req = sreg.SRegRequest.fromOpenIDRequest(request)

		# In a real application, this data would be user-specific,
		# and the user should be asked for permission to release
		# it.
		sreg_data = {
				'nickname':self.user
				}

		sreg_resp = sreg.SRegResponse.extractResponse(sreg_req, sreg_data)
		response.addExtension(sreg_resp)


	def post(self):
	
		# We _must_ be authenticated.
		userpass = self.getBasicAuth()
		self.user = userpass[0] if userpass else None # just trust it 
		if not self.user:
			self.sendAuthenticationChallenge()
			return
	
		# Um.  How do we safely determine which endpoint the user has granted access to?
		# Do we need to sign the trust_root/identity tuple somehow?

		# For now we just pull it out of the request.  This is not right.
		go = self.request.arguments['go'][0]
		root = self.request.arguments['root'][0]
		id = self.request.arguments['id'][0]
		return_to = self.request.arguments['return_to'][0] if 'return_to' in self.request.arguments else None
		assoc_handle = self.request.arguments['assoc_handle'][0] if 'assoc_handle' in self.request.arguments else None
		op_endpoint = self.request.arguments['op_endpoint'][0] if 'op_endpoint' in self.request.arguments else None

		request = server.CheckIDRequest(id, return_to, root, assoc_handle=assoc_handle, op_endpoint=op_endpoint)
		request.message = Message(OPENID2_NS) # XXX version?

		remember = self.request.arguments['remember'][0] == 'yes' if 'remember' in self.request.arguments else False

		if 'Yes, allow this site to know who I am' == go:
			if remember:
				# Persist remember on the user
				# self.server.approved[(identity, trust_root)] = 'always'
				pass
			response = self.approved(request, id)

		elif 'no' in query:
			response = request.answer(False)

		else:
			logging.error('strange allow post.  %r' % (query,))
			raise tornado.web.HTTPError("400", "Strange Allow Post")

		self.displayResponse(response)


class OpenIDUserEndpoint(tornado.web.RequestHandler):
	def get(self, userID):
	
		logging.error(self.request.path)
	
		link_tag = '<link rel="openid.server" href="%s/openid">' %\
					server_config.external_base_url

		yadis_loc_tag = '<meta http-equiv="x-xrds-location" content="%s">'%\
				(server_config.external_base_url+'/yadis/'+userID)

		disco_tags = link_tag + yadis_loc_tag

		ident = server_config.external_base_url + "/openid/" + userID
	
#		approved_trust_roots = []
#		for (aident, trust_root) in OpenIDServer.approved.keys():
#				if aident == ident:
#						trs = '<li><tt>%s</tt></li>\n' % cgi.escape(trust_root)
#						approved_trust_roots.append(trs)
#
#		if approved_trust_roots:
#				prepend = '<p>Approved trust roots:</p>\n<ul>\n'
#				approved_trust_roots.insert(0, prepend)
#				approved_trust_roots.append('</ul>\n')
#				msg = ''.join(approved_trust_roots)
#		else:
#				msg = ''
		msg = ''

		self.write("<html><head><title>Identity Page for %s</title>%s</head><body>%s</body></html>" %
				(ident,
				disco_tags, 
				"<p>This is an identity page for %s.</p>%s" % (ident, msg)))
				
if __name__ == '__main__':
	import doctest
	doctest.testmod()
