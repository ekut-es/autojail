#!/bin/bash -e 


BOARD=raspberrypi4b-jh1

script_path="`dirname \"$0\"`"

pushd "${script_path}/../../"


do_reset=0

while [[ $# -gt 0 ]]
do
key="$1"

case $key in
    -r|--reset)
    do_reset=1
    shift # past argument
    ;;
    *)    # unknown option
    exit
    shift # past argument
    ;;
esac
done

if [ $do_reset == 1 ]; then
    reset_raspi
fi

#automate-run update
pushd board_data
python -m autojail.extract.board rpi4 rpi4 raspberrypi4b-jh1
popd

cp board_data/config_rpi4.c configs/arm64/
cp -r configs jailhouse
automate-run build -b raspberrypi4b-jh1
automate-run deploy -b raspberrypi4b-jh1

automate board.lock raspberrypi4b-jh1


automate board.run raspberrypi4b-jh1 /home/es/kexec_jailhouse.sh || true
automate board.run raspberrypi4b-jh1 "sudo insmod jailhouse/driver/jailhouse.ko"
#automate board.run raspberrypi4b-jh1 "sudo jailhouse/tools/jailhouse enable jailhouse/configs/arm64/rpi4.cell"
automate board.run raspberrypi4b-jh1 "sudo jailhouse/tools/jailhouse enable jailhouse/configs/arm64/config_rpi4.cell"
automate board.run raspberrypi4b-jh1 "sudo jailhouse/tools/jailhouse cell create jailhouse/configs/arm64/rpi4-inmate-demo.cell"
automate board.run raspberrypi4b-jh1 "sudo jailhouse/tools/jailhouse cell load 1 jailhouse/inmates/demos/arm64/gic-demo.bin"
automate board.run raspberrypi4b-jh1 "sudo jailhouse/tools/jailhouse cell start 1"
automate board.run raspberrypi4b-jh1 "sudo jailhouse/tools/jailhouse cell list"

read -p "Press enter to stop jailhouse and reboot the board"

automate board.run raspberrypi4b-jh1 "sudo jailhouse/tools/jailhouse disable"

automate board.reboot $BOARD
automate board.unlock $BOARD
