#!/usr/bin/python

# This suite contains OpenSocial conformance tests for the Identity Server.

import opensocial_tests

import module_test_runner
import unittest
import logging
import sys

def Run():
	test_runner = module_test_runner.ModuleTestRunner()
	test_runner.modules = [opensocial_tests]
	test_runner.RunAllTests()

import logging

if __name__ == '__main__':
	logging.basicConfig(level = logging.DEBUG)
	if len(sys.argv) > 1:
		runner = unittest.TextTestRunner(verbosity=3)
		for a in sys.argv[1:]:
			runner.run(unittest.defaultTestLoader.loadTestsFromName(a, module=openid_tests))
	else:
		Run()