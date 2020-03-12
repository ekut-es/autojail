#!/bin/bash

if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "Could not detect virtual environment"
    echo "Please run 'poetry shell' first"
    exit -1 
fi

if [ ! -d dtc ] ; then
    git clone git://git.kernel.org/pub/scm/utils/dtc/dtc.git
fi

cd dtc
make
make install PREFIX=${VIRTUAL_ENV} V=1 

