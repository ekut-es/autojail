# Machine Learning based extraction from Datasheets / User Manuals

So far at least the following attributes seem problematic to 
derive from device trees:

    platform info:
        maintenance_irq = 25 # But is always 25 on the example boards
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
