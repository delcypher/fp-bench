# Floating Point correctness benchmark repository.

Build Status: [![Build Status](https://travis-ci.org/delcypher/fp-bench.svg?branch=master)](https://travis-ci.org/delcypher/fp-bench)

This repository contains a system for organising and building
various benchmarks.

In this system each benchmark is placed in its own folder containings

* Source files
* A benchmark specification file (``spec.yml``)

This system of organisation is fork of https://github.com/delcypher/svcomp-build-mockup

## Benchmark specification file

This [YAML](http://www.yaml.org/) file contains the relevant information for
verifiying and compiling the benchmark.

The schema for these benchmark specification files is written using
[json-schema](http://json-schema.org/) and be found at
[svcb/svcb/schema.yml](svcb/svcb/schema.yml).

Please note that the schema currently isn't finalised.

Having such a format is useful because

* It is clear how benchmarks should be compiled.
* It is clear what properties should be verified/checked for.
* It is easy to gather statistics on the benchmarks.

A key concept to understand with this format is that a `spec.yml` can declare
multiple benchmarks by declaring multiple variants. If no variants are specified
or if there is only one variant the `spec.yml` file only declares a single benchmark.

Having variants is useful for having benchmarks where small changes guarded by macro
definitions create different versions of a benchmark from the same source files.

## Requirements

Before building the benchmarks you will need the following installed:

* A working C and C++ compiler
* [CMake](https://cmake.org/) >= 2.8.12
* [Python](https://www.python.org/) >= 2.7
* [jsonschema](https://pypi.python.org/pypi/jsonschema) and [pyyaml](https://pypi.python.org/pypi/PyYAML) Python modules

## Building benchmarks as native binaries

Here are the basic steps for building the benchmarks.

```
$ mkdir build
$ cd build
$ KLEE_NATIVE_RUNTIME_LIB_DIR=<KLEE_RUNTIME_LIB_DIR> KLEE_NATIVE_RUNTIME_INCLUDE_DIR=<KLEE_RUNTIME_INCLUDE_DIR>  cmake ../
$ make
```

where `<KLEE_RUNTIME_LIB_DIR>` is the directory containing `libkleeRuntest.so` and `<KLEE_RUNTIME_INCLUDE_DIR>` is the
directory containing `klee/klee.h`. You can get and build KLEE from [GitHub](https://github.com/klee/klee).

Note by default it is enforced that the KLEE runtime be available because the majority of the benchmarks will require it.
However you can change this by passing `-DKLEE_NATIVE_RUNTIME_REQUIRED=FALSE` when invoking CMake. Doing this will cause
only the benchmarks that don't need the KLEE runtime.


## Building benchmarks as LLVM bitcode

KLEE can't run native binaries. Instead it runs LLVM bitcode. To build the benchmarks as LLVM bitcode you should follow
the steps above but use [Whole Program LLVM](https://github.com/travitch/whole-program-llvm) as the compiler rather
than your normal host compiler.

The invocation to CMake will probably look something like this:

```
$ export WLLVM_COMPILER=clang
$ mkdir build_llvm
$ cd build_llvm
$ CC=wllvm CXX=wllvm++ KLEE_NATIVE_RUNTIME_LIB_DIR=<KLEE_RUNTIME_LIB_DIR> KLEE_NATIVE_RUNTIME_INCLUDE_DIR=<KLEE_RUNTIME_INCLUDE_DIR>  cmake ../
$ make
```

then you would run the `extract-bc` tool that comes with Whole Program LLVM to get the bitcode file that corresponds to the native binary.

## Running schema tests

```
make check-svcb
```

## Displaying the number of benchmarks by category

```
make show-categories
```

## Displaying the number of verification tasks

```
make show-tasks
```

## Displaying a summary of benchmark correctness

```
make show-correctness-summary
```

## Benchmark tools

You can find various tools in `svcb/tools/`.

## `category-count.py`

This tool will recursively traverse a specified directory parsing all found `spec.yml` files and reporting the found categories and how
many benchmarks are in each category.

## `correctness-count.py`

This tool will recursively traverse a specified directory parsing all found `spec.yml` files and reporting all the found verification tasks.

## `svcb-emit-cmake-decls.py`

A tool for internal use that when given a `spec.yml` file will declare all the targets (i.e. the benchmarks) to be built for the CMake build system.

## `svcb-show-targets.py`

This tool when given a `spec.yml` file will parse it and display all the benchmarks declared by the file. Note there will only be multiple
benchmarks in a `spec.yml` file is multiple variants are declared in it.
