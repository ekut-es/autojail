#!/bin/bash

INITRD_URL=https://atreus.informatik.uni-tuebingen.de/seafile/f/827fb5d90a4040f98794/?dl=1
VMLINUZ_URL=https://atreus.informatik.uni-tuebingen.de/seafile/f/998f76ccd65e4fffa581/?dl=1
ROOTFS_URL=https://atreus.informatik.uni-tuebingen.de/seafile/f/8760e85c366a42eca26a/?dl=1

mkdir -p qemu
wget -c ${INITRD_URL} -O qemu/initrd.img 
wget -c ${VMLINUZ_URL} -O qemu/vmlinuz 
wget -c ${ROOTFS_URL} -O qemu/rootfs.img


QEMU=qemu-system-aarch64
QEMU_EXTRA_ARGS=" \
			-cpu cortex-a57 \
			-smp 16 \
			-machine virt,gic-version=3,virtualization=on \
			-device virtio-serial-device \
			-chardev socket,id=serial0,path=qemu/serial0.sock,server,nowait \
            -serial chardev:serial0 \
            -chardev socket,id=monitor,path=qemu/monitor.sock,server,nowait \
            -monitor chardev:monitor \
			-device virtio-blk-device,drive=disk \
			-device virtio-net-device,netdev=net"
KERNEL_CMDLINE=" \
			root=/dev/vda mem=768M"



${QEMU_PATH}${QEMU} \
    -nographic \
	-drive file=qemu/rootfs.img,discard=unmap,if=none,id=disk,format=raw \
	-m 4G -netdev user,id=net,hostfwd=tcp::2222-:22 \
	-kernel qemu/vmlinuz -append "${KERNEL_CMDLINE}" \
	-initrd qemu/initrd.img ${QEMU_EXTRA_ARGS} "$@"

