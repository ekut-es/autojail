#!/bin/bash

function get_script_dir()
{
    local prg=$0
    if [ ! -e "$prg" ]; then
        case $prg in
        (*/*) exit 1;;
    (*) prg=$(command -v -- "$prg") || exit;;
    esac
    fi
    local dir=$(
        cd -P -- "$(dirname -- "$prg")" && pwd -P
    ) || exit
    
    script_dir=$dir
}

get_script_dir
downloads_path="${script_dir}/../downloads/"

if [ ! -d ${downloads_path} ]; then
    mkdir -p ${downloads_path}
fi

INITRD_URL=https://atreus.informatik.uni-tuebingen.de/seafile/f/827fb5d90a4040f98794/?dl=1
VMLINUZ_URL=https://atreus.informatik.uni-tuebingen.de/seafile/f/998f76ccd65e4fffa581/?dl=1
ROOTFS_URL=https://atreus.informatik.uni-tuebingen.de/seafile/f/8760e85c366a42eca26a/?dl=1
KERNEL_URL=https://atreus.informatik.uni-tuebingen.de/seafile/f/dfc7fc6ac5ce4b27bc18/?dl=1

mkdir -p ${downloads_path}/qemu
if [ ! -f ${downloads_path}/qemu/initrd.img ]; then
    wget -c ${INITRD_URL} -O ${downloads_path}/qemu/initrd.img
fi
if [ ! -f ${downloads_path}/qemu/vmlinuz ]; then
    wget -c ${VMLINUZ_URL} -O ${downloads_path}/qemu/vmlinuz
fi
if [ ! -f ${downloads_path}/qemu/rootfs.img ]; then
    wget -c ${ROOTFS_URL} -O ${downloads_path}/qemu/rootfs.img
fi
if [ ! -f ${downloads_path}/qemu/linux-jailhouse-images.tar.bz ]; then
    wget -c ${KERNEL_URL} -O ${downloads_path}/qemu/linux-jailhouse-images.tar.bz
    pushd ${downloads_path}/qemu
    tar xJf linux-jailhouse-images.tar.bz
    popd
fi

rm -fr qemu
mkdir qemu

QEMU=qemu-system-aarch64
QEMU_EXTRA_ARGS=" \
-cpu cortex-a57 \
-smp 16 \
-machine virt,gic-version=3,virtualization=on \
-device virtio-serial-device \
-chardev socket,id=serial0,path=qemu/serial0.sock,server,nowait,logfile=qemu/serial0.log \
-serial chardev:serial0 \
-chardev socket,id=monitor,path=qemu/monitor.sock,server,nowait,logfile=qemu/monitor.log \
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
-drive file=${downloads_path}/qemu/rootfs.img,discard=unmap,if=none,id=disk,format=raw \
-m 4G -netdev user,id=net,hostfwd=tcp::2222-:22 \
-kernel ${downloads_path}/qemu/vmlinuz -append "${KERNEL_CMDLINE}" \
-initrd ${downloads_path}/qemu/initrd.img ${QEMU_EXTRA_ARGS} "$@" &

for i in {0..10}
do
    if [ ! -f qemu/serial0.log ]; then
        sleep 2;
    fi
done

if [ ! -f qemu/serial0.log ]; then
    echo "Failed to start qemu. Exiting..."
    exit -1
fi

tail -f qemu/serial0.log &
boot_pid=$!
grep -m1 "Jailhouse Demo Image (login: root/root)" < <(stdbuf -oL tail -f qemu/serial0.log)
kill $boot_pid

popd

#if [ -f $(which socat) ]; then
#	socat qemu/serial0.sock -
#fi
