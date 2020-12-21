#!/bin/bash

cp *.c ../../jailhouse/configs/arm64
cp linux-*.dts ../../jailhouse/configs/arm64/dts

automate-run build -b raspberrypi4b-jh1
automate-run deploy -b raspberrypi4b-jh1

automate board.run raspberrypi4b-jh1 "sudo insmod jailhouse/driver/jailhouse.ko"

