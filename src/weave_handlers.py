#!/usr/bin/env python
#
import tornado.httpserver
import tornado.ioloop
import tornado.web
import base64
import server_config
account = server_config.account

class WeaveHandler(tornado.web.RequestHandler):

# TODO: I'm not happy with how we're enforcing the URL-to-header
# name match: currently, every authenticated method must call
# check_account_match.  That's error-prone: can we get it added
# to the decorator in some intelligent way?

def get_current_user(self):
  auth = self.request.headers.get("Authorization")
  tokens = auth.split(" ")
  upstr = base64.decodestring(tokens[1])
  up = upstr.split(":")
  if account.checkPassword(up[0], up[1]):
    return up[0]
  raise tornado.web.HTTPError(401)

def check_account_match(self, name):
  if self.get_current_user() != name:
    raise tornado.web.HTTPError(401)
