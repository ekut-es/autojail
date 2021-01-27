obj-m += extract-clocks.o

KDIR ?= /lib/modules/$(shell uname -r)/build

all:
	make -C $(KDIR) M=${CURDIR} modules
 
clean:
	make -C $(KDIR) M=${CURDIR} clean