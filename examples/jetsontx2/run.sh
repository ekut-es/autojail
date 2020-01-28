#!/bin/bash -e 

BOARD=jetsontx2

script_path="`dirname \"$0\"`"

pushd "${script_path}/../../"

automate-run update
cp -r configs jailhouse
automate-run build -b $BOARD
automate-run deploy -b $BOARD

automate board.lock $BOARD
automate board.reboot $BOARD --wait

automate board.kexec $BOARD --append="mem=7808M vmalloc=512M"
automate board.run $BOARD "sudo insmod jailhouse/driver/jailhouse.ko"
automate board.run $BOARD "sudo jailhouse/tools/jailhouse enable jailhouse/configs/arm64/jetson-tx2.cell"
automate board.run $BOARD "sudo jailhouse/tools/jailhouse cell create jailhouse/configs/arm64/jetson-tx2-inmate-demo.cell"
automate board.run $BOARD "sudo jailhouse/tools/jailhouse cell load 1 jailhouse/inmates/demos/arm64/gic-demo.bin"
automate board.run $BOARD "sudo jailhouse/tools/jailhouse cell start 1"
automate board.run $BOARD "sudo jailhouse/tools/jailhouse cell list"

read -p "Press enter to stop jailhouse and reboot the board"

automate board.reboot $BOARD
automate board.unlock $BOARD
