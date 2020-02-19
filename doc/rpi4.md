# Rpi4 inter-cell communication setup

This documents describes how to set up the Rpi4 for inter-cell communication

## Requirements

- a custom `initramfs`
- official jailhouse kernel for Rpi4
- jailhouse built with that kernel

## Preparation

- build custom initramfs
    * get files from [Jailhouse images](https://github.com/siemens/jailhouse-images/tree/master/recipes-core/non-root-initramfs/files)
        - `overlay`
        - `arm64-config`
    * get [buildroot](https://buildroot.org/downloads/) in a version corresponding to the version stated among the first lines of `arm64-config`
    * unpack *buildroot* such that you have the folling files/directories inside your working directory
        - `buildroot-<version>`
        - `overlay`
        - `arm64-config`
    * run `cp arm64-config buildroot-<version>/.config`
    * run `cd buildroot-<version>`
    * run `make olddefconfig`
    * the path to the custom initramfs is `buildroot-<version>/output/images/rootfs.cpio`
- build jailhouse kernel for Rpi4
    * use automate to get a prebuilt kernel
- build jailhouse
    * use automate to build jailhouse
- copy files to Rpi
    * rootfs.cpio
    * tared jailhouse kernel
    * jailhouse build folder

## Setup on Rpi

- `cd jailhouse`
    * `cp hypervisor/jailhouse.bin /lib/firmware`
    * `sudo insmod drivers/jailhouse.ko`

## Setup cells and inter-cell communication

- load jailhouse kernel
~~~
sudo kexec -l /boot/vmlinuz-5.4.16 --initrd /boot/initrd.img-5.4.16 --command-line="coherent_pool=1M 8250.nr_uarts=1 cma=64M bcm2708_fb.fbwidth=0 bcm2708_fb.fbheight=0 bcm2708_fb.fbswap=1 smsc95xx.macaddr=DC:A6:32:59:87:30 vc_mem.mem_base=0x3ec00000 vc_mem.mem_size=0x40000000 net.ifnames=0 dwc_otg.lpm_enable=0 console=ttyS0,115200 console=tty1 root=LABEL=writable rootfstype=ext4 elevator=deadline rootwait fixrtc mem=768M"

sudo kexec -e
~~~
- `cd jailhouse`
    * `sudo tools/jailhouse enable configs/arm64/rpi4.cell`
    * check status: `sudo tools/jailhouse console`
- configure ivshmem provided virtual ethernet
    * get PCI device
        - run `lspci -k | grep -B 2 "ivshmemi-net"`
    * get interface name
        - run `ls /sys/bus/pci/<pci-device/net`
    * run
        - `ip addr add 192.168.19.1/24 dev <device>`
        - `ip link set dev <device> up`
    * **Important note** configure virtual ethernet device in root cell **before** starting an inmate cell
- load linux inmate
    * `sudo tools/jailhouse cell linux configs/arm64/rpi4-linux-demo.cell /boot/vmlinuz-5.4.16 -d configs/arm64/dts/inmate-rpi4.dtb -i <path-to-rootfs.cpio> -c "console=ttyS0,115200 ip=192.168.19.2"`
- run `ssh 192.168.19.2`
