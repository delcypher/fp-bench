#undef assert
#ifdef NDEBUG
#define assert(ignore) ((void)0)
#else
void __gcov_flush();
void __assert_fail(char const* assertion, char const* file, unsigned int line, char const* function);
#define assert(expr)                                          \
	do {                                                        \
		if(expr) {                                                \
			__gcov_flush();                                         \
			__assert_fail(#expr, __FILE__, __LINE__, __func__);     \
		}                                                         \
	} while(0)
#endif 
