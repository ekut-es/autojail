
When configuring the shared mbox on raspberry we have seen the following error log on UART. 

    Initializing Jailhouse hypervisor v0.12 (81-g9b4efcf4-dirty) on CPU 0
    Code location: 0x0000ffffc0200800
    Page pool usage after early setup: mem 39/993, remap 0/131072
    Initializing processors:
    CPU 0... OK
    CPU 2... OK
    CPU 1... OK
    CPU 3... OK
    Initializing unit: irqchip
    Initializing unit: ARM SMMU v3
    Initializing unit: PVU IOMMU
    Initializing unit: PCI
    Adding virtual PCI device 00:00.0 to cell "Raspberry-Pi4"
    Adding virtual PCI device 00:01.0 to cell "Raspberry-Pi4"
    Page pool usage after late setup: mem 61/993, remap 5/131072
    Activating hypervisor
    [  124.716501] pci 0001:00:00.0: failed to get arch_dma_ops
    [  124.727383] pci 0001:00:01.0: failed to get arch_dma_ops
    Adding virtual PCI device 00:00.0 to cell "rpi4-linux-demo"
    Shared memory connection established, peer cells:
    "Raspberry-Pi4"
    Adding virtual PCI device 00:01.0 to cell "rpi4-linux-demo"
    Shared memory connection established, peer cells:
    "Raspberry-Pi4"
    Created cell "rpi4-linux-demo"
    Page pool usage after cell creation: mem 76/993, remap 5/131072
    Cell "rpi4-linux-demo" can be loaded
    Started cell "rpi4-linux-demo"
    [  177.983689] raspberrypi-clk raspberrypi-clk: Failed to change pllb frequency: -110
    [  179.007444] raspberrypi-clk raspberrypi-clk: Failed to get pllb frequency: -110
    [  180.031462] hwmon hwmon0: Failed to get throttled (-110)
    [  181.055475] raspberrypi-clk raspberrypi-clk: Failed to change pllb frequency: -110
    [  182.079494] raspberrypi-clk raspberrypi-clk: Failed to get pllb frequency: -110
    [  184.127559] raspberrypi-clk raspberrypi-clk: Failed to change pllb frequency: -110
    [  185.151579] raspberrypi-clk raspberrypi-clk: Failed to get pllb frequency: -110
    [  187.199600] raspberrypi-clk raspberrypi-clk: Failed to change pllb frequency: -110
    [  188.223629] raspberrypi-clk raspberrypi-clk: Failed to get pllb frequency: -110
    [  191.583700] raspberrypi-clk raspberrypi-clk: Failed to change pllb frequency: -110
    [  193.631949] raspberrypi-clk raspberrypi-clk: Failed to get pllb frequency: -110
    [  194.687709] raspberrypi-clk raspberrypi-clk: Failed to change pllb frequency: -110
    [  363.490089] INFO: task kworker/0:2:70 blocked for more than 120 seconds.
    [  363.497308]       Tainted: G        W  O      5.4.16 #3
    [  363.502888] "echo 0 > /proc/sys/kernel/hung_task_timeout_secs" disables this message.
    [  363.511712] INFO: task kworker/1:2:320 blocked for more than 120 seconds.
    [  363.518818]       Tainted: G        W  O      5.4.16 #3
    [  363.524458] "echo 0 > /proc/sys/kernel/hung_task_timeout_secs" disables this message.
    [  484.323354] INFO: task kworker/0:2:70 blocked for more than 241 seconds.
    [  484.330390]       Tainted: G        W  O      5.4.16 #3
    [  484.336075] "echo 0 > /proc/sys/kernel/hung_task_timeout_secs" disables this message.
    [  484.344941] INFO: task kworker/1:2:320 blocked for more than 241 seconds.
    [  484.352071]       Tainted: G        W  O      5.4.16 #3
    [  484.357716] "echo 0 > /proc/sys/kernel/hung_task_timeout_secs" disables this message.
    [  605.157550] INFO: task kworker/0:2:70 blocked for more than 362 seconds.
    [  605.164816]       Tainted: G        W  O      5.4.16 #3
    [  605.170505] "echo 0 > /proc/sys/kernel/hung_task_timeout_secs" disables this message.
    [  605.179555] INFO: task kworker/1:2:320 blocked for more than 362 seconds.
    [  605.186745]       Tainted: G        W  O      5.4.16 #3
    [  605.192386] "echo 0 > /proc/sys/kernel/hung_task_timeout_secs" disables this message.
    Closing cell "rpi4-linux-demo"
    WARNING: Overflow during MMIO region registration!
    Page pool usage after cell destruction: mem 62/993, remap 5/131072
    [  725.991700] INFO: task kworker/0:2:70 blocked for more than 483 seconds.
    [  725.998898]       Tainted: G        W  O      5.4.16 #3
    [  726.004593] "echo 0 > /proc/sys/kernel/hung_task_timeout_secs" disables this message.
    [  726.013504] INFO: task kworker/1:2:320 blocked for more than 483 seconds.
    [  726.020612]       Tainted: G        W  O      5.4.16 #3
    [  726.026363] "echo 0 > /proc/sys/kernel/hung_task_timeout_secs" disables this message
