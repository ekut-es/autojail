# Machine Learning based extraction from Datasheets / User Manuals

So far at least the following attributes seem problematic to 
derive from device trees:

    platform info:
	    Bases for SPI, PPI and SGI interrupts, but for now we can assume 0 for SGI, 16 for PPI and 32 for SPI
     

They might be automatically extractable from datasheets using, 
intent detection similar to <https://ieeexplore.ieee.org/document/8876925> .
