#include <jailhouse/types.h>
#include <jailhouse/cell-config.h>
struct { 
	struct jailhouse_system header; 
	__u64 cpus[1];
	struct jailhouse_memory mem_regions[29];
	struct jailhouse_irqchip irqchips[2];
	struct jailhouse_pci_device pci_devices[2];
} __attribute__((packed)) config = {

.header = {
	.signature = JAILHOUSE_SYSTEM_SIGNATURE,
	.revision = JAILHOUSE_CONFIG_REVISION,
	.flags = JAILHOUSE_SYS_VIRTUAL_DEBUG_CONSOLE,
	.hypervisor_memory = {
		.phys_start = 0x30000000,
		.size = 0x1000000,
	},

	.debug_console = {
		.address = 0xfe215040,
		.size = 0x40,
		.type = JAILHOUSE_CON_TYPE_8250,
		.flags = JAILHOUSE_CON_ACCESS_MMIO | JAILHOUSE_CON_REGDIST_4,
	},

	.platform_info = {
		.pci_mmconfig_base = 0xe0000000,
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
		.name = "Raspberry PI4" ,
		.vpci_irq_base = 150- 32,
		.num_memory_regions = ARRAY_SIZE(config.mem_regions),
		.num_pci_devices = ARRAY_SIZE(config.pci_devices),
		.cpu_set_size = sizeof(config.cpus),
		.num_irqchips = ARRAY_SIZE(config.irqchips),
	},
	},
	.cpus = {0b1111},
	
	.mem_regions = {
	/*System RAM 0x0-0x30000000*/
	{
		.phys_start = 0x0,
		.virt_start = 0x0,
		.size = 0x30000000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_EXECUTE,
	},
	/*ivshmem1 0x3faf0000-0x3faf1000*/
	{
		.phys_start = 0x3faf0000,
		.virt_start = 0x3faf0000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ,
	},
	/*ivshmem2 0x3faf1000-0x3fafa000*/
	{
		.phys_start = 0x3faf1000,
		.virt_start = 0x3faf1000,
		.size = 0x9000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*ivshmem3 0x3fafa000-0x3fafc000*/
	{
		.phys_start = 0x3fafa000,
		.virt_start = 0x3fafa000,
		.size = 0x2000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*ivshmem4 0x3fafc000-0x3fafe000*/
	{
		.phys_start = 0x3fafc000,
		.virt_start = 0x3fafc000,
		.size = 0x2000,
		.flags = JAILHOUSE_MEM_READ,
	},
	/*ivshmem5 0x3fafe000-0x3fb00000*/
	{
		.phys_start = 0x3fafe000,
		.virt_start = 0x3fafe000,
		.size = 0x2000,
		.flags = JAILHOUSE_MEM_READ,
	},
	/* shmem_net */
	JAILHOUSE_SHMEM_NET_REGIONS(0x3fb00000, 0),
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
	/*mmio_5 0xfe200000-0xfe215100*/
	{
		.phys_start = 0xfe200000,
		.virt_start = 0xfe200000,
		.size = 0x15100,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_6 0xfe300000-0xfe300100*/
	{
		.phys_start = 0xfe300000,
		.virt_start = 0xfe300000,
		.size = 0x100,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_7 0xfe340000-0xfe340100*/
	{
		.phys_start = 0xfe340000,
		.virt_start = 0xfe340000,
		.size = 0x100,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_8 0xfe400000-0xfe406000*/
	{
		.phys_start = 0xfe400000,
		.virt_start = 0xfe400000,
		.size = 0x6000,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_9 0xfe600000-0xfe600100*/
	{
		.phys_start = 0xfe600000,
		.virt_start = 0xfe600000,
		.size = 0x100,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_10 0xfe700000-0xfe70008c*/
	{
		.phys_start = 0xfe700000,
		.virt_start = 0xfe700000,
		.size = 0x8c,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_11 0xfe800000-0xfe808600*/
	{
		.phys_start = 0xfe800000,
		.virt_start = 0xfe800000,
		.size = 0x8600,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_12 0xfe902000-0xfe902600*/
	{
		.phys_start = 0xfe902000,
		.virt_start = 0xfe902000,
		.size = 0x600,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_13 0xfe980000-0xfe990000*/
	{
		.phys_start = 0xfe980000,
		.virt_start = 0xfe980000,
		.size = 0x10000,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_14 0xfe9c0000-0xfeac0000*/
	{
		.phys_start = 0xfe9c0000,
		.virt_start = 0xfe9c0000,
		.size = 0x100000,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_15 0xfeb00000-0xfeb40000*/
	{
		.phys_start = 0xfeb00000,
		.virt_start = 0xfeb00000,
		.size = 0x40000,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_16 0xfec00000-0xfec11114*/
	{
		.phys_start = 0xfec00000,
		.virt_start = 0xfec00000,
		.size = 0x11114,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_17 0xfee08000-0xfee08100*/
	{
		.phys_start = 0xfee08000,
		.virt_start = 0xfee08000,
		.size = 0x100,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_18 0xff800000-0xff800100*/
	{
		.phys_start = 0xff800000,
		.virt_start = 0xff800000,
		.size = 0x100,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	},
	.irqchips = {
		{
			.address = 0xff841000,
			.pin_base = 32,
			.pin_bitmap = {
				0xffffffff, 
				0xffffffff, 
				0xffffffff, 
				0xffffffff
			},
		},
		{
			.address = 0xff841000,
			.pin_base = 160,
			.pin_bitmap = {
				0xffffffff, 
				0xffffffff, 
				0xffffffff, 
				0x0
			},
		},
	},

	.pci_devices = {
		/*demo*/
		{
			.type = JAILHOUSE_PCI_TYPE_IVSHMEM,
			.domain = 1,
			.bar_mask = JAILHOUSE_IVSHMEM_BAR_MASK_INTX,
			.bdf = 0 << 8 | 0 << 3 | 0,
			.shmem_regions_start = 0,
			.shmem_dev_id = 0,
			.shmem_peers = 3,
			.shmem_protocol = JAILHOUSE_SHMEM_PROTO_UNDEFINED,
		},
		/*networking*/
		{
			.type = JAILHOUSE_PCI_TYPE_IVSHMEM,
			.domain = 1,
			.bar_mask = JAILHOUSE_IVSHMEM_BAR_MASK_INTX,
			.bdf = 0 << 8 | 1 << 3 | 0,
			.shmem_regions_start = 5,
			.shmem_dev_id = 0,
			.shmem_peers = 2,
			.shmem_protocol = JAILHOUSE_SHMEM_PROTO_VETH,
		},
	},

};