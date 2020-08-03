# Usage

To prepare an autojail build you need the kernel build directory for the target board preferably a kernel with jailhouse specific extensions
from http://git.kiszka.org/?p=linux.git;a=summary , and a checkout of the jailhouse source code.

Autojail provides the following command line interface:

## autojail init

Initializes an autojail project in the current working directory.

By default this command uses an interactive intialization non interactive initializarion can
be forced by using parameter _-n_. In non-interactive mode most default configuration paramters can be overwritten
using commandline arguments.

## autojail extract

Builds basic configuration data from the boards runtime system.
In normal mode the target board is connected via ssh. This assumes working ssh public key authentication
to a sudo capable account on the target board. If this is not possible the runtime system files can be
extracted manually, and the location of the files is given by command line parameter _-b/--base-folder_ .

To show detailed information about the extracted board information use _-v_ to activate verbose output.

## autojail config

This command builds the configured cell configuration for root and guest cell.

A configuration file cells.yml must provided in the project directory. For a description
of the documentation format see: [Configuration File Format](config_format.md)

To show detailed information about the generated configurations use _-v_ to activate
verbose output.
