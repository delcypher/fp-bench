# Copyright (c) 2016, Daniel Liew
# This file is covered by the license in LICENSE-SVCB.txt

# This overrides the default flags for the different CMAKE_BUILD_TYPEs
set(CMAKE_USER_MAKE_RULES_OVERRIDE_C "${CMAKE_CURRENT_SOURCE_DIR}/cmake/c_flags_override.cmake")
set(CMAKE_USER_MAKE_RULES_OVERRIDE_CXX "${CMAKE_CURRENT_SOURCE_DIR}/cmake/cxx_flags_override.cmake")
project(SVCOMP_C_BENCHMARKS C CXX)
cmake_minimum_required(VERSION 3.0.2)

################################################################################
# Set the root of SVCB infrastructure
################################################################################
set(SVCB_DIR "${CMAKE_SOURCE_DIR}/svcb")

################################################################################
# Sanity check - Disallow building in source to avoid conflicting with
# ``Makefiles`` that exist in the main ``sv-benchmarks`` repository and would
# cause problems if we ever merged.
################################################################################
if ("${CMAKE_SOURCE_DIR}" STREQUAL "${CMAKE_BINARY_DIR}")
  message(FATAL_ERROR "In source builds are not allowed. You should invoke "
          "CMake from a different directory.")
endif()

###############################################################################
# Set useful variables depending on CMake version
###############################################################################
if (("${CMAKE_VERSION}" VERSION_EQUAL "3.2") OR ("${CMAKE_VERSION}" VERSION_GREATER "3.2"))
  # In CMake >= 3.2 add_custom_command() supports a ``USES_TERMINAL`` argument
  set(ADD_CUSTOM_COMMAND_USES_TERMINAL_ARG "USES_TERMINAL")
else()
  set(ADD_CUSTOM_COMMAND_USES_TERMINAL_ARG "")
endif()
# Detect target supported by compiler
include(${CMAKE_SOURCE_DIR}/cmake/target_arch_detect.cmake)
detect_target_architecture(SVCOMP_ARCHITECTURE)
if (NOT SVCOMP_ARCHITECTURE)
  message(FATAL_ERROR "Failed to detect target architecture")
endif()

################################################################################
# Build type
################################################################################
message(STATUS "CMake generator: ${CMAKE_GENERATOR}")
if (DEFINED CMAKE_CONFIGURATION_TYPES)
  # Multi-configuration build (e.g. Visual Studio and Xcode). Here
  # CMAKE_BUILD_TYPE doesn't matter
  message(STATUS "Available configurations: ${CMAKE_CONFIGURATION_TYPES}")
else()
  # Single configuration generator (e.g. Unix Makefiles, Ninja)
  set(available_build_types Debug Release RelWithDebInfo MinSizeRel)
  if(NOT CMAKE_BUILD_TYPE)
    message(STATUS "CMAKE_BUILD_TYPE is not set. Setting default")
    message(STATUS "The available build types are: ${available_build_types}")
    set(CMAKE_BUILD_TYPE RelWithDebInfo CACHE String
        "Options are ${available_build_types}"
        FORCE)
    # Provide drop down menu options in cmake-gui
    set_property(CACHE CMAKE_BUILD_TYPE PROPERTY STRINGS ${available_build_types})
  endif()
  message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
endif()

###############################################################################
# Set default project BUILD_TYPE
###############################################################################
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE "Release" CACHE STRING
      "Choose the type of build, options are: Debug Release RelWithDebInfo MinSizeRel." FORCE)
endif()
message(STATUS "CMAKE_BUILD_TYPE:${CMAKE_BUILD_TYPE}")

###############################################################################
# Find Python
###############################################################################
find_package(PythonInterp REQUIRED)
if ("${PYTHON_VERSION_STRING}" VERSION_LESS "2.7.0")
  message(FATAL_ERROR "Detected version of Python is too old (need >= 2.7)."
    " You can pass -DPYTHON_EXECUTABLE=/path/python to use a different version"
    " of Python")
endif()

###############################################################################
# Setup global include directory
###############################################################################
include_directories("${CMAKE_SOURCE_DIR}/include")

