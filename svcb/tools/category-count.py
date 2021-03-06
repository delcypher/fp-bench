#!/usr/bin/env python
# Copyright (c) 2016, Daniel Liew
# This file is covered by the license in LICENSE-SVCB.txt
"""
Traverse a directory looking for benchmarks
and group them by category
"""
from load_svcb import add_svcb_to_module_search_path
add_svcb_to_module_search_path()
import svcb.schema
import svcb.benchmark
import argparse
import logging
import os
import sys

_logger = None

def main(args):
  global _logger
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("-l","--log-level",type=str, default="info",
                      dest="log_level",
                      choices=['debug','info','warning','error'])
  parser.add_argument("--show-benchmark-names",
                      action='store_true',
                      default=False,
                      dest='show_benchmark_names')
  parser.add_argument("--all-categories", dest='all_categories', type=str,
      nargs='+', default=None, help='Only count benchmarks belonging to all the specified categories')
  parser.add_argument("directory",
                      type=str,
                      help="Directory to traverse")
  pargs = parser.parse_args(args)
  logLevel = getattr(logging, pargs.log_level.upper(),None)
  logging.basicConfig(level=logLevel)
  _logger = logging.getLogger(__name__)

  if not os.path.isdir(pargs.directory):
    _logger.error('"{}" is not a directory'.format(pargs.directory))
    return 1

  # Stats
  benchmarkFileParseSuccess = set()
  benchmarkFileParseFailures = set()
  categoryToBenchmarkNames = {}
  uncategorisedBenchmarks = set()
  benchmarksFilteredOut = set()
  benchmarkToFileMap = dict()

  # Traverse directory
  for dirpath, dirnames, filenames in os.walk(pargs.directory):
    for fname in filenames:
      if fname == 'spec.yml':
        fullFileName = os.path.join(dirpath, fname)
        _logger.debug('Found file "{}"'.format(fullFileName))

        benchSpec = None
        try:
          with open(fullFileName, 'r') as f:
            benchSpec = svcb.schema.loadBenchmarkSpecification(f)
        except svcb.schema.BenchmarkSpecificationValidationError as e:
          _logger.error('Failed to validate "{}"'.format(fullFileName))
          benchmarkFileParseFailures.add(fullFileName)
          continue

        _logger.debug('Successfuly parsed and validated "{}"'.format(fullFileName))
        benchmarkFileParseSuccess.add(fullFileName)
        sys.stdout.write("Loaded {} file(s)\r".format(len(benchmarkFileParseSuccess)))

        # Convert to BenchmarkObjects. This also handles variants by giving
        # back multiple BenchmarkObjects
        benchmarkObjs = svcb.benchmark.getBenchmarks(benchSpec)
        assert len(benchmarkObjs) > 0
        for benchmarkObj in benchmarkObjs:
          if benchmarkObj.name in benchmarkToFileMap:
            _logger.error('Attempted to load benchmark "{}" ({}) but a benchmark with the same name was already loaded from "{}"'.format(
              benchmarkObj.name,
              fullFileName,
              benchmarkToFileMap[benchmarkObj.name]))
            return 1
          benchmarkToFileMap[benchmarkObj.name] = fullFileName
          if len(benchmarkObj.categories) == 0:
            uncategorisedBenchmarks.add(benchmarkObj.name)
            continue
          if pargs.all_categories is not None:
            # Filter out benchmarks not in all specified categories
            filterOut = False
            for category in pargs.all_categories:
              if category not in benchmarkObj.categories:
                benchmarksFilteredOut.add(benchmarkObj.name)
                _logger.debug('Filtering out "{}" because "{}" is not in category'.format(benchmarkObj.name, category))
                filterOut = True
                break
            if filterOut:
              continue

          # Handle categories
          for category in benchmarkObj.categories:
            if categoryToBenchmarkNames.get(category) == None:
              categoryToBenchmarkNames[category] = set()
            categoryToBenchmarkNames[category].add(benchmarkObj.name)

  # Show statistics
  print("")
  print("# of file(s) successfully parsed: {}".format(len(benchmarkFileParseSuccess)))
  print("# of file(s) unsuccessfully parsed: {}".format(len(benchmarkFileParseFailures)))
  print("# of benchmarks: {}".format(len(benchmarkToFileMap.keys())))
  print("# of uncategorised benchmarks: {}".format(len(uncategorisedBenchmarks)))
  print("# of filtered out benchmarks: {}".format(len(benchmarksFilteredOut)))
  print("")
  print("=== Categories ===")
  # Show categories with counts, sorted by category name
  for categoryName, benchmarkNames in sorted(categoryToBenchmarkNames.items(),key = lambda pair: pair[0]):
    print("{category}: {count}".format(category=categoryName, count=len(benchmarkNames)))
    if pargs.show_benchmark_names:
      for benchmarkName in sorted(benchmarkNames):
        fileName = benchmarkToFileMap[benchmarkName]
        print("{} (declared in \"{}\")".format(benchmarkName, fileName))
      print("="*80)

  return 0

if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
