#include <jailhouse/types.h>
#include <jailhouse/cell-config.h>
struct { 
	struct jailhouse_system header; 
	__u64 cpus[1];
	struct jailhouse_memory mem_regions[8];
	struct jailhouse_irqchip irqchips[2];
	struct jailhouse_pci_device pci_devices[2];
} __attribute__((packed)) config = {

.header = {
	.signature = JAILHOUSE_SYSTEM_SIGNATURE,
	.revision = JAILHOUSE_CONFIG_REVISION,
	.flags = JAILHOUSE_SYS_VIRTUAL_DEBUG_CONSOLE,
	.hypervisor_memory = {
		.phys_start = 0x41000000,
		.size = 0x1000000,
	},

	.debug_console = {
		.address = 0xfe215040,
		.size = 0x40,
		.type = JAILHOUSE_CON_TYPE_8250,
		.flags = JAILHOUSE_CON_ACCESS_MMIO | JAILHOUSE_CON_REGDIST_4,
	},

	.platform_info = {
		.pci_mmconfig_base = 0x40000000,
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
	/*mmio_0 0xfd500000-0xff800100*/
	{
		.phys_start = 0xfd500000,
		.virt_start = 0xfd500000,
		.size = 0x2300100,
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