# Copyright (c) 2016, Daniel Liew
# This file is covered by the license in LICENSE-SVCB.txt
from . import benchmark
from . import schema
import logging
import os
import sys

_logger = logging.getLogger(__name__)

class CMakeDependencyRegisterException(Exception):
  def __init__(self, msg):
    self.message = msg

class CMakeDependencyDispatchException(Exception):
  def __init__(self, msg):
    self.message = msg

class CMakeDependencyHandlerLoadException(Exception):
  def __init__(self, msg):
    self.message = msg

class GenerateCMakeDeclsException(Exception):
  def __init__(self, msg):
    self.message = msg

# Instances of this object are just a convenient way
# of passing around information needed to emit a
# CMake decl that doesn't require clients to change
# their function signatures if we add/remove information
class CMakeDependencyAndTargetInfo(object):
  def __init__(self,
      dependencyInfo,
      targetName,
      enableTargetCMakeVariable,
      disabledTargetReasonsCMakeVariable,
      benchmarkObj,
      cmakeIndent):
    self.dependencyInfo = dependencyInfo
    assert isinstance(self.dependencyInfo, dict)
    self.targetName = targetName
    assert isinstance(self.targetName, str)
    assert len(self.targetName) > 0
    self.enableTargetCMakeVariable = enableTargetCMakeVariable
    assert isinstance(self.enableTargetCMakeVariable, str)
    assert len(self.enableTargetCMakeVariable) > 0
    self.disabledTargetReasonsCMakeVariable = disabledTargetReasonsCMakeVariable
    assert isinstance(self.disabledTargetReasonsCMakeVariable, str)
    assert len(self.disabledTargetReasonsCMakeVariable) > 0
    self.benchmarkObj = benchmarkObj
    assert isinstance(self.benchmarkObj, benchmark.Benchmark)
    self.cmakeIndent = cmakeIndent
    assert isinstance(self.cmakeIndent, str)
    assert len(self.cmakeIndent) > 0

class CMakeDependencyDispatcher(object):
  """
    Instances of this class store a mapping of depedency names
    (e.g. "pthreads") to functions that know how to emit the
    relevant CMake code to handle the dependency.
  """
  def __init__(self):
    self.handlers = dict()

  def register(self, name, fn):
    assert isinstance(name, str)
    if name in self.handlers:
      msg = '"{}" already has a registered handler'.format(name)
      _logger.error(msg)
      raise CMakeDependencyRegisterException(msg)

    # FIXME: We should check the signature of the function
    self.handlers[name] = fn

  @classmethod
  def getDefaultDispatcher(ClassObj):
    newObj = ClassObj()

    newObj.register('pthreads', generate_pthreads_dependency_code)
    newObj.register('openmp', generate_openmp_dependency_code)
    newObj.register('klee_runtime', generate_klee_runtime_dependency_code)
    newObj.register('svcomp_klee_runtime', generate_svcomp_klee_runtime_dependency_code)
    newObj.register('cmath', generate_cmath_dependency_code)
    newObj.register('gsl', generate_gsl_dependency_code)

    return newObj

  def loadHandlerFromFile(self, filePath):
    # HACK: use reference type so `handlerCalled` can be modifed by `registerFunction`
    # and have its changes be visible
    handlerCalled = [False]
    def registerFunction(name, fn):
      self.register(name, fn)
      handlerCalled[0] = True
      return None

    # Provide a simple global environment
    g = {'register_handler': registerFunction }
    l = {}
    c = None
    try:
      if sys.version_info >= (3,):
        with open(filePath, 'r') as f:
          c = compile(f.read(), filePath, 'exec')
          # YUCK: Python 2.7.6 complains about `exec(c,g,l)` being present in the code
          # even if it would never be executed so hack around this by using `eval()`.
          eval('exec(c,g,l)')
      else:
        execfile(filePath, g, l)
    except SyntaxError as e:
      msg = "Syntax error: {}:{}:{}\n".format(e.filename, e.lineno, e.offset)
      msg += e.text.strip() + "\n"
      msg += " "*(e.offset - 1) + "^" # Hack carret style diagnoistc
      _logger.error(msg)
      raise CMakeDependencyHandlerLoadException(msg)

    if not handlerCalled[0]:
      msg = 'Dependency handler not registered by code in "{}"'.format(filePath)
      _logger.error(msg)
      raise CMakeDependencyHandlerLoadException(msg)
    return

  def getDeclsFor(self, dependencyName, cmakeDepInfo):
    """
    Returns a tuple (preGuardCode, inGuardCode)
    """
    assert(isinstance(dependencyName, str))
    assert(isinstance(cmakeDepInfo, CMakeDependencyAndTargetInfo))

    # Look for a handler
    handler = None
    try:
      handler = self.handlers[dependencyName]
    except KeyError as e:
      msg = 'CMake Dependency "{}" has no handler'.format(dependencyName)
      _logger.error(msg)
      raise CMakeDependencyDispatchException(msg)

    # Invoke the handler
    result = handler(cmakeDepInfo)

    # Sanity check the results
    if not isinstance(result, tuple):
      msg = 'Handler for dependency "{}" did not return a tuple'.format(dependencyName)
      _logger.error(msg)
      raise CMakeDependencyRegisterException(msg)

    if len(result) != 2:
      msg = 'Handler for dependency "{}" did not return a tuple with two elements'.format(dependencyName)
      _logger.error(msg)
      raise CMakeDependencyRegisterException(msg)

    for index in range(0,2):
      if not isinstance(result[index], str):
        msg = 'The element at index {} in the tuple returned by the handler for dependency "{}" should be a string'.format(index, dependencyName)
        _logger.error(msg)
        raise CMakeDependencyRegisterException(msg)

    return result

