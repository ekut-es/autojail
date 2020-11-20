#include <jailhouse/types.h>
#include <jailhouse/cell-config.h>
struct { 
	struct jailhouse_system header; 
	__u64 cpus[1];
	struct jailhouse_memory mem_regions[11];
	struct jailhouse_irqchip irqchips[2];
	struct jailhouse_pci_device pci_devices[1];
} __attribute__((packed)) config = {

.header = {
	.signature = JAILHOUSE_SYSTEM_SIGNATURE,
	.revision = JAILHOUSE_CONFIG_REVISION,
	.flags = JAILHOUSE_SYS_VIRTUAL_DEBUG_CONSOLE,
	.hypervisor_memory = {
		.phys_start = 0x82000000,
		.size = 0x2000000,
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
	/*net1 0x80000000-0x80001000*/
	{
		.phys_start = 0x80000000,
		.virt_start = 0x80000000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED,
	},
	/* empty optional region */
	{ 0 },
	/*net1 0x80001000-0x80002000*/
	{
		.phys_start = 0x80001000,
		.virt_start = 0x80001000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED|JAILHOUSE_MEM_WRITE,
	},
	/*net1 0x80002000-0x80003000*/
	{
		.phys_start = 0x80002000,
		.virt_start = 0x80002000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED,
	},
	/*memreserve 0x3b400000-0x40000000*/
	{
		.phys_start = 0x3b400000,
		.virt_start = 0x3b400000,
		.size = 0x4c00000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_EXECUTE,
	},
	/*mmio_0 0xfd500000-0xfe215008*/
	{
		.phys_start = 0xfd500000,
		.virt_start = 0xfd500000,
		.size = 0xd15008,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*mmio_1 0xfe215080-0xff800100*/
	{
		.phys_start = 0xfe215080,
		.virt_start = 0xfe215080,
		.size = 0x15eb080,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*Boot Memory@guest1 0x80003000-0x80103000*/
	{
		.phys_start = 0x80003000,
		.virt_start = 0x80003000,
		.size = 0x100000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_EXECUTE,
	},
	/*Main Memory@guest1 0x40000000-0x80000000*/
	{
		.phys_start = 0x40000000,
		.virt_start = 0x40000000,
		.size = 0x40000000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_EXECUTE|JAILHOUSE_MEM_DMA,
	},
	},
	.irqchips = {
		{
			.address = 0xff841000,
			.pin_base = 32,
			.pin_bitmap = {
				0x3, 
				0x106, 
				0x3fff0e00, 
				0x6b6177d6
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