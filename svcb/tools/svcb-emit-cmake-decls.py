#!/usr/bin/env python
# Copyright (c) 2016, Daniel Liew
# This file is covered by the license in LICENSE-SVCB.txt
"""
Reads a benchmark specification file and
emits CMake declarations for building the
bencmarks
"""
from load_svcb import add_svcb_to_module_search_path
add_svcb_to_module_search_path()
import argparse
import logging
import os
import pprint
import svcb
import svcb.benchmark
import svcb.build
import svcb.schema
import sys
import yaml

_logger = None

def main(args):
  global _logger
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("-l","--log-level",type=str, default="info",
                      dest="log_level",
                      choices=['debug','info','warning','error'])
  parser.add_argument('bench_spec_file',
                      help='Benchmark specification file',
                      type=argparse.FileType('r'))
  parser.add_argument('--architecture', type=str, required=True,
                      choices=['x86_64', 'i686', 'unknown'])
  parser.add_argument('-o', '--output',
                      type=argparse.FileType('w'),
                      default=sys.stdout,
                      help='Output location (default stdout)')
  parser.add_argument('--load-dependency-handlers',
                      dest='load_dependency_handlers',
                      default=[],
                      nargs='+',
                      help='Additional dependency handlers to load')
  parser.add_argument('--coverage', action="store_true")


  pArgs = parser.parse_args()
  logLevel = getattr(logging, pArgs.log_level.upper(),None)
  logging.basicConfig(level=logLevel)
  _logger = logging.getLogger(__name__)

  try:
    benchSpec = svcb.schema.loadBenchmarkSpecification(pArgs.bench_spec_file)
  except svcb.schema.BenchmarkSpecificationValidationError as e:
    _logger.error('Failed to validate benchmark specification against schema')
    _logger.error(e.message)
    return 1
  except Exception as e:
    _logger.error('Exception raised whilst loading benchmark specification file')
    _logger.error(str(e))
    raise e

  # Get absolute path to benchmark specification file
  bSpecPath = os.path.realpath(pArgs.bench_spec_file.name)
  sourceFileDirectory = os.path.dirname(bSpecPath)

  # Create a CMakeDependencyDispatcher using the default handlers
  dispatcher = svcb.build.CMakeDependencyDispatcher.getDefaultDispatcher()

  # Load additional handlers
  for fileName in pArgs.load_dependency_handlers:
    if not os.path.exists(fileName):
      _logger.error('Dependency handler "{}" does not exist'.format(fileName))
      return 1
    dispatcher.loadHandlerFromFile(fileName)

  benchmarkObjs = svcb.benchmark.getBenchmarks(benchSpec)
  _logger.debug('Found {} benchmark(s)'.format(len(benchmarkObjs)))
  cmakeDeclStr = svcb.build.generateCMakeDecls(benchmarkObjs,
                                               sourceRootDir=sourceFileDirectory,
                                               supportedArchitecture=pArgs.architecture,
                                               dependencyDispatcher=dispatcher,
                                               coverage=pArgs.coverage)
  pArgs.output.write(cmakeDeclStr)
  return 0

if __name__ == '__main__':
  sys.exit(main(sys.argv))