cmakeIndent = "  "
def generateCMakeDecls(benchmarkObjs, sourceRootDir, supportedArchitecture, dependencyDispatcher, coverage):
  """
    Returns a string containing CMake declarations
    that declare the benchmarks in the list ``benchmarkObjs``.
  """
  assert isinstance(benchmarkObjs, list)
  assert os.path.exists(sourceRootDir)
  assert os.path.isdir(sourceRootDir)

  if not isinstance(dependencyDispatcher, CMakeDependencyDispatcher):
    msg = "Provided `dependencyDispatcher` is not an instance of CMakeDependencyDispatcher"
    _logger.error(msg)
    raise GenerateCMakeDeclsException(msg)

  declStr = "# Autogenerated. DO NOT MODIFY!\n"

  # CMake Variable to hold list of targets. This exists so the build system
  # can easily iterate through the declared targets.
  declStr += "set(_benchmark_targets \"\")\n"

  for b in benchmarkObjs:
    assert isinstance(b.name, str)
    assert isinstance(b, benchmark.Benchmark)

    benchmarkArchitectures = None
    if isinstance(b.architectures, str):
      assert b.architectures == 'any'
      benchmarkArchitectures = {'any'}
    else:
      benchmarkArchitectures = b.architectures

    for arch in benchmarkArchitectures:
      targetName = '{}.{}'.format(b.name, arch)
      declStr += "### BEGIN target {targetName} ####\n".format(targetName=targetName)
      if arch != 'any' and arch != supportedArchitecture:
        # Architecture not supported
        declStr += 'message(STATUS "Compiler cannot build target {}. Architecture not supported by compiler")\n'.format(targetName)
        continue

      # Emit code that can be used by dependencies to prevent generaton of the target.
      # This is useful if a library required is not available.
      enableTargetCMakeVariable = "ENABLE_TARGET_{}".format(b.name.upper())
      declStr += "set({} TRUE)\n".format(enableTargetCMakeVariable)
      disabledTargetReasonsCMakeVariable = "DISABLED_TARGET_REASONS"
      declStr += "set({} \"\")\n".format(disabledTargetReasonsCMakeVariable)

      dependencyHandlingCMakeDecls = generate_dependency_decls(b, targetName, enableTargetCMakeVariable, disabledTargetReasonsCMakeVariable, dependencyDispatcher)

      # Emit dependency code that may change guard on executable
      for (guardDecl, _) in dependencyHandlingCMakeDecls:
        declStr += guardDecl

      # Emit code that can disable building the benchmark if the language
      # version is not supported
      lang_ver = b.language.replace('+','X').upper()
      declStr += """
if (NOT HAS_STD_{lang_ver})
{indent}set({enableTargetCMakeVariable} FALSE)
{indent}list(APPEND {disabledTargetReasonsCMakeVariable} "Compiler does not support language standard {lang_ver}")
endif()
  \n""".format(
      lang_ver=lang_ver,
      enableTargetCMakeVariable=enableTargetCMakeVariable,
      disabledTargetReasonsCMakeVariable=disabledTargetReasonsCMakeVariable,
      indent=cmakeIndent)

      # Emit guard
      declStr += "if ({})\n".format(enableTargetCMakeVariable)
      # Emit ``add_executable()``
      declStr += "{indent}add_executable({target_name}\n".format(indent=cmakeIndent, target_name=targetName)
      # FIXME: Need to put in absolute path
      for source in b.sources:
        declStr += "{indent}{indent}{source_file}\n".format(indent=cmakeIndent, source_file=os.path.join(sourceRootDir, source))
      # HACK: Emit svcomp_klee_runtime object files here if needed. We should use the `target_sources()` CMake
      # command but only CMake >= 3.1 support this.
      svcomp_klee_runtime_dependency = [ (name,info) for (name, info) in b.dependencies.items() if name == "svcomp_klee_runtime"]
      assert(len(svcomp_klee_runtime_dependency) <= 1)
      if len(svcomp_klee_runtime_dependency) == 1:
        declStr += "{indent}{indent}$<TARGET_OBJECTS:svcomp_klee_runtime>\n".format(indent=cmakeIndent)
      declStr += "{indent})\n".format(indent=cmakeIndent)

      if len(b.defines) > 0:
        declStr += "{indent}target_compile_definitions({target_name} PRIVATE\n".format(
          indent=cmakeIndent,
          target_name=targetName)
        for (macroName,macroValue) in b.defines.items():
          assert isinstance(macroName, str)
          if macroValue != None:
            declStr += "  {}={}\n".format(macroName, macroValue)
          else:
            declStr += "  {}\n".format(macroName)
        declStr += ")\n"
      # Emit compiler flags
      if coverage:
        declStr += "{indent}target_compile_options({target_name} PRIVATE ${{SVCOMP_STD_{lang_ver}}} \"-fprofile-dir={profile_dir}.cov\")\n".format(
          indent = cmakeIndent,
          target_name = targetName,
          lang_ver = lang_ver,
          profile_dir = targetName
        )
      else:
        declStr += "{indent}target_compile_options({target_name} PRIVATE ${{SVCOMP_STD_{lang_ver}}})\n".format(
          indent = cmakeIndent,
          target_name = targetName,
          lang_ver = lang_ver
        )

      # Emit dependency code that adds necessary dependencies to that target
      for (_, depAddDecl) in dependencyHandlingCMakeDecls:
        declStr += depAddDecl

      # Add target to list of targets
      declStr += "list(APPEND _benchmark_targets {targetName})".format(targetName=targetName)

      # Close guard
      declStr += """
else()
{indent}set(msgConcat "")
{indent}foreach (msg ${{DISABLED_TARGET_REASONS}})
{indent}{indent}set(msgConcat "${{msgConcat}}\\n  ${{msg}}")
{indent}endforeach()
{indent}message(WARNING "Not building target {target} due to ${{msgConcat}}")
{indent}unset(msgConcat)
endif()
      \n""".format(indent=cmakeIndent, target=targetName)
  return declStr

