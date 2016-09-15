# Copyright (c) 2016, Daniel Liew
# This file is covered by the license in LICENSE-SVCB.txt

# List of additional files that generation of target
# include files should depend on. This ensures that if these
# files change the files containing the benchmark targets
# get regenerated (i.e. OUTPUT_FILE in add_svcomp_benchmark())
set(SVCOMP_ADDITIONAL_GEN_CMAKE_INC_DEPS
  "${SVCB_DIR}/svcb/benchmark.py"
  "${SVCB_DIR}/svcb/build.py"
  "${SVCB_DIR}/svcb/schema.py"
  "${SVCB_DIR}/svcb/schema.yml"
  "${SVCB_DIR}/svcb/util.py"
  "${SVCB_DIR}/tools/svcb-emit-cmake-decls.py"
)

macro(add_benchmark BENCHMARK_DIR)
  set(INPUT_FILE ${CMAKE_CURRENT_SOURCE_DIR}/${BENCHMARK_DIR}/spec.yml)
  set(OUTPUT_FILE ${CMAKE_CURRENT_BINARY_DIR}/${BENCHMARK_DIR}_targets.cmake)
  # Only re-generate the file if necessary so that re-configure is as fast as possible
  set(_should_force_regen FALSE)
  foreach (dep ${SVCOMP_ADDITIONAL_GEN_CMAKE_INC_DEPS})
    if (NOT EXISTS "${dep}")
      message(FATAL_ERROR "Dependency \"${dep}\" does not exist")
    endif()
    if ("${dep}" IS_NEWER_THAN "${OUTPUT_FILE}")
      set(_should_force_regen TRUE)
    endif()
  endforeach()
  if (("${INPUT_FILE}" IS_NEWER_THAN "${OUTPUT_FILE}") OR ${_should_force_regen})
    message(STATUS "Generating \"${OUTPUT_FILE}\"")
    get_filename_component(OUTPUT_DIR "${OUTPUT_FILE}" DIRECTORY)
    file(MAKE_DIRECTORY ${OUTPUT_DIR})
    execute_process(COMMAND ${PYTHON_EXECUTABLE} "${SVCB_DIR}/tools/svcb-emit-cmake-decls.py"
                            ${INPUT_FILE}
                            --architecture ${SVCOMP_ARCHITECTURE}
                            --output ${OUTPUT_FILE}
                    RESULT_VARIABLE RESULT_CODE
                   )
    if (NOT ${RESULT_CODE} EQUAL 0)
      # Remove the generated output file because it is broken and if we don't
      # the next time configure runs it will succeed.
      file(REMOVE "${OUTPUT_FILE}")
      message(FATAL_ERROR "Failed to process benchmark ${BENCHMARK_DIR}. With error ${RESULT_CODE}")
    endif()
  endif()
  # Include the generated file
  include(${OUTPUT_FILE})
  # Let CMake know that configuration depends on the benchmark specification file
  set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${INPUT_FILE}")
  foreach (dep ${SVCOMP_ADDITIONAL_GEN_CMAKE_INC_DEPS})
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${dep}")
  endforeach()
  unset(_should_force_regen)
endmacro()
