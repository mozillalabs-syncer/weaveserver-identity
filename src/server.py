#!/usr/bin/env python
#
import tornado.httpserver
import tornado.ioloop
import tornado.web
import os
import re
import time
import calendar
import base64
import traceback
import logging
import cStringIO
import json
import cgi
from urlparse import urlparse

# Hm, this is inconsistent.  Fix it.
import server_config
account = server_config.account
from storage import WeaveStorageException
storage = server_config.storage

from weave_handlers import WeaveHandler
import opensocial_handlers
import openid_handlers
    
class MainHandler(WeaveHandler):
  def get(self):
    self.render("main.html", errorMessage=None)

class UsernameRootHandler(WeaveHandler):
  def get(self, name):
    if account.nameIsAvailable(name):
      self.write("0")
    else:
      self.write("1")

  def put(self, name):
    args = json.loads(self.request.body)
    # TODO handle captcha, invite code, secret, etc.
    try:
      name = name.lower()
      account.create(name, password=args['password'], email=args['email'])
      self.write(name)
    except Exception, e:
      # TODO: return weave error codes
      raise tornado.web.HTTPError(500, str(e))
  
  @tornado.web.authenticated
  def delete(self, name):
    self.check_account_match(name)
    account.delete(name)
    
class SetEmailHandler(WeaveHandler):
  @tornado.web.authenticated
  def post(self, name):
    self.check_account_match(name)
    account.setEmail(name, self.request.body)
    self.write(self.request.body)

class SetPasswordHandler(WeaveHandler):
  @tornado.web.authenticated
  def post(self, name):
    self.check_account_match(name)
    account.setPassword(name, self.request.body)
    self.write("success")

class GetStorageNodeHandler(WeaveHandler):
  def get(self, name):
    node = account.getStorageNode(name)
    if node:
      self.write(node)
    else:
      if account.nameIsAvailable(name):
        raise tornado.web.HTTPError(404, "Not Found")
      else:
        self.write("%s://%s" % (server_config.external_scheme, server_config.external_hostname))


##### BEGIN STORAGE API ########


class CollectionTimestampsHandler(WeaveHandler):
  @tornado.web.authenticated
  def get(self, name):
    self.check_account_match(name)
    ctx = storage.get_context(name)		
    tsMap = storage.collection_timestamps(ctx)
    self.write(json.dumps(tsMap))

class CollectionCountsHandler(WeaveHandler):
  @tornado.web.authenticated
  def get(self, name):
    self.check_account_match(name)
    ctx = storage.get_context(name)		
    ts = storage.collection_counts(ctx)
    self.write(json.dumps(ts))

class StorageHandler(WeaveHandler):
  @tornado.web.authenticated
  def get(self, name):
    self.check_account_match(name)
    pass

  def delete(self, name):
    self.check_account_match(name)
    # TODO require confirmation header
    ctx = storage.get_context(name)
    storage.delete(ctx)

class CollectionHandler(WeaveHandler):
  @tornado.web.authenticated
  def get(self, name, collection=None, id=None):
    self.check_account_match(name)
    if not collection:
      raise tornado.web.HTTPError(400, "Missing required collection")

    ctx = storage.get_context(name)
    wbo = storage.get(ctx, collection, id, query=self.request.arguments)
    if wbo:
      self.write(str(wbo))
    else:
      raise tornado.web.HTTPError(404, "Not Found")

  def put(self, name, collection=None, id=None):
    self.check_account_match(name)
    if not collection:
      raise tornado.web.HTTPError(400, "Missing required collection")
    ctx = storage.get_context(name)

    try:
      ius = 'X-If-Unmodified-Since' in self.request.headers and self.request.headers['X-If-Unmodified-Since'] or None		

      if ius and storage.collection_modification_date(ctx, collection) > float(ius):
        logging.error("Rejecting PUT because of modification date")
        raise tornado.web.HTTPError(412, "No overwrite")

      ts = storage.add_or_modify(ctx, collection, self.request.body, id=id, query=self.request.arguments)
      self.write(str(ts))
    except WeaveStorageException, e:
      raise tornado.web.HTTPError(400, str(e))


  def post(self, name, collection):
    self.check_account_match(name)
    if not collection:
      raise tornado.web.HTTPError(400, "Missing required collection")
    ctx = storage.get_context(name)

    ius = 'X-If-Unmodified-Since' in self.request.headers and self.request.headers['X-If-Unmodified-Since'] or None		

    if ius and storage.collection_modification_date(ctx, collection) > float(ius):
      logging.error("Rejecting PUT because of modification date")
      raise tornado.web.HTTPError(412, "No overwrite")

    success_ids = []
    failed_ids = {}
    # storage.begin_transaction()
    json_data = json.loads(self.request.body)
    ts = time.time()
    for j in json_data:
      try:
        storage.add_or_modify(ctx, collection, j)
        success_ids.append(j['id'])
      except Exception, e:
        try:
          failed_ids[j['id']] = str(e)
        except:
          pass # missing ID ends up here
    # storage.commit_transaction()
    self.write(json.dumps({'modified':ts, 'success':success_ids, 'failed':failed_ids}))

  def delete(self, name, collection, id=None):
    self.check_account_match(name)
    if not collection:
      raise tornado.web.HTTPError(400, "Missing required collection")
    ctx = storage.get_context(name)

    ius = 'X-If-Unmodified-Since' in self.request.headers and self.request.headers['X-If-Unmodified-Since'] or None		
    if ius and storage.collection_modification_date(ctx, collection) > float(ius):
      logging.error("Rejecting PUT because of modification date")
      raise tornado.web.HTTPError(412, "No overwrite")

    if id:
      storage.delete(ctx, collection, id=id)
    else:
      storage.delete(ctx, collection, query=self.request.arguments)
    self.write(str(float(int(time.time() * 100)) / 100))
    

