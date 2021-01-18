#include <jailhouse/types.h>
#include <jailhouse/cell-config.h>
struct { 
	struct jailhouse_cell_desc cell; 
	__u64 cpus[1];
	struct jailhouse_memory mem_regions[8];
	struct jailhouse_irqchip irqchips[1];
	struct jailhouse_pci_device pci_devices[1];
} __attribute__((packed)) config = {

.cell = {
	.signature = JAILHOUSE_CELL_DESC_SIGNATURE,
	.revision = JAILHOUSE_CONFIG_REVISION,
	.console = {
		.address = 0x9000000,
		.size = 0x1000,
		.type = JAILHOUSE_CON_TYPE_PL011,
		.flags = JAILHOUSE_CON_ACCESS_MMIO | JAILHOUSE_CON_REGDIST_4,
	},

		.name = "guest" ,
		.vpci_irq_base = 32- 32,
		.num_memory_regions = ARRAY_SIZE(config.mem_regions),
		.num_pci_devices = ARRAY_SIZE(config.pci_devices),
		.cpu_set_size = sizeof(config.cpus),
		.num_irqchips = ARRAY_SIZE(config.irqchips),
	},
	.cpus = {0b1},
	
	.mem_regions = {
	/*boot 0x60106000-0x60206000*/
	{
		.phys_start = 0x60106000,
		.virt_start = 0x0,
		.size = 0x100000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_EXECUTE|JAILHOUSE_MEM_LOADABLE,
	},
	/*main 0x60206000-0x80206000*/
	{
		.phys_start = 0x60206000,
		.virt_start = 0x9001000,
		.size = 0x20000000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_EXECUTE|JAILHOUSE_MEM_DMA|JAILHOUSE_MEM_LOADABLE,
	},
	/*comm 0x80206000-0x80207000*/
	{
		.phys_start = 0x80206000,
		.virt_start = 0x80000000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_COMM_REGION,
	},
	/*pl011@9000000 0x9000000-0x9001000*/
	{
		.phys_start = 0x9000000,
		.virt_start = 0x9000000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*net1 0x60000000-0x60001000*/
	{
		.phys_start = 0x60000000,
		.virt_start = 0x100000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED,
	},
	/* empty optional region */
	{ 0 },
	/*net1 0x60001000-0x60002000*/
	{
		.phys_start = 0x60001000,
		.virt_start = 0x101000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED,
	},
	/*net1 0x60002000-0x60003000*/
	{
		.phys_start = 0x60002000,
		.virt_start = 0x102000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED|JAILHOUSE_MEM_WRITE,
	},
	},
	.irqchips = {
		{
			.address = 0x8000000,
			.pin_base = 32,
			.pin_bitmap = {
				1 << (32 - 32) | 1 << (33 - 32), 
				0x0, 
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
			.shmem_regions_start = 4,
			.shmem_dev_id = 1,
			.shmem_peers = 2,
			.shmem_protocol = JAILHOUSE_SHMEM_PROTO_VETH,
		},
	},

};