def generate_dependency_decls(benchmarkObj, targetName, enableTargetCMakeVariable, disabledTargetReasonsCMakeVariable, dependencyDispatcher):
  """
    Returns a list of tuples [(preGuardCode, inGuardCode)]
  """
  decls = []
  for depName, info in benchmarkObj.dependencies.items():
    depInfo = CMakeDependencyAndTargetInfo(
        dependencyInfo=info,
        targetName=targetName,
        enableTargetCMakeVariable=enableTargetCMakeVariable,
        disabledTargetReasonsCMakeVariable=disabledTargetReasonsCMakeVariable,
        benchmarkObj=benchmarkObj,
        cmakeIndent=cmakeIndent
    )
    # This indirection to call the right functions to emit the CMake
    # code exists so we can support out of tree dependencies.
    decl = dependencyDispatcher.getDeclsFor(depName, depInfo)
    decls.append(decl)
  return decls

def generate_pthreads_dependency_code(depInfo):
  # Unpack the needed information
  assert isinstance(depInfo, CMakeDependencyAndTargetInfo)
  info = depInfo.dependencyInfo
  targetName = depInfo.targetName
  enableTargetCMakeVariable = depInfo.enableTargetCMakeVariable
  disabledTargetReasonsCMakeVariable = depInfo.disabledTargetReasonsCMakeVariable

  # This guardDecl works in cooperation with find_package(Threads)
  guardDecl = """
if (NOT CMAKE_USE_PTHREADS_INIT)
{indent}set({enableTargetCMakeVariable} FALSE)
{indent}list(APPEND {disabledTargetReasonsCMakeVariable} "Pthreads library not available")
endif()
  \n""".format(enableTargetCMakeVariable=enableTargetCMakeVariable,
      disabledTargetReasonsCMakeVariable=disabledTargetReasonsCMakeVariable,
      indent=cmakeIndent)
  addDepDecl = "{indent}target_link_libraries({targetName} PRIVATE ${{CMAKE_THREAD_LIBS_INIT}})\n".format(indent=cmakeIndent, targetName=targetName)
  return (guardDecl, addDepDecl)

