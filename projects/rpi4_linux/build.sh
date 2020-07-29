#!/bin/bash

autojail config

cp *.c ../../jailhouse/configs/arm64

automate-run build -b raspberrypi4b-jh1
automate-run deploy -b raspberrypi4b-jh1

automate board.run raspberrypi4b-jh1 "sudo insmod jailhouse/driver/jailhouse.ko; sudo chmod ugo+rw /dev/jailhouse"

pushd ../../builds/raspberrypi4b-jh1/jailhouse/
python tools/jailhouse-config-check configs/arm64/rpi4-linux.cell configs/arm64/rpi4-linux-guest.cell
popd  