###############################################################################
# Setup variables used by auto generated CMake files
###############################################################################
include(CheckCCompilerFlag)
include(CheckCXXCompilerFlag)
function(SVCOMP_SANITIZE_FLAG_NAME OUTPUT_VAR FLAG)
  string(REPLACE "-" "_" SANITIZED_FLAG_NAME "${FLAG}")
  string(REPLACE "/" "_" SANITIZED_FLAG_NAME "${SANITIZED_FLAG_NAME}")
  string(REPLACE "=" "_" SANITIZED_FLAG_NAME "${SANITIZED_FLAG_NAME}")
  string(REPLACE " " "_" SANITIZED_FLAG_NAME "${SANITIZED_FLAG_NAME}")
  set(${OUTPUT_VAR} "${SANITIZED_FLAG_NAME}" PARENT_SCOPE)
endfunction()

# FIXME: This assumes a gcc/clang like compiler
macro(SVCOMP_CHECK_C_LANG_STD flag name)
  CHECK_C_COMPILER_FLAG("${flag}" HAS_${name})
  if (HAS_${name})
    set(SVCOMP_${name} "${flag}")
  else()
    message(WARNING "C standard ${name} is not supported")
  endif()
endmacro()
SVCOMP_CHECK_C_LANG_STD("-std=c89" STD_C89)
SVCOMP_CHECK_C_LANG_STD("-std=c99" STD_C99)
SVCOMP_CHECK_C_LANG_STD("-std=c11" STD_C11)
SVCOMP_CHECK_C_LANG_STD("-std=gnu89" STD_GNU89)
SVCOMP_CHECK_C_LANG_STD("-std=gnu99" STD_GNU99)
SVCOMP_CHECK_C_LANG_STD("-std=gnu11" STD_GNU11)

# FIXME: This assumes a gcc/clang like compiler
macro(SVCOMP_CHECK_CXX_LANG_STD flag name)
  CHECK_CXX_COMPILER_FLAG("${flag}" HAS_${name})
  if (HAS_${name})
    set(SVCOMP_${name} "${flag}")
  else()
    message(WARNING "C++ standard ${name} is not supported")
  endif()
endmacro()

SVCOMP_CHECK_CXX_LANG_STD("-std=c++98" STD_CXX98)
SVCOMP_CHECK_CXX_LANG_STD("-std=c++03" STD_CXX03)
SVCOMP_CHECK_CXX_LANG_STD("-std=c++11" STD_CXX11)
SVCOMP_CHECK_CXX_LANG_STD("-std=c++14" STD_CXX14)
SVCOMP_CHECK_CXX_LANG_STD("-std=gnu++98" STD_GNUXX98)
SVCOMP_CHECK_CXX_LANG_STD("-std=gnu++03" STD_GNUXX03) # Clang 3.7 doesn't seem to support this, should we drop supporting this?
SVCOMP_CHECK_CXX_LANG_STD("-std=gnu++11" STD_GNUXX11)
SVCOMP_CHECK_CXX_LANG_STD("-std=gnu++14" STD_GNUXX14)

###############################################################################
# Detect supported warning flags
###############################################################################
# Warnings for both the C and C++ compiler
set(SVCOMP_BOTH_WARNING_FLAGS
  -Wall
  -Werror=main
  -Wformat
  -Wmain
  -Wuninitialized
  -Winit-self
)
# Warning flags for the C compiler only
set(SVCOMP_C_WARNING_FLAGS
  -Werror=implicit
  -Werror=missing-parameter-type
  )
# Warning flags for the C++ compiler only
set(SVCOMP_CXX_WARNING_FLAGS
  -Wnon-virtual-dtor
  -Woverloaded-virtual
  -Wreorder
)


# Globally set C compiler warning flags that are supported and emit
# a warning about unsupported flags
foreach (flag ${SVCOMP_BOTH_WARNING_FLAGS} ${SVCOMP_C_WARNING_FLAGS})
  SVCOMP_SANITIZE_FLAG_NAME(SANITIZED_FLAG_NAME "${flag}")
  CHECK_C_COMPILER_FLAG("${flag}" HAS_C_${SANITIZED_FLAG_NAME})
  if (HAS_C_${SANITIZED_FLAG_NAME})
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${flag}")
  else()
    message(WARNING "C compiler does not support flag \"${flag}\"")
  endif()
endforeach()