def generate_openmp_dependency_code(info, targetName, enableTargetCMakeVariable, disabledTargetReasonsCMakeVariable, benchmarkObj):
  guardDecl = """
if (NOT OPENMP_FOUND)
{indent}set({enableTargetCMakeVariable} FALSE)
{indent}list(APPEND {disabledTargetReasonsCMakeVariable} "OpenMP not available")
endif()
  \n""".format(enableTargetCMakeVariable=enableTargetCMakeVariable,
      disabledTargetReasonsCMakeVariable=disabledTargetReasonsCMakeVariable,
      indent=cmakeIndent)

  addDepDecl=""
  if benchmarkObj.isLanguageC():
    addDepDecl += "{indent}target_compile_options({targetName} PRIVATE ${{OpenMP_C_FLAGS}})\n".format(indent=cmakeIndent, targetName=targetName)
    addDepDecl += "{indent}set_property(TARGET {targetName} APPEND_STRING PROPERTY LINK_FLAGS \" ${{OpenMP_C_FLAGS}}\")\n".format(targetName=targetName, indent=cmakeIndent)
  elif benchmarkObj.isLanguageCXX():
    addDepDecl += "{indent}target_compile_options({targetName} PRIVATE ${{OpenMP_CXX_FLAGS}})\n".format(indent=cmakeIndent, targetName=targetName)
    addDepDecl += "{indent}set_property(TARGET {targetName} APPEND_STRING PROPERTY LINK_FLAGS \" ${{OpenMP_CXX_FLAGS}}\")\n".format(targetName=targetName, indent=cmakeIndent)
  else:
    _logger.error("Unknown benchmark language")
    raise Exception("Unknown benchmark language")
  return (guardDecl, addDepDecl)

def generate_klee_runtime_dependency_code(depInfo):
  # Unpack the needed information
  assert isinstance(depInfo, CMakeDependencyAndTargetInfo)
  info = depInfo.dependencyInfo
  targetName = depInfo.targetName
  enableTargetCMakeVariable = depInfo.enableTargetCMakeVariable
  disabledTargetReasonsCMakeVariable = depInfo.disabledTargetReasonsCMakeVariable

  guardDecl = """
if (NOT KLEE_NATIVE_RUNTIME_FOUND)
{indent}set({enableTargetCMakeVariable} FALSE)
{indent}list(APPEND {disabledTargetReasonsCMakeVariable} "KLEE runtime not available")
endif()
  \n""".format(enableTargetCMakeVariable=enableTargetCMakeVariable,
      disabledTargetReasonsCMakeVariable=disabledTargetReasonsCMakeVariable,
      indent=cmakeIndent)
  addDepDecl = "{indent}target_include_directories({targetName} PRIVATE ${{KLEE_NATIVE_RUNTIME_INCLUDE_DIR}})\n".format(indent=cmakeIndent, targetName=targetName)
  addDepDecl += "{indent}target_link_libraries({targetName} PRIVATE ${{KLEE_NATIVE_RUNTIME_LIB}})\n".format(indent=cmakeIndent, targetName=targetName)
  return (guardDecl, addDepDecl)

def generate_svcomp_klee_runtime_dependency_code(depInfo):
  # Unpack the needed information
  assert isinstance(depInfo, CMakeDependencyAndTargetInfo)
  info = depInfo.dependencyInfo
  targetName = depInfo.targetName
  enableTargetCMakeVariable = depInfo.enableTargetCMakeVariable
  disabledTargetReasonsCMakeVariable = depInfo.disabledTargetReasonsCMakeVariable

  guardDecl = """
if (NOT KLEE_NATIVE_RUNTIME_FOUND)
{indent}set({enableTargetCMakeVariable} FALSE)
{indent}list(APPEND {disabledTargetReasonsCMakeVariable} "KLEE runtime not available")
endif()
  \n""".format(enableTargetCMakeVariable=enableTargetCMakeVariable,
      disabledTargetReasonsCMakeVariable=disabledTargetReasonsCMakeVariable,
      indent=cmakeIndent)
  addDepDecl = "{indent}target_link_libraries({targetName} PRIVATE ${{KLEE_NATIVE_RUNTIME_LIB}})\n".format(indent=cmakeIndent, targetName=targetName)
  # svcomp_klee_runtime is an OBJECT library so we can't use `target_link_libraries`.
  # FIXME: We should use `target_sources()` here but that isn't available in CMake >= 3.1.
  # HACK: We add `$<TARGET_OBJECTS:svcomp_klee_runtime>` elsewhere.
  return (guardDecl, addDepDecl)

def generate_cmath_dependency_code(depInfo):
  # Unpack the needed information
  assert isinstance(depInfo, CMakeDependencyAndTargetInfo)
  info = depInfo.dependencyInfo
  targetName = depInfo.targetName
  enableTargetCMakeVariable = depInfo.enableTargetCMakeVariable
  disabledTargetReasonsCMakeVariable = depInfo.disabledTargetReasonsCMakeVariable

  addDepDecl = """
{indent}if (C_MATH_LIBRARY)
{indent}{indent}target_link_libraries({targetName} PRIVATE ${{C_MATH_LIBRARY}})
{indent}endif()
  \n""".format(indent=cmakeIndent, targetName=targetName)

  return ("", addDepDecl)

def generate_gsl_dependency_code(depInfo):
  # Unpack the needed information
  assert isinstance(depInfo, CMakeDependencyAndTargetInfo)
  info = depInfo.dependencyInfo
  targetName = depInfo.targetName
  enableTargetCMakeVariable = depInfo.enableTargetCMakeVariable
  disabledTargetReasonsCMakeVariable = depInfo.disabledTargetReasonsCMakeVariable

  # FIXME: Rename GSL to clearer name once benchmarks are public
  guardDecl = """
if (NOT GSL_AVAILABLE)
{indent}set({enableTargetCMakeVariable} FALSE)
{indent}list(APPEND {disabledTargetReasonsCMakeVariable} "GSL not available")
endif()
  \n""".format(enableTargetCMakeVariable=enableTargetCMakeVariable,
      disabledTargetReasonsCMakeVariable=disabledTargetReasonsCMakeVariable,
      indent=cmakeIndent)
  # Want to use as system path so the include is used in preference to anything in the host's include directory
  addDepDecl = "{indent}target_include_directories({targetName} SYSTEM BEFORE PRIVATE ${{GSL_INCLUDE_DIR}})\n".format(indent=cmakeIndent, targetName=targetName)
  addDepDecl += "{indent}target_link_libraries({targetName} PRIVATE ${{GSL_LIBS}} ${{C_MATH_LIBRARY}})\n".format(indent=cmakeIndent, targetName=targetName)
  return (guardDecl, addDepDecl)
