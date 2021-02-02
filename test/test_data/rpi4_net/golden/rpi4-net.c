#include <jailhouse/types.h>
#include <jailhouse/cell-config.h>
struct { 
	struct jailhouse_system header; 
	__u64 cpus[1];
	struct jailhouse_memory mem_regions[28];
	struct jailhouse_irqchip irqchips[2];
	struct jailhouse_pci_device pci_devices[1];
} __attribute__((packed)) config = {

.header = {
	.signature = JAILHOUSE_SYSTEM_SIGNATURE,
	.revision = JAILHOUSE_CONFIG_REVISION,
	.flags = JAILHOUSE_SYS_VIRTUAL_DEBUG_CONSOLE,
	.hypervisor_memory = {
		.phys_start = 0x32000000,
		.size = 0x2000000,
	},

	.debug_console = {
		.address = 0xfe215040,
		.size = 0x40,
		.type = JAILHOUSE_CON_TYPE_8250,
		.flags = JAILHOUSE_CON_ACCESS_MMIO | JAILHOUSE_CON_REGDIST_4,
	},

	.platform_info = {
		.pci_mmconfig_base = 0x30000000,
		.pci_mmconfig_end_bus = 0,
		.pci_is_virtual = 1,
		.pci_domain = 1,
		.arm = {
			.maintenance_irq = 25,
			.gic_version = 2,
			.gicd_base = 0xff841000,
			.gicc_base = 0xff842000,
			.gich_base = 0xff844000,
			.gicv_base = 0xff846000,
			.gicr_base = 0x0,
		},

	},

	.root_cell = {
		.name = "RPI4 net" ,
		.vpci_irq_base = 32- 32,
		.num_memory_regions = ARRAY_SIZE(config.mem_regions),
		.num_pci_devices = ARRAY_SIZE(config.pci_devices),
		.cpu_set_size = sizeof(config.cpus),
		.num_irqchips = ARRAY_SIZE(config.irqchips),
	},
	},
	.cpus = {0b1111},
	
	.mem_regions = {
	/*Main Memory 0x0-0x30000000*/
	{
		.phys_start = 0x0,
		.virt_start = 0x0,
		.size = 0x30000000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_EXECUTE|JAILHOUSE_MEM_DMA,
	},
	/*serial@7e215040 0xfe215040-0xfe215080*/
	{
		.phys_start = 0xfe215040,
		.virt_start = 0xfe215040,
		.size = 0x40,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*net1 0x30200000-0x30201000*/
	{
		.phys_start = 0x30200000,
		.virt_start = 0x30200000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED,
	},
	/* empty optional region */
	{ 0 },
	/*net1 0x30201000-0x30202000*/
	{
		.phys_start = 0x30201000,
		.virt_start = 0x30201000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED|JAILHOUSE_MEM_WRITE,
	},
	/*net1 0x30202000-0x30203000*/
	{
		.phys_start = 0x30202000,
		.virt_start = 0x30202000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED,
	},
	/*mmio_0 0xfd500000-0xfd509310*/
	{
		.phys_start = 0xfd500000,
		.virt_start = 0xfd500000,
		.size = 0x9310,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_1 0xfd580000-0xfd590000*/
	{
		.phys_start = 0xfd580000,
		.virt_start = 0xfd580000,
		.size = 0x10000,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_2 0xfd5d2200-0xfd5d222c*/
	{
		.phys_start = 0xfd5d2200,
		.virt_start = 0xfd5d2200,
		.size = 0x2c,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_3 0xfe004000-0xfe01b200*/
	{
		.phys_start = 0xfe004000,
		.virt_start = 0xfe004000,
		.size = 0x17200,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_4 0xfe100000-0xfe104010*/
	{
		.phys_start = 0xfe100000,
		.virt_start = 0xfe100000,
		.size = 0x4010,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_5 0xfe200000-0xfe215008*/
	{
		.phys_start = 0xfe200000,
		.virt_start = 0xfe200000,
		.size = 0x15008,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_6 0xfe215080-0xfe215100*/
	{
		.phys_start = 0xfe215080,
		.virt_start = 0xfe215080,
		.size = 0x80,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_7 0xfe300000-0xfe300100*/
	{
		.phys_start = 0xfe300000,
		.virt_start = 0xfe300000,
		.size = 0x100,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_8 0xfe340000-0xfe340100*/
	{
		.phys_start = 0xfe340000,
		.virt_start = 0xfe340000,
		.size = 0x100,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_9 0xfe400000-0xfe406000*/
	{
		.phys_start = 0xfe400000,
		.virt_start = 0xfe400000,
		.size = 0x6000,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_10 0xfe600000-0xfe600100*/
	{
		.phys_start = 0xfe600000,
		.virt_start = 0xfe600000,
		.size = 0x100,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_11 0xfe700000-0xfe70008c*/
	{
		.phys_start = 0xfe700000,
		.virt_start = 0xfe700000,
		.size = 0x8c,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_12 0xfe800000-0xfe808600*/
	{
		.phys_start = 0xfe800000,
		.virt_start = 0xfe800000,
		.size = 0x8600,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_13 0xfe902000-0xfe902600*/
	{
		.phys_start = 0xfe902000,
		.virt_start = 0xfe902000,
		.size = 0x600,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_14 0xfe980000-0xfe990000*/
	{
		.phys_start = 0xfe980000,
		.virt_start = 0xfe980000,
		.size = 0x10000,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_15 0xfe9c0000-0xfeac0000*/
	{
		.phys_start = 0xfe9c0000,
		.virt_start = 0xfe9c0000,
		.size = 0x100000,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_16 0xfeb00000-0xfeb40000*/
	{
		.phys_start = 0xfeb00000,
		.virt_start = 0xfeb00000,
		.size = 0x40000,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_17 0xfec00000-0xfec11114*/
	{
		.phys_start = 0xfec00000,
		.virt_start = 0xfec00000,
		.size = 0x11114,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_18 0xfee08000-0xfee08100*/
	{
		.phys_start = 0xfee08000,
		.virt_start = 0xfee08000,
		.size = 0x100,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_19 0xff800000-0xff800100*/
	{
		.phys_start = 0xff800000,
		.virt_start = 0xff800000,
		.size = 0x100,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*Boot Memory@guest1 0x30203000-0x30303000*/
	{
		.phys_start = 0x30203000,
		.virt_start = 0x30203000,
		.size = 0x100000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*Main Memory@guest1 0x40000000-0x80000000*/
	{
		.phys_start = 0x40000000,
		.virt_start = 0x40000000,
		.size = 0x40000000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_DMA,
	},
	},
	.irqchips = {
		{
			.address = 0xff841000,
			.pin_base = 32,
			.pin_bitmap = {
				0xf0003, 
				0x106, 
				0x3fff0e00, 
				0x6b6777d6
			},
		},
		{
			.address = 0xff841000,
			.pin_base = 160,
			.pin_bitmap = {
				1 << (169 - 160) | 1 << (180 - 160) | 1 << (189 - 160) | 1 << (190 - 160), 
				1 << (208 - 192), 
				0x0, 
				0x0
			},
		},
	},

	.pci_devices = {
		/*net1*/
		{
			.type = JAILHOUSE_PCI_TYPE_IVSHMEM,
			.domain = 1,
			.bar_mask = JAILHOUSE_IVSHMEM_BAR_MASK_INTX,
			.bdf = 0 << 8 | 0 << 3 | 0,
			.shmem_regions_start = 2,
			.shmem_dev_id = 0,
			.shmem_peers = 2,
			.shmem_protocol = JAILHOUSE_SHMEM_PROTO_VETH,
		},
	},

};