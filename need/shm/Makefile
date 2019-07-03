
OBJS=EnforcerSharedMem.o ManagerSharedMem.o
HEADERS=utils.h functions.h definitions.h structures.h

CC=gcc
#We compile without optimizations because we have observed a bug even with -O2. In the function
#destination_create(), with -O2 or -O3, the compiled code assumes we are passing 3 ints and 2 floats,
#even though we of course pass 2 ints and 3 floats.
#LL based on comments + analysis by JN
CFLAGS = -O0 -fPIC -I./libutc/include -I ./libutc/ip/  -I./libutc/include/uapi -I./libutc/tc/
LDFLAGS= -shared -ldl -lm


all: clean clean-libs EnforcerSharedMem.so ManagerSharedMem.so clean


ManagerSharedMem.so:
	gcc -c -Wall -fpic $(HEADERS) ManagerSharedMem.c
# 	$(CC) -o $@ -shared $(OBJS) $(LDLIBS) -lm
# 	#objcopy --strip-all --keep-symbols=exported.sym $@ $@
	gcc -shared ManagerSharedMem.o -o ManagerSharedMem.so -lrt
	rm -f ./*.o


EnforcerSharedMem.so:
	gcc -c -Wall -fpic $(HEADERS) EnforcerSharedMem.c
# 	$(CC) -o $@ -shared $(OBJS) $(LDLIBS) -lm
# 	#objcopy --strip-all --keep-symbols=exported.sym $@ $@
	gcc -shared EnforcerSharedMem.o -o EnforcerSharedMem.so -lrt
	rm -f ./*.o


test: test.c
	gcc -g -o $@ $^ -ldl


#######################################
# 	CLEAN
#######################################
clean:
	-rm -f ./*.o
	-rm -f ./*.a
	-rm -f ./*.gch
	-rm -f ./test

clean-libs: clean
	-rm -f ./*.so

