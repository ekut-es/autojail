#include <jailhouse/types.h>
#include <jailhouse/cell-config.h>
struct { 
	struct jailhouse_cell_desc cell; 
	__u64 cpus[1];
	struct jailhouse_memory mem_regions[8];
	struct jailhouse_irqchip irqchips[2];
	struct jailhouse_pci_device pci_devices[1];
} __attribute__((packed)) config = {

.cell = {
	.signature = JAILHOUSE_CELL_DESC_SIGNATURE,
	.revision = JAILHOUSE_CONFIG_REVISION,
	.flags = JAILHOUSE_CELL_PASSIVE_COMMREG | JAILHOUSE_CELL_VIRTUAL_CONSOLE_PERMITTED,
	.console = {
		.address = 0xfe215040,
		.size = 0x40,
		.type = JAILHOUSE_CON_TYPE_8250,
		.flags = JAILHOUSE_CON_ACCESS_MMIO | JAILHOUSE_CON_REGDIST_4,
	},

		.name = "Linux demo 2" ,
		.vpci_irq_base = 187,
		.num_memory_regions = ARRAY_SIZE(config.mem_regions),
		.num_pci_devices = ARRAY_SIZE(config.pci_devices),
		.cpu_set_size = sizeof(config.cpus),
		.num_irqchips = ARRAY_SIZE(config.irqchips),
	},
	.cpus = {0b1000},
	
	.mem_regions = {
	/*RAM 1 0xebfd7000-0xebfe7000*/
	{
		.phys_start = 0xebfd7000,
		.virt_start = 0x0,
		.size = 0x10000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_EXECUTE|JAILHOUSE_MEM_LOADABLE,
	},
	/*RAM 2 0xe3fd7000-0xebfd7000*/
	{
		.phys_start = 0xe3fd7000,
		.virt_start = 0x10000,
		.size = 0x8000000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_EXECUTE|JAILHOUSE_MEM_DMA|JAILHOUSE_MEM_LOADABLE,
	},
	/*gpio 0xfe200000-0xfe201000*/
	{
		.phys_start = 0xfe200000,
		.virt_start = 0xfe200000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*serial@7e215040 0xfe215040-0xfe215080*/
	{
		.phys_start = 0xfe215040,
		.virt_start = 0xfe215040,
		.size = 0x40,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*net2_0 0xe3fd6000-0xe3fd7000*/
	{
		.phys_start = 0xe3fd6000,
		.virt_start = 0x8010000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED,
	},
	/* empty optional region */
	{ 0 },
	/*net2_2 0xe3fd5000-0xe3fd6000*/
	{
		.phys_start = 0xe3fd5000,
		.virt_start = 0x8011000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED,
	},
	/*net2_3 0xe3fd4000-0xe3fd5000*/
	{
		.phys_start = 0xe3fd4000,
		.virt_start = 0x8012000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED|JAILHOUSE_MEM_WRITE,
	},
	},
	.irqchips = {
		{
			.address = 0xff841000,
			.pin_base = 32,
			.pin_bitmap = {0x0, 0x2000000000000000, 0x0, 0x0},
		},
		{
			.address = 0xff841000,
			.pin_base = 160,
			.pin_bitmap = {0x0, 0x10000000, 0x0, 0x0},
		},
	},

	.pci_devices = {
		/*net2*/
		{
			.type = JAILHOUSE_PCI_TYPE_IVSHMEM,
			.domain = 1,
			.bar_mask = JAILHOUSE_IVSHMEM_BAR_MASK_INTX,
			.bdf = 1 << 3,
			.shmem_regions_start = 4,
			.shmem_dev_id = 1,
			.shmem_peers = 2,
			.shmem_protocol = JAILHOUSE_SHMEM_PROTO_VETH,
		},
	},

};