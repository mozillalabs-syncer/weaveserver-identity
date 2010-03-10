#!/usr/bin/python

import random
import urllib
import httplib
import hashlib
import unittest
from base64 import b64encode

import weave
import opensocial
import test_config


SERVER_BASE = test_config.SERVER_BASE
TEST_CONFIG = opensocial.ContainerConfig(
    server_rpc_base = SERVER_BASE + '/opensocial/rpc/',
    server_rest_base = SERVER_BASE + '/opensocial/rest/',
)

#config = opensocial.ContainerConfig(
#     oauth_consumer_key='<put your consumer key here>',
#      oauth_consumer_secret='<put your consumer secret here>',
#      server_rpc_base='http://path/to/rpc/base',
#      server_rest_base='http://path/to/rest/base')
#
#container = opensocial.ContainerContext(config)#
#
#request = opensocial.FetchPersonRequest(user_id='@me')


class TestFetching(unittest.TestCase):
  def setUp(self):
    # Create a bunch of people using Weave Acct Mgmt API
    self.personID = '1234'

  def testSingleFetch(self):
    # basic fetch
    # of @me?
    # do we support any other IDs?
    pass

  def testMultipleFetch(self):
    # do we support multiple fetch?
    # exercise count
    # exercise paging
    pass

class TestProfileUpdate(unittest.TestCase):
  
  def setUp(self):
    self.userID = 'weaveunittest_' + ''.join([chr(random.randint(ord('a'), ord('z'))) for i in xrange(10)])
    self.password = 'mypassword'
    self.email = 'user@unittest.com'

    self.failUnless(weave.checkNameAvailable(SERVER_BASE, self.userID))
    weave.createUser(SERVER_BASE, self.userID, self.password, self.email)
    
    # Get an OpenSocial container reference
    config = opensocial.ContainerConfig(
      oauth_consumer_key='anonymous',
      oauth_consumer_secret='anonymous',
      server_rpc_base=TEST_CONFIG.server_rpc_base,
      server_rest_base=TEST_CONFIG.server_rest_base)
      
    self.container = opensocial.ContainerContext(config)		

  def testUpdate(self):

    request = opensocial.FetchPersonRequest(self.userID)
    starting_result = self.container.send_request(request, use_rest=True)
    
    request = opensocial.UpdatePersonRequest(self.personID, "{jsonifiedperson}")
    result = self.container.send_request(request)

    request = opensocial.FetchPersonRequest(self.personID)
    ending_result = self.container.send_request(request)
    
    # exercise adding new, lists, removing values
    # does the server enforce unary field restrictions?
    # are there values that we're not allowed to touch?
    
    # exercise changing permissions
    # view as self, view as other
    # make unreadable by other - can self still read?  can other not?
    # test groups
    
    
class TestOAuth(unittest.TestCase):

  def setUp(self):
    # Create the main user
    # Create some other users	
    # Grant access to main from some, not others
    pass
  
  def testSuccess(self):
    # establish a container that simulates another service
    # using OAuth to log in as that user
    # read the user's profile
    # can read some
    # can't read others
    pass
    

  def testWrongPassword(self):
    # Try to use OAuth, but wrong password
    # Can't do anything now
    pass

  # Other:
  # Expired access token
  # Revoke access token?

