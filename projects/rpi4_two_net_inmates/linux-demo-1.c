#include <jailhouse/types.h>
#include <jailhouse/cell-config.h>
struct { 
	struct jailhouse_cell_desc cell; 
	__u64 cpus[1];
	struct jailhouse_memory mem_regions[6];
	struct jailhouse_irqchip irqchips[2];
	struct jailhouse_pci_device pci_devices[1];
} __attribute__((packed)) config = {

.cell = {
	.signature = JAILHOUSE_SYSTEM_SIGNATURE,
	.revision = JAILHOUSE_CONFIG_REVISION,
	.flags = JAILHOUSE_SYS_VIRTUAL_DEBUG_CONSOLE,
	.debug_console = {
		.address = 0xfe215040,
		.size = 0x40,
		.type = JAILHOUSE_CON_TYPE_8250,
		.flags = JAILHOUSE_CON_ACCESS_MMIO | JAILHOUSE_CON_REGDIST_4,
	},

		.name = "Linux demo 1" ,
		.vpci_irq_base = 153,
		.num_memory_regions = ARRAY_SIZE(config.mem_regions),
		.num_pci_devices = ARRAY_SIZE(config.pci_devices),
		.cpu_set_size = sizeof(config.cpus),
		.num_irqchips = ARRAY_SIZE(config.irqchips),
	},
	.cpus = {0b110},
	
	.mem_regions = {
	/*RAM 1 0x4f900000-0x4f910000*/
	{
		.phys_start = 0x4f900000,
		.virt_start = 0x0,
		.size = 0x10000,
		.flags = MEM_READ|MEM_WRITE|MEM_EXECUTE|MEM_LOADABLE,
	},
	/*RAM 2 0x30000000-0x38000000*/
	{
		.phys_start = 0x30000000,
		.virt_start = 0x30000000,
		.size = 0x8000000,
		.flags = MEM_READ|MEM_WRITE|MEM_EXECUTE|MEM_DMA|MEM_LOADABLE,
	},
	/*net1_0 0x0-0x1000*/
	{
		.phys_start = 0x0,
		.virt_start = 0x0,
		.size = 0x1000,
		.flags = MEM_READ|MEM_ROOTSHARED,
	},
	/*net1_1 0x0-0x0*/
	{
		.phys_start = 0x0,
		.virt_start = 0x0,
		.size = 0x0,
		.flags = MEM_READ|MEM_WRITE|MEM_ROOTSHARED,
	},
	/*net1_2 0x0-0x0*/
	{
		.phys_start = 0x0,
		.virt_start = 0x0,
		.size = 0x0,
		.flags = MEM_READ|MEM_ROOTSHARED,
	},
	/*net1_3 0x0-0x0*/
	{
		.phys_start = 0x0,
		.virt_start = 0x0,
		.size = 0x0,
		.flags = MEM_READ|MEM_ROOTSHARED,
	},
	},
	.irqchips = {
		{
			.address = 0xff841000,
			.pin_base = 32,
			.pin_bitmap = {},
		},
		{
			.address = 0xff841000,
			.pin_base = 160,
			.pin_bitmap = {0x0, 0x2000000},
		},
	},

	.pci_devices = {
		/*gic*/
		{
			.type = JAILHOUSE_PCI_TYPE_IVSHMEM,
			.domain = 1,
			.bar_mask = JAILHOUSE_IVSHMEM_BAR_MASK_INTX,
			.bdf = 0,
			.shmem_regions_start = -1,
			.shmem_dev_id = 1,
			.shmem_peers = 2,
			.shmem_protocol = JAILHOUSE_SHMEM_PROTO_VETH,
		},
	},

};