XML_BOILERPLATE = "<?xml version='1.0' encoding='UTF-8'?>\n"
XRD_NS = "http://docs.oasis-open.org/ns/xri/xrd-1.0"
        
class XRDPageHandler(WeaveHandler):
  def get(self, name):
    ctx = storage.get_context(name)
    wbo = storage.get(ctx, 'services', 'root')
    self.set_header('Content-Type', 'text/xml')
    self.write(XML_BOILERPLATE)
    self.write("<XRD xmlns='%s'>\n" % XRD_NS)
    if wbo:
      list = json.loads(wbo.payload)
      self.write("\t<Subject>acct:%s@id.mozilla.com</Subject>\n" % name)
      for l in list:
        rel = l['rel']
        uri = l['uri']
        self.write("<Link>\n<Rel>%s</Rel>\n<URI>%s</URI>\n</Link>\n" % (cgi.escape(rel), cgi.escape(uri)))
    self.write("</XRD>")

##################################################################
# Main Application Setup
##################################################################

settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
    "cookie_secret": "dfaDSGSLJGfsdlfselrfg532rsf24552ksgslkfjllj=",
    "login_url": "/login"
#    "xsrf_cookies": True,
}

application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/user/1/([a-zA-Z0-9-_]+)/?", UsernameRootHandler),# TODO note ambiguity about trailing slash
    (r"/user/1/([a-zA-Z0-9-_]+)/node/weave", GetStorageNodeHandler),
    (r"/user/1/([a-zA-Z0-9-_]+)/email", SetEmailHandler),
    (r"/user/1/([a-zA-Z0-9-_]+)/password", SetPasswordHandler),

    # Storage functions:
    (r"/1.0/([a-zA-Z0-9-_]+)/info/collections", CollectionTimestampsHandler),
    (r"/1.0/([a-zA-Z0-9-_]+)/info/collection_counts", CollectionCountsHandler),
    (r"/1.0/([a-zA-Z0-9-_]+)/storage", StorageHandler),
    (r"/1.0/([a-zA-Z0-9-_]+)/storage/([a-zA-Z0-9_-]+)", CollectionHandler),
    (r"/1.0/([a-zA-Z0-9-_]+)/storage/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_-]+)", CollectionHandler), # with an ID...

    # "Home page" implementation
    # (r"/([a-zA-Z0-9-_]+)", HomePageHandler)

    # OpenSocial implementation
    (r"/opensocial/rest/people/([a-zA-Z0-9-_]+)/(.*)", opensocial_handlers.OpenSocialPeopleHandler),

    # OpenID implementation
    (r"/openid", openid_handlers.OpenIDServerEndpoint),
    (r"/openid/allow", openid_handlers.OpenIDAllowEndpoint),
    (r"/openid/([a-zA-Z0-9-_]+)", openid_handlers.OpenIDUserEndpoint),

    # User XRD page
    (r"/([a-zA-Z0-9-_]+)/xrd", XRDPageHandler)
    

#    (r"/user/1/([a-zA-Z0-9-_]+)/password_reset", PasswordResetHandler)
#    (r"/profile/(.*)", ProfileHandler)
  ], **settings)

def run():
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(80)
    tornado.ioloop.IOLoop.instance().start()
    
import logging
import sys
if __name__ == '__main__':
  if '-test' in sys.argv:
    import doctest
    doctest.testmod()
  else:
    logging.basicConfig(level = logging.DEBUG)
    run()
  
  