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
from xml.sax.saxutils import escape as saxescape


# Hm, this is inconsistent.  Fix it.
import server_config
account = server_config.account
from storage import WeaveStorageException
storage = server_config.storage

from weave_handlers import WeaveHandler


OPENSOCIAL_NS_URI = "http://ns.opensocial.org/2008/opensocial"

class HTMLEscapeType(object):
  def escape(str):
    return cgi.escape(str)
    
HTMLEscape = HTMLEscapeType()
Escapes = {"htmlEscape":HTMLEscape}

class XMLFormatHandler(object):
  # Gah, how to handle this API?  We can't really introspect on people easily.
  def writeResponse(self, handler, escaper, responseType, responseObject):
    self.write("""<response xmlns="%s">\n""" % OPENSOCIAL_NS_URI)
    self.write("""<%s>\n""" % responseType)
    for key, value in responseObject.items():
      self.writeKV(handler, escaper, key, value)
    self.write("""</%s>\n""" % responseType)
    self.write("""</response>\n""")

  def writeKV(self, handler, escaper, key, value):
    try:
      keys = value.keys()
      if keys:
        for key in keys:
          self.writeKV(handler, escaper, key, value[key])
    except AttributeError, e: 
      # Not a mapping: serialize it directly
      tag = self.excapeXML(key)
      value = self.escapeXML(escaper.escape(value))
      self.write("<%s>%s</%s>\n", tag, value, tag)
      
  def escapeXML(self, str):
    """
    >>> XMLFormatHandler().escapeXML(u"a<b>c&d\u00e9")
    "a&lt;b&gt;c&amp;d&xe9;"
    """
    # Hm, not sure what I really want here.
    #return str.encode("utf-8", "xmlcharrefreplace")
    return saxescape(str).encode("utf-8")

class AtomFormatHandler(object):
  def write(self, handler, escaper, data):
    return "Atom Format Not Supported"

class JSONFormatHandler(object):
  def write(self, handler, escaper, data):
    return json.dumps(obj)

XMLFormat = XMLFormatHandler()
AtomFormat = AtomFormatHandler()
JSONFormat = JSONFormatHandler()
Formats = {"xml":XMLFormat, "atom":AtomFormat, "json":JSONFormat}

def resolveFormatArg(request):
  "Resolves an HTTP request to a formatter object; returns JSON by default"
  if 'format' in request.arguments:
    fmt = request.arguments['format'][0]
    if fmt in Formats:
      return Formats[fmt]
  return JSONFormat

def resolveEscapeArg(request):
  "Resolves an HTTP request to an Escape object; returns HTML by default"
  if 'escapeType' in request.arguments:
    et = request.arguments['escapeType'][0]
    if et in Escapes:
      return Escapes[et]
  return HTMLEscape
  
  
dateTimeRE = re.compile(r"""(?P<year>\d\d\d\d)
 ([-])?(?P<month>\d\d)
 ([-])?(?P<day>\d\d)
 (
  (T|\s+)
  (?P<hour>\d\d)
  (
   ([:])?(?P<minute>\d\d)
   (
    ([:])?(?P<second>\d\d)
    (
     ([.])?(?P<fraction>\d+)
    )?
   )?
  )?
 )?
 (
  (?P<tzzulu>Z)
  |
  (?P<tzoffset>[-+])
  (?P<tzhour>\d\d)
  ([:])?(?P<tzminute>\d\d)
 )?
 $
 """, re.VERBOSE)

