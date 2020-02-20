# RPI 4

This documents describes board bring up and the rpi4 for inter-cell communication


## Installation of Ubuntu 19.10

  Follow https://ubuntu.com/download/raspberry-pi
  
## Installation of perf

Just sudo apt-get install linux-tools -y
  
## Kernel:

We provide rpi-5.3 kernel with raspberry pi patches and jailhouse-5.4 kernel with 
jailhouse patches.

### Default Kernel
   
Is built from: https://github.com/raspberrypi/linux branch rpi-5.3.y

Deployment:
   
     tar xvzf kernel-default.tar.gz
     cp -r boot /
	 cp -r lib/modules /lib/
	 cp -r lib/firmware /lib/

To update the initramfs:
   
1. Edit /etc/initramfs-tools/initramfs.conf and change MODULES= to dep
   
        MODULES=dep
   
2. Rebuild initramfs
   
        sudo update-initramfs -c -k 5.3.18 -v
  
	 
To make the kernel the default:
   
	  sudo cp /boot/vmlinuz-5.3.18 /boot/firmware/vmlinuz
	  sudo cp /boot/initrd.img-5.3.18 /boot/firmware/initrd.img
	  sudo cp /boot/dtbs/5.3.18/bcm2711-rpi-4-b.dtb /boot/firmware/bcm2711-rpi-4-b.dtb
	  
Then reboot and test
   
### Jailhouse Kernel

Is built from jailhouse patch queue 5.4.16: http://git.kiszka.org/?p=linux.git;a=shortlog;h=refs/heads/jailhouse-enabling/5.4
Using defconfig from jailhouse-images: https://github.com/siemens/jailhouse-images/blob/master/recipes-kernel/linux/files/rpi4_defconfig_5.4
   
## ARM Trusted firmware

To support kexec and jailhouse an ARM Trusted Firmware must be built.

Build steps are as follows:

    git clone https://github.com/ARM-software/arm-trusted-firmware.git
    cd arm-trusted-firmware
	make CROSS_COMPILE=/afs/wsi/es/tools/arm/gcc-linaro-7.4.1-2019.02-x86_64_aarch64-linux-gnu/bin/aarch64-linux-gnu- PLAT=rpi4 DEBUG=1
	
Then copy 'build/rpi4/debug/bl31.bin' to the boards /boot/firmware directory and
edit /boot/firmware/config.txt to include the following lines in  [all] section.

    arm_64bit=1
    device_tree_address=0x03000000
    armstub=bl31.bin
    enable_gic=1
	enable_uart=1


After successful installation the BL31 messages should apear on serial console:


    NOTICE:  BL31: v2.2(debug):v2.2-614-gfa764c8
    NOTICE:  BL31: Built : 17:41:14, Feb 10 2020
    INFO:    Changed device tree to advertise PSCI.
    INFO:    ARM GICv2 driver initialized
    INFO:    BL31: Initializing runtime services                   
	INFO:    BL31: cortex_a72: CPU workaround for 859971 was applied
	INFO:    BL31: cortex_a72: CPU workaround for cve_2017_5715 was applied
	INFO:    BL31: cortex_a72: CPU workaround for cve_2018_3639 was applied
	INFO:    BL31: Preparing for EL3 exit to normal world


For jailhouse the patches mentioned in https://github.com/siemens/jailhouse-images/blob/7c6d0ddb2763ef38a019b565568b8e9b59ca48c8/recipes-bsp/arm-trusted-firmware/files/0001-rpi3-4-Add-support-for-offlining-CPUs.patch seem no longer necessary when using the current master of arm trusted firmware. 


# Rpi4 inter-cell communication setup

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
