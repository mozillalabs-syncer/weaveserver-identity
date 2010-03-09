import account
import logging
import ldap
import sys
import server_config

try:
	server_config.LDAP_SERVER
except NameError, e:
	print "To use the LDAP account driver, the LDAP_SERVER variable must be defined before account_ldap is imported."
	sys.exit()	


def constructUserDN(username):
#	return "%s=%s,%s" % (WEAVE_LDAP_AUTH_USER_PARAM_NAME, username, WEAVE_LDAP_AUTH_DN)
#	LDAP_HANDLE_BASE_DN = 'mail=%s@mozilla.com,o=com,dc=mozilla'
	return 'mail=%s@mozilla.com,o=com,dc=mozilla' % username

def get_connection():
#		ldap_set_option($this->_conn, LDAP_OPT_PROTOCOL_VERSION, 3);
	return ldap.initialize(server_config.LDAP_SERVER)

def nameIsAvailable(name):
	pass
	
def create(name, password, email):
	pass
	
def delete(name):
	pass
	
def checkPassword(name, password):
	dn = constructUserDN(name)
	conn = get_connection()
	logging.error("Connected to LDAP server")
	try:
		logging.error("Attempting LDAP bind for %s" % dn)
		conn.simple_bind(dn, password)
		res = conn.search_s( dn, ldap.SCOPE_BASE, "objectClass=*", ['*'] )
		return True
	except Exception, e:	
		logging.error("unable to bind: %s" % e)
		return False

def getStorageNode(name):
	pass
	
def setPassword(name, password):
	pass

def setEmail(name, email):
	pass