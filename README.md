# Automated Jailhouse configuration ARM and ARM64 based devices

## Requirements 

1. Linux Kernel build and source directory for the target board
2. checkout of the jailhouse source code
3. cross compiler installation for the target board
4. working device tree compiler (*dtc*) installation
 

## Getting started

To install the package in development mode:

    git clone git@atreus.informatik.uni-tuebingen.de:ties/autojailhouse/autojail.git
    cd autojail
    pip3 install poetry --user
    poetry install
    poetry shell

To start the documentation browser use:

    mkdocs serve

To generate a new autojail project use: 
    
    mkdir project
    cd project
    autojail init
