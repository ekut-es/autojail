#!/bin/bash

INITRD_URL=https://atreus.informatik.uni-tuebingen.de/seafile/f/827fb5d90a4040f98794/?dl=1
VMLINUZ_URL=https://atreus.informatik.uni-tuebingen.de/seafile/f/998f76ccd65e4fffa581/
ROOTFS_URL=https://atreus.informatik.uni-tuebingen.de/seafile/f/8760e85c366a42eca26a/?dl=1
KERNEL_URL=https://atreus.informatik.uni-tuebingen.de/seafile/f/dfc7fc6ac5ce4b27bc18/?dl=1

mkdir -p qemu
if [ ! -f qemu/initrd.img ]; then
  wget -c ${INITRD_URL} -O qemu/initrd.img
fi
if [ ! -f qemu/vmlinuz ]; then 
  wget -c ${VMLINUZ_URL} -O qemu/vmlinuz 
fi
if [ ! -f qemu/rootfs.img ]; then 
  wget -c ${ROOTFS_URL} -O qemu/rootfs.img
fi
if [ ! -f qemu/linux-jailhouse-images.tar.bz ]; then
  wget -c ${KERNEL_URL} -O qemu/linux-jailhouse-images.tar.bz
  pushd qemu
  tar xvJf linux-jailhouse-images.tar.bz
  popd
fi


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

if [ -e qemu/monitor.sock ]; then 
	echo ""
	echo "Qemu seems to be already started"
	echo "If qemu is not running run 'rm qemu/monitor.sock'"
	exit 0 
fi

${QEMU_PATH}${QEMU} \
    -nographic \
	-drive file=qemu/rootfs.img,discard=unmap,if=none,id=disk,format=raw \
	-m 4G -netdev user,id=net,hostfwd=tcp::2222-:22 \
	-kernel qemu/vmlinuz -append "${KERNEL_CMDLINE}" \
	-initrd qemu/initrd.img ${QEMU_EXTRA_ARGS} "$@" &

sleep 60
#if [ -f $(which socat) ]; then
#	socat qemu/serial0.sock - 
#fi