def resolveUpdatedSinceArg(request):
  """If the provided HTTP request header contains a 'updatedSince' value,
  parses the value and returns it as a number of seconds since 1970.
  
  >>> class R(object): pass
  >>> r = R()

  >>> r.arguments = {'updatedSince':['2002-05-06T13:12:13']}
  >>> time.gmtime(resolveUpdatedSinceArg(r))
  time.struct_time(tm_year=2002, tm_mon=5, tm_mday=6, tm_hour=13, tm_min=12, tm_sec=13, tm_wday=0, tm_yday=126, tm_isdst=0)

  >>> r.arguments = {'updatedSince':['2002-05-06T13:12:13-00:00']}
  >>> time.gmtime(resolveUpdatedSinceArg(r))
  time.struct_time(tm_year=2002, tm_mon=5, tm_mday=6, tm_hour=13, tm_min=12, tm_sec=13, tm_wday=0, tm_yday=126, tm_isdst=0)

  >>> r.arguments = {'updatedSince':['2002-05-06T13:12:13+07:30']}
  >>> time.gmtime(resolveUpdatedSinceArg(r))
  time.struct_time(tm_year=2002, tm_mon=5, tm_mday=6, tm_hour=20, tm_min=42, tm_sec=13, tm_wday=0, tm_yday=126, tm_isdst=0)

  >>> r.arguments = {'updatedSince':['2002-05-06T13:12:13-07:30']}
  >>> time.gmtime(resolveUpdatedSinceArg(r))
  time.struct_time(tm_year=2002, tm_mon=5, tm_mday=6, tm_hour=5, tm_min=42, tm_sec=13, tm_wday=0, tm_yday=126, tm_isdst=0)

  """

  if 'updatedSince' in request.arguments:
    us = request.arguments['updatedSince'][0]
    # value space of US is an XML Schema DateTime
    #return time.strptime(us, "%Y-%m-%dT%H:%M:%S%Z")
    ma = dateTimeRE.match(us)
    m = ma.groupdict()
    
    year = 0
    if m['year']:
      try: year = int(m['year'])
      except: pass
    month = 0
    if m['month']:
      try: month = int(m['month'])
      except: pass
    day = 0
    if m['day']:
      try: day = int(m['day'])
      except: pass
    minute = 0
    if m['minute']:
      try: minute = int(m['minute'])
      except: pass
    hour = 0
    if m['hour']:
      try: hour = int(m['hour'])
      except: pass
      if m['tzoffset'] and m['tzhour']:
        if m['tzoffset'] == '-': sign = -1
        else: sign = 1
        try:
          hour += int(m['tzhour']) * sign
          if m['tzminute']:
            minute += int(m['tzminute']) * sign
        except: pass
    seconds = 0
    if m['second']:
      try: 
        seconds = int(m['second'])
        if m['fraction']: 
          seconds += float(m['fraction'])
      except: pass
  
    return calendar.timegm((year, month, day, hour, minute, seconds, 0, 0, -1))
    # TODO handle time zone
    
  return None

class OpenSocialPeopleHandler(WeaveHandler):
  def get(self, username, argument):
    # Some magical usernames: @me, -1
  
    # for now we only support the '@self' argument
    # we could also expect to see /<group-id>/<related-user-id>
    
    if argument == '@self':
      # handle parameters
      if 'userId' in self.request.arguments:
        raise tornado.web.HTTPError(400, "userId is not a legal argument for REST OpenSocial Get Person requests")

      escape = resolveEscapeArg(self.request)			
      format = resolveFormatArg(self.request)
      updatedSince = resolveUpdatedSinceArg(self.request)
      
      ctx = storage.get_context(username)
      wbo = storage.get(ctx, 'profile', 'root')
      if wbo:
        profileData = wbo.payload
        
        # Filter the profile data through the access control policy for this request...
        # And the updatedSince....
        
        # And return it
        format.write(self, escape, profileData)
      else:
        raise tornado.web.HTTPError(404, "Not Found")			

  def put(self, name, collection=None):
    self.check_account_match(name)
    if not collection:
      raise tornado.web.HTTPError(400, "Missing required collection")
    ts = storage.handle_put(name, collection, self.request.body)
    self.write(str(ts))
    
    
if __name__ == '__main__':
  import doctest
  doctest.testmod()
    