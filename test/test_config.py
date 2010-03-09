
SCHEME = "http"
SERVER_NAME = "localhost"
#SCHEME = "https"
#SERVER_NAME = "pm-weave06.mozilla.org"

# python-openid-test-server:
#SCHEME = "http"
#SERVER_NAME = "www.shopmonkey.com:8000"


SERVER_BASE = "%s://%s" % (SCHEME, SERVER_NAME)
OPENID_IDENTIFIER_PREFIX = "%s://%s/openid/" % (SCHEME, SERVER_NAME)
#OPENID_IDENTIFIER_PREFIX = "%s://%s/id/" % (SCHEME, SERVER_NAME)

EXPECTED_OPENID_EXPIRATION = 1209600