# Globally set C++ compiler warning flags that are supported and emit
# a warning about unsupported flags
foreach (flag ${SVCOMP_BOTH_WARNING_FLAGS} ${SVCOMP_CXX_WARNING_FLAGS})
  SVCOMP_SANITIZE_FLAG_NAME(SANITIZED_FLAG_NAME "${flag}")
  CHECK_CXX_COMPILER_FLAG("${flag}" HAS_CXX_${SANITIZED_FLAG_NAME})
  if (HAS_CXX_${SANITIZED_FLAG_NAME})
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${flag}")
  else()
    message(WARNING "C++ compiler does not support flag \"${flag}\"")
  endif()
endforeach()

###############################################################################
# Support building with profiling
###############################################################################
option(BUILD_WITH_PROFILING "Build benchmarks with profiling" OFF)
if (BUILD_WITH_PROFILING)
  message(STATUS "Profiling enabled")
  set(PROFILING_FLAGS
    "--coverage"
    "-I${CMAKE_SOURCE_DIR}/overrides/include"
  )
  foreach (f ${PROFILING_FLAGS})
    SVCOMP_SANITIZE_FLAG_NAME(sanitized_name "${f}")
    # HACK: The linker needs to know about the flag too
    # so pretend it's a library so it gets put in the link line.
    set(CMAKE_REQUIRED_LIBRARIES "${f}")
    CHECK_C_COMPILER_FLAG("${f}" HAS_${sanitized_name}_C)
    unset(CMAKE_REQUIRED_LIBRARIES)
    if (HAS_${sanitized_name}_C)
      set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${f}")
    else()
      message(FATAL_ERROR "C Compiler is required to support flag \"${f}\"")
    endif()
    # HACK: The linker needs to know about the flag too
    # so pretend it's a library so it gets put in the link line.
    set(CMAKE_REQUIRED_LIBRARIES "${f}")
    CHECK_CXX_COMPILER_FLAG("${f}" HAS_${sanitized_name}_CXX)
    unset(CMAKE_REQUIRED_LIBRARIES)
    if (HAS_${sanitized_name}_CXX)
      set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${f}")
    else()
      message(FATAL_ERROR "C++ Compiler is required to support flag \"${f}\"")
    endif()
  endforeach()
else()
  message(STATUS "Profiling disabled")
endif()

###############################################################################
# Detect libraries that benchmarks may depend on
###############################################################################
# Pthreads
set(CMAKE_THREAD_PREFER_PTHREAD TRUE)
list(APPEND CMAKE_MODULE_PATH "${PROJECT_SOURCE_DIR}/cmake/modules")
# HACK: We don't need OpenMP or pthreads for now so pretend we don't have
# them to speed up configure.
#find_package(Threads)
#find_package(OpenMP)
find_package(KLEENativeRuntime)

option(KLEE_NATIVE_RUNTIME_REQUIRED "Require the KLEE native runtime" ON)
if (KLEE_NATIVE_RUNTIME_REQUIRED)
	if (NOT KLEE_NATIVE_RUNTIME_FOUND)
		message(FATAL_ERROR "KLEE native runtime is required.")
	endif()
endif()

# Check if a separate C math library exists
find_library(C_MATH_LIBRARY
  NAMES libm.so libm.a # Prefer dynamic library over static library
  DOC "Separate C Math library"
)

###############################################################################
# Detect if building with wllvm
###############################################################################
if ( ${CMAKE_C_COMPILER} MATCHES "wllvm$")
  message(STATUS "C compiler is wllvm")
  if ( NOT ${CMAKE_CXX_COMPILER} MATCHES "wllvm\\+\\+$")
    message(FATAL_ERROR "CXX compiler but be wllvm++")
  endif()
  option(WLLVM_RUN_EXTRACT_BC "Automatically run extract-bc on benchmarks when building with wllvm" ON)
  if (WLLVM_RUN_EXTRACT_BC)
    # Find extract-bc
    find_program(WLLVM_EXTRACT_BC_TOOL
      NAMES extract-bc
      DOC "Path to extract-bc tool shipped with wllvm"
    )
    if (NOT WLLVM_EXTRACT_BC_TOOL)
      message(FATAL_ERROR "Could not find extract-bc tool that should be shipped with wllvm. Please add it to your path")
    else()
      message(STATUS "Found extract-bc tool: ${WLLVM_EXTRACT_BC_TOOL}")
    endif()
  endif()
