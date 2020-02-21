# Device Trees

Linux Device Trees should provide most data needed. 

## Busses

### Memory Mapped Bus (simple-bus)

- compatible = "simple-bus" means a simple memory-mapped bus with no specific handling or driver.
- Childnodes will be registered as platform devices.
- The #address-cells property indicates how many cells (i.e 32 bit values) are needed to form the base address part in the reg property.
- The #size-cells is the same, for the size part of the reg property.
- The ranges property can describe an address translation between the child bus and the parent bus.  
  When simply defined as ranges;, it means that the translation is an identity translation.
- For busses not handled specially, we assume it is a simple bus


Examples:

- Jetson TX2: 
  
Main bus is 64 Bit e.g size-cells and address-cells are both 2.

        / {
                nvidia,dtbbuildtime = "Aug 12 2019\021:34:58";
                model = "quill";
                serial-number = "0423818033430";
                nvidia,proc-boardid = "3310:0000:A0";
                compatible = "nvidia,quill\0nvidia,tegra186";
                ...
                #size-cells = <0x02>;
                #address-cells = <0x02>;

- Raspberry PI 4B 

Main Bus is 64 Bit, but sizes are only given as 32 Bit Values

        / {
                memreserve = <0x3b400000 0x4c00000>;
                model = "Raspberry Pi 4 Model B Rev 1.1";
                serial-number = "100000007d82cb65";
                compatible = "raspberrypi,4-model-b\0brcm,bcm2711";
                interrupt-parent = <0x01>;
                #size-cells = <0x01>;
                #address-cells = <0x02>;

### Bus Bridges

Physical address translation is defined via. a ranges attribute.

"Ranges is a list of address translations. Each entry in the ranges table is a tuple containing the child address, 
the parent address, and the size of the region in the child address space. The size of each field is determined by 
taking the child's #address-cells value, the parent's #address-cells value, and the child's #size-cells value."

[source](https://elinux.org/Device_Tree_Usage#Ranges_.28Address_Translation.29)



Example:

- Raspberry PI 4b:

  In the following example addresses are translated from 64 Bit System Bus (*/*-Node) to 32-Bit SOC-Bus.
  
  The first line of ranges defines the following Mapping.
  
  0x7e000000 on the SOC-Bus is translated to 0x00...fe000000 in the System-Bus and the mapping is valid
  for all addresses in the range  0x7e000000-0x7c800000. 
  

         soc {
                 dma-ranges = <0xc0000000 0x00 0x00 0x3c000000>;
                 compatible = "simple-bus";
                 ranges = <0x7e000000 0x00 0xfe000000 0x1800000 
				           0x7c000000 0x00 0xfc000000 0x2000000 
						   0x40000000 0x00 0xff800000 0x800000>;
                 #size-cells = <0x01>;
                 phandle = <0x35>;
                 #address-cells = <0x01>;
				 
				 gpio@7e200000 {
                        ...
                        compatible = "brcm,bcm2711-gpio\0brcm,bcm2835-gpio";
                        reg = <0x7e200000 0xb4>;

So the device *gpio@7e200000* should correspond to the following entry from */proc/iomem*

        fe200000-fe2000b3 : fe200000.gpio

### PCIE-Bus

TBD:

Example Raspberry PI 4B:

                pcie@7d500000 {
                        interrupt-map-mask = <0x00 0x00 0x00 0x07>;
                        interrupts = <0x00 0x94 0x04 0x00 0x94 0x04>;
                        #interrupt-cells = <0x01>;
						dma-ranges = <0x2000000 0x00 0x00 0x00 0x00 0x01 0x00>;
                        compatible = "brcm,bcm7211-pcie\0brcm,bcm7445-pcie\0brcm,pci-plat-dev";
                        bus-range = <0x00 0x01>;
                        max-link-speed = <0x02>;
                        ranges = <0x2000000 0x00 0xf8000000 0x06 0x00 0x00 0x4000000>;
                        interrupt-names = "pcie\0msi";
                        reg = <0x00 0x7d500000 0x9310 0x00 0x7e00f300 0x20>;
                        linux,pci-domain = <0x00>;
                        tot-num-pcie = <0x01>;
                        #size-cells = <0x02>;
                        msi-parent = <0x22>;
                        phandle = <0x22>;
                        status = "okay";
                        interrupt-map = <0x00 0x00 0x00 0x01 0x01 0x00 0x8f 0x04 0x00 0x00 0x00 0x02 0x01 0x00 0x90 0x04 0x00 0x00 0x00 0x03 0x01 0x00 0x91 0x04 0x00 0x00 0x00 0x04 0x01 0x00 0x92 0x04>;
                        msi-controller;
                        #address-cells = <0x03>;
                };




## Interrupts

Source see: <https://www.kernel.org/doc/Documentation/devicetree/bindings/interrupt-controller/interrupts.txt>

### Interrupt Sources

Devices that can generate interrupts, have an *interrupts*. 

Examples:

- Raspberry PI 4B: 

        gpio@7e200000 {
                 interrupts = <0x00 0x71 0x04 0x00 0x72 0x04>;
                 gpio-controller;
                 pinctrl-names = "default";
                 #interrupt-cells = <0x02>;
                 compatible = "brcm,bcm2711-gpio\0brcm,bcm2835-gpio";
                 reg = <0x7e200000 0xb4>;
                 interrupt-controller;
                 #gpio-cells = <0x02>;
                 phandle = <0x0f>;

                 ...
        }

        timer {
                interrupts = <0x01 0x0d 0xf08 0x01 0x0e 0xf08 0x01 0x0b 0xf08 0x01 0x0a 0xf08>;
                arm,cpu-registers-not-fw-configured;
                compatible = "arm,armv7-timer";
                always-on;
        };




### Interrupt Controller

Device Tree Nodes with the property *interrupt-controller;* set, are interrupt controllers.

It has the following attributes:

#interrupt-cells : It specifies the number of cells needed to encode an interrupt source. In the case of ARM-GICs interrupt-cells should always be 3



- Raspberry PI 4B

                gic400@40041000 {
                        interrupts = <0x01 0x09 0xf04>;
                        #interrupt-cells = <0x03>;
                        compatible = "arm,gic-400";
                        reg = <0x40041000 0x1000 0x40042000 0x2000 0x40044000 0x2000 0x40046000 0x2000>;
                        interrupt-controller;
                        phandle = <0x01>;
                };





## Parsing Libraries

- <https://pypi.org/project/fdt/>
- <https://pypi.org/project/pyfdt/>


## Documentation Links:

- <https://elinux.org/Device_Tree_Reference>
- <https://elinux.org/images/c/cf/Power_ePAPR_APPROVED_v1.1.pdf>
- <https://elinux.org/images/f/f9/Petazzoni-device-tree-dummies_0.pdf>
