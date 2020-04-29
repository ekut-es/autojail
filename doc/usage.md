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

## autojail config

This command builds the configured cell configuration for root and guest cell.
For this purpose, it builds a guest cell configuration for each guest cell.
