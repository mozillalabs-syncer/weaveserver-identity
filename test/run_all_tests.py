#!/usr/bin/python

import run_opensocial_tests
import run_server_tests


def RunAllTests():
  run_opensocial_tests.Run()
  run_server_tests.Run()

if __name__ == '__main__':
  RunAllTests()