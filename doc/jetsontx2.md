# Jetson TX2

An adopted jailhouse config is available in *configs/arm64/jetson-tx2.c*

This cellconfig adds support for running jailhouse on the denver cores
and includes the following adjustments for the memory regions:

- UART: add rootshared
- Add Hypervisor memory region (might not be necessary)
- Fixes location of persistent memory


# Usage example

An automate based example commandline is provided in:

examples/jetsontx2
