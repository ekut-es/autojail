#!/bin/bash


if [ ! -d dtc ] ; then
    git clone git://git.kernel.org/pub/scm/utils/dtc/dtc.git
fi

cd dtc
make
make install PREFIX=${VIRTUAL_ENV} V=1 