endif()

###############################################################################
# Number of jobs to be used when building external projects
###############################################################################
include(ProcessorCount)
ProcessorCount(SVCB_NUMBER_OF_HOST_PROCESSORS)
message(STATUS "Host has ${SVCB_NUMBER_OF_HOST_PROCESSORS} CPU(s)")
set(EXTERNAL_PROJECT_JOBS
  "${SVCB_NUMBER_OF_HOST_PROCESSORS}"
  CACHE
  STRING
  "When building an external project if supported build with this many jobs"
)

###############################################################################
# This option will cause a corresponding YAML file to be emitted for every
# benchmark that contains the information from the original `spec.yml` file
# augmented with the location of the built executable and other information.
###############################################################################
option(EMIT_AUGMENTED_BENCHMARK_SPECIFICATION_FILES "Emit Augmented Benchmark specification files" ON)

if (EMIT_AUGMENTED_BENCHMARK_SPECIFICATION_FILES)
  # Top level target used to build augmented spec files
  add_custom_target(build-augmented-spec-files ALL)
endif()

###############################################################################
###############################################################################
define_property(GLOBAL PROPERTY SVCB_AUGMENTED_BENCHMARK_SPECIFICATION_FILES
  BRIEF_DOCS "List of augmented spec files"
  FULL_DOCS "List of augmented spec files"
)

###############################################################################
# Add add_benchmark() macro
###############################################################################
include(cmake/add_benchmark.cmake)

###############################################################################
# Runtime libraries
###############################################################################
add_subdirectory(lib)

###############################################################################
# Python tests
###############################################################################
add_custom_target(check-svcb ALL
                  COMMAND ${PYTHON_EXECUTABLE} -m unittest discover
                  WORKING_DIRECTORY "${SVCB_DIR}"
                  COMMENT "Running svcb unit tests"
                 )

###############################################################################
# Show categories
###############################################################################
add_custom_target(show-categories
                  COMMAND ${PYTHON_EXECUTABLE}
                    "${SVCB_DIR}/tools/category-count.py"
                    ${CMAKE_SOURCE_DIR}/benchmarks
                  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
                  COMMENT "Showing benchmark categories"
                 )

###############################################################################
# Show verification tasks
###############################################################################
add_custom_target(show-tasks
                  COMMAND ${PYTHON_EXECUTABLE}
                    "${SVCB_DIR}/tools/correctness-count.py"
                    "--mode"
                    "tasks"
                    ${CMAKE_SOURCE_DIR}/benchmarks
                  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
                  COMMENT "Showing verification tasks"
                 )

###############################################################################
# Show benchmark correctness summary
###############################################################################
add_custom_target(show-correctness-summary
                  COMMAND ${PYTHON_EXECUTABLE}
                    "${SVCB_DIR}/tools/correctness-count.py"
                    "--mode"
                    "benchmark"
                    ${CMAKE_SOURCE_DIR}/benchmarks
                  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
                  COMMENT "Showing benchmark correctness summary"
                 )

###############################################################################
# Benchmarks
###############################################################################
add_subdirectory(benchmarks)

###############################################################################
# Output list of augmented spec files
###############################################################################
if (EMIT_AUGMENTED_BENCHMARK_SPECIFICATION_FILES)
  get_property(list_of_augmented_spec_files
    GLOBAL PROPERTY
    SVCB_AUGMENTED_BENCHMARK_SPECIFICATION_FILES
  )
  list(SORT list_of_augmented_spec_files)
  add_custom_command(OUTPUT augmented_spec_files.txt
    COMMAND ${CMAKE_COMMAND} -E remove augmented_spec_files.txt
  )
  foreach (specfile ${list_of_augmented_spec_files})
    add_custom_command(OUTPUT augmented_spec_files.txt
      COMMAND ${CMAKE_COMMAND} -E echo
        ${specfile} >> augmented_spec_files.txt
      APPEND
    )
  endforeach()
  add_custom_target(create-augmented-spec-file-list
    DEPENDS build-augmented-spec-files augmented_spec_files.txt
  )
endif()
