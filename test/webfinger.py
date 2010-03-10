#!/usr/bin/python

# Implementation of a Webfinger client

import urllib2
import httplib
import hashlib
import logging
import unittest
import base64
import xml.dom.minidom

opener = urllib2.build_opener(urllib2.HTTPHandler)

WEBFINGER_SERVICE_REL = "http://webfinger.info/rel/service"
DESCRIBEDBY_REL = "describedby"

class WebfingerException(Exception):
  def __init__(self, value):
    self.value = value
    
  def __str__(self):
    return repr(self.value)

class XRDDocument(object):
  def __init__(self, inBytes):
  
    doc = xml.dom.minidom.parseString(inBytes)
    root = util.nodeToDict(doc.documentElement)
    host = root["Host"]
    links = root["Link"]

    self.host = host
    self.links = links
    self.relMap = {}
    
    for l in links:
      for r in l["rel"]:
        self.relMap[r] = l.lower()

  def applyWebfingerAccountTemplate(self, account):
    webfingerLink = None

    if WEBFINGER_SERVICE_REL in self.relMap:
      template = self.relMap[WEBFINGER_SERVICE_REL]
    elif DESCRIBEDBY_REL in self.relMap:
      template = self.relMap[DESCRIBEDBY_REL]
    else:
      raise ValueError("HostMeta contains no webfinger account resolution information")

    if "URITemplate" in webfingerLink:
      template = webfingerLink["URITemplate"]
      url = template.replace("{id}", account)
      return url
    raise ValueError("Webfinger link in site Host-meta does not contain a URLTemplate")


def resolveHostMeta(domain):
  if domain.find("http:") == 0:
    url = domain + "/.well-known/host-meta";
  elif domain.find("https:") == 0:
    url = domain + "/.well-known/host-meta";	
  else:
    url = "http://" + domain + "/.well-known/host-meta";

  req = urllib2.Request(url)
  f = opener.open(req)
  result = f.read()
  f.close()
  return XRDDocument(result)

    

def resolveUser(address, atSite = None):
  '''If atSite is defined, it overrides the usual hostname resolution of the HOST-META;
    the HOST-META of the given site will be used instead.'''

  try:
    split = address.split("@")
    if split.length != 2:
      raise ValueError("Webfinger Error: must provide a valid account address")

    id = split[0]
    domain = split[1]
    if atSite:
      hostmeta = resolveHostMeta(atSite)
    else:
      hostmeta = resolveHostMeta(domain)
    
    xrdURL = hostmeta.applyAccountTemplate(address)

    req = urllib2.Request(xrdURL)
    f = opener.open(req)
    result = f.read()
    f.close()
    return XRDDocument(result)
  except Exception, e:
    raise WebfingerException("Unable to resolve webfinger for '%s': %s" % (address, e))


def nodeToDict(node):
  base = {}
  for c in node.childNodes:
    if isAllTextChildren(c):
      txt = flattenTextNodes(c.childNodes).strip()
      if c.tagName in base:
        if isinstance(base[c.tagName], list):
          base[c.tagName].append(txt)
        else:
          base[c.tagName] = [base[c.tagName], txt]
      else:
        base[c.tagName] = txt
    else:
      if c.tagName in base:
        if isinstance(base[c.tagName], list):
          base[c.tagName].append(nodeToDict(c))
        else:
          base[c.tagName] = [base[c.tagName], nodeToDict(c)]
      else:
        base[c.tagName] = nodeToDict(c)
  return base

def parse(bytes):
  doc = xml.dom.minidom.parseString(bytes)
  return nodeToDict(doc.documentElement)
