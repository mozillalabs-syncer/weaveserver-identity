#!/usr/bin/python

import module_test_runner
import webfinger_tests

def Run():
  test_runner = module_test_runner.ModuleTestRunner()
  test_runner.modules = [webfinger_tests]
  test_runner.RunAllTests()

import logging

if __name__ == '__main__':
	logging.basicConfig(level = logging.DEBUG)
	Run()