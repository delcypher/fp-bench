/* Copyright (c) 2016, Daniel Liew
   This file is covered by the license in LICENSE-SVCB.txt
*/

// This provides a basic implementation of the SV-COMP
// runtime functions that calls into KLEE's runtime functions.
#include "svcomp/svcomp.h"
#include "klee/klee.h"
#include <assert.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define SVCOMP_NONDET_DEFN_D(NAME,T) \
T __VERIFIER_nondet_ ## NAME() { \
  static uint64_t counter = 0; \
  char name[] = "symbolic_xxxxxxxxxxxxxxxxxxxx_TTTTTTTT"; \
  const char typeName[] = #NAME ;\
  static_assert(sizeof(typeName) <= (8 + 1), "Not enough space allocated for name"); \
  char* offsetStr = name + 9; \
  sprintf(offsetStr, "%" PRIu64 "_%s", counter, typeName); \
  T initialValue; \
  klee_make_symbolic(&initialValue, sizeof(T), name); \
  return initialValue; \
}

#define SVCOMP_NONDET_DEFN(NAME) SVCOMP_NONDET_DEFN_D(NAME, NAME)

SVCOMP_NONDET_DEFN_D(bool,_Bool)
SVCOMP_NONDET_DEFN(char)
SVCOMP_NONDET_DEFN(double)
SVCOMP_NONDET_DEFN(float)
SVCOMP_NONDET_DEFN(int)
SVCOMP_NONDET_DEFN(long)
//SVCOMP_NONDET_DEFN(loff_t)
SVCOMP_NONDET_DEFN_D(pointer,void*)
SVCOMP_NONDET_DEFN_D(pchar,char*)
//SVCOMP_NONDET_DEFN(pthread_t)
//SVCOMP_NONDET_DEFN(sector_t)
SVCOMP_NONDET_DEFN(short)
SVCOMP_NONDET_DEFN(size_t)
SVCOMP_NONDET_DEFN_D(u32, uint32_t)
SVCOMP_NONDET_DEFN_D(uchar,unsigned char)
SVCOMP_NONDET_DEFN_D(uint, unsigned int)
SVCOMP_NONDET_DEFN_D(ulong, unsigned long)
SVCOMP_NONDET_DEFN(unsigned)
SVCOMP_NONDET_DEFN_D(ushort, unsigned short)

void __VERIFIER_assume(int expression) {
  klee_assume(expression);
}

// FIXME: We can probably do better than this
void __VERIFIER_atomic_begin() {
  fprintf(stderr, "__VERIFIER_atomic_begin() is a no-op\n");
}

// FIXME: We can probably do better than this
void __VERIFIER_atomic_end() {
  fprintf(stderr, "__VERIFIER_atomic_end() is a no-op\n");
}
