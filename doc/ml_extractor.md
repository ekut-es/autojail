# Machine Learning based extraction from Datasheets / User Manuals

So far at least the following attributes seem problematic to 
derive from device trees:

    platform info:
	    Bases for SPI, PPI and SGI interrupts, but for now we can assume 0 for SGI, 16 for PPI and 32 for SPI
        vpci_irq_base 
         
        pci_mmconfig_base
        pci_mmconfig_end_bus
        pci_is_virtual
        pci_domain
     
    Shared Memory Configs:
        domain
        bdf
        bar_mask

They might be automatically extractable from datasheets using, 
intent detection similar to <https://ieeexplore.ieee.org/document/8876925> .
