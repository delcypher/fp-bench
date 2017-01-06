#!/usr/bin/env python3

import argparse
from collections import namedtuple
import glob
import os, os.path
import shutil
import stat
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as xmltree

def mkyamlfuncs():
	from yaml import load, dump
	try:
		from yaml import CLoader as Loader, CDumper as Dumper
	except ImportError:
		from yaml import Loader, Dumper
	return lambda x: load(x, Loader=Loader), lambda x: dump(x, Dumper=Dumper)
yamlLoad, yamlDump = mkyamlfuncs()

def copytree(src, dst, symlinks = False, ignore = None):
	"""copy a directory tree, merging with existing target where necessary
	taken from http://stackoverflow.com/a/22331852/65678"""
	if not os.path.exists(dst):
		os.makedirs(dst)
		shutil.copystat(src, dst)
	lst = os.listdir(src)
	if ignore:
		excl = ignore(src, lst)
		lst = [x for x in lst if x not in excl]
	for item in lst:
		s = os.path.join(src, item)
		d = os.path.join(dst, item)
		if symlinks and os.path.islink(s):
			if os.path.lexists(d):
				os.remove(d)
			os.symlink(os.readlink(s), d)
			try:
				st = os.lstat(s)
				mode = stat.S_IMODE(st.st_mode)
				os.lchmod(d, mode)
			except:
				pass # lchmod not available
		elif os.path.isdir(s):
			copytree(s, d, symlinks, ignore)
		else:
			shutil.copy2(s, d)

PathInfo = namedtuple("PathInfo", ["name", "exe", "cov", "gcno", "gcda", "tests"])
def pathalyze(bcroot, covroot, bc, wd):
	name = os.path.relpath(bc, start=bcroot)[:-3]
	exe = os.path.join(covroot, name)
	head, tail = os.path.split(exe)
	gcno = os.path.join(head, "CMakeFiles", tail + ".dir")
	cov = exe + ".cov"
	gcda = os.path.join(cov, os.path.relpath(gcno, start = covroot))
	tests = glob.iglob(glob.escape(os.path.join(wd, "test")) + "*.ktest")
	return PathInfo(name = name[13:-7], exe = exe, cov = cov, gcno = gcno, gcda = gcda, tests = tests)

def prep(paths, verbose = False):
	if os.path.isdir(paths.cov):
		if verbose:
			print("deleting ", paths.cov, "...", sep="")
		shutil.rmtree(paths.cov)
	os.makedirs(paths.cov)

def runall(paths, kleeLibrary, verbose = False):
	if verbose:
		print("Running tests for ", paths.name, "...", sep="")
	for test in paths.tests:
		env = os.environ.copy()
		env["LD_LIBRARY_PATH"] = kleeLibrary
		env["KTEST_FILE"] = test
		if verbose:
			print("running test ", test, "...", sep="")
		name = os.path.basename(test)
		with open(os.path.join(paths.cov, name + ".out"), "w") as out, open(os.path.join(paths.cov, name + ".err"), "w") as err:
			proc = subprocess.Popen([paths.exe], env=env, cwd=os.path.split(paths.exe)[0], stdout = out, stderr = err)
			proc.wait(60)

def analyze(paths, verbose = False):
	with tempfile.TemporaryDirectory(prefix = "coverage-") as tempdir:
		if verbose:
			print("Copying gcov files to ", tempdir, "...", sep="")
		copytree(paths.gcno, tempdir)
		copytree(paths.gcda, tempdir)
		call = ["gcovr", "-r", tempdir, "-f", "/", "-x"]
		if verbose:
			print("calling ", call, "...", sep="")
		proc = subprocess.run(call, stdout = subprocess.PIPE, check = True)
		if verbose:
			sys.stdout.write(proc.stdout.decode(sys.stdout.encoding))
		branchrate = float(xmltree.fromstring(proc.stdout).attrib["branch-rate"])
		return branchrate

def doit(paths, kleeLibrary, verbose = False):
	prep(paths, verbose)
	runall(paths, kleeLibrary, verbose)
	if os.path.isdir(os.path.join(paths.cov, "benchmarks")): # FIXME
		branchiness = analyze(paths)
	else:
		branchiness = 0.0
	print("Branch coverage is ", branchiness, " for ", paths.name, sep="")
	if verbose:
		print()
	return branchiness

def main(argv):
	parser = argparse.ArgumentParser()
	parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
	parser.add_argument("-o", "--output", help="path to output file", default="coverage_report.yml")
	requiredNamed = parser.add_argument_group('required named arguments')
	requiredNamed.add_argument("--bc", help="the path to the root of where you built the bytecode files", required=True)
	requiredNamed.add_argument("--cov", help="the path to the root of where you built the coverage binaries", required=True)
	requiredNamed.add_argument("--yaml", help="the path to the yaml file that was generated for your KLEE run", required=True)
	requiredNamed.add_argument("--kleelib", help="the path to your KLEE library directory", required=True)
	args = parser.parse_args(argv)

	with open(args.output, "w") as out:
		out.write("results:\n")
		with open(args.yaml) as f:
			testspec = yamlLoad(f)
		for result in testspec["results"]:
			paths = pathalyze(os.path.realpath(args.bc), os.path.realpath(args.cov), result["invocation_info"]["program"], result["klee_dir"])
			branchiness = doit(paths, os.path.realpath(args.kleelib), args.verbose)
			out.write("- program: {}\n  branch_coverage: {:14f}\n".format(paths.name, branchiness))

if __name__ == "__main__":
	main(sys.argv[1:])
