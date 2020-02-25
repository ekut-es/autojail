# Proc Filesystem

## _/proc/iomem_

Gives a view of the system memory map as seen by the linux kernel.

Example rpi4b:

    00080000-3b3fffff : System RAM
      01080000-021fffff : Kernel code
      02200000-025fffff : reserved
      02600000-02847fff : Kernel data
      03000000-0300bfff : reserved
      03100000-0409ffff : reserved
      33400000-3b3fffff : reserved
    40000000-fbffffff : System RAM
      f6f20000-f77fffff : reserved
      f780f000-fb7fffff : reserved
      fb80e000-fb80efff : reserved
      fb811000-fb811fff : reserved
      fb812000-fb814fff : reserved
      fb815000-fbffffff : reserved
    fd500000-fd50930f : fd500000.pcie
    fd580000-fd58ffff : fd580000.genet
      fd580e14-fd580e1c : unimac-mdio.-19
    fd5d2200-fd5d222b : fd5d2200.thermal
    fe007000-fe007aff : fe007000.dma
    fe007b00-fe007eff : fe007b00.dma
    fe00a000-fe00a023 : fe100000.watchdog
    fe00b200-fe00b3ff : dwc_otg
    fe00b840-fe00b87b : fe00b840.mailbox
    fe00b880-fe00b8bf : fe00b880.mailbox
    fe100000-fe100113 : fe100000.watchdog
    fe101000-fe102fff : fe101000.cprman
    fe104000-fe10400f : fe104000.rng
    fe200000-fe2000b3 : fe200000.gpio
    fe201000-fe2011ff : serial@7e201000
      fe201000-fe2011ff : fe201000.serial
    fe204000-fe2041ff : fe204000.spi
    fe215000-fe215007 : fe215000.aux
    fe215040-fe21507f : fe215040.serial
    fe300000-fe3000ff : fe300000.mmcnr
    fe340000-fe3400ff : fe340000.emmc2
    fe804000-fe804fff : fe804000.i2c
    fe980000-fe98ffff : dwc_otg
    fec11000-fec1101f : fe100000.watchdog
    600000000-603ffffff : pcie@7d500000
      600000000-6000fffff : PCI Bus 0000:01
        600000000-600000fff : 0000:01:00.0
          600000000-600000fff : xhci-hcd
