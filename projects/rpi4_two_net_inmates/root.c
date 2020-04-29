#include <jailhouse/types.h>
#include <jailhouse/cell-config.h>
struct { 
	struct jailhouse_system header; 
	__u64 cpus[1];
	struct jailhouse_memory mem_regions[9];
	struct jailhouse_irqchip irqchips[2];
	struct jailhouse_pci_device pci_devices[2];
} __attribute__((packed)) config = {

.header = {
	.signature = JAILHOUSE_SYSTEM_SIGNATURE,
	.revision = JAILHOUSE_CONFIG_REVISION,
	.flags = JAILHOUSE_SYS_VIRTUAL_DEBUG_CONSOLE,
	.hypervisor_memory = {
		.phys_start = 0x3fc00000,
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
			.gic_version = 2,,
			.gicd_base = 0xff841000,,
			.gicc_base = 0xff842000,,
			.gich_base = 0xff844000,,
			.gicv_base = 0xff846000,,
			.maintenance_irq = 25,,
		},

	},

	.root_cell = {
		.name = "root" ,
		.vpci_irq_base = 150,
		.num_memory_regions = ARRAY_SIZE(config.mem_regions),
		.num_pci_devices = ARRAY_SIZE(config.pci_devices),
		.cpu_set_size = sizeof(config.cpus),
		.num_irqchips = ARRAY_SIZE(config.irqchips),
	},
	},
	.cpus = {0b11111},
	
	.mem_regions = {
	/*System RAM 0x0-0x4fa10000*/
	{
		.phys_start = 0x0,
		.virt_start = 0x0,
		.size = 0x4fa10000,
		.flags = MEM_READ|MEM_WRITE|MEM_EXECUTE,
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
	/*net2_0 0x0-0x1000*/
	{
		.phys_start = 0x0,
		.virt_start = 0x0,
		.size = 0x1000,
		.flags = MEM_READ|MEM_ROOTSHARED,
	},
	/*net2_1 0x0-0x0*/
	{
		.phys_start = 0x0,
		.virt_start = 0x0,
		.size = 0x0,
		.flags = MEM_READ|MEM_WRITE|MEM_ROOTSHARED,
	},
	/*net2_2 0x0-0x0*/
	{
		.phys_start = 0x0,
		.virt_start = 0x0,
		.size = 0x0,
		.flags = MEM_READ|MEM_ROOTSHARED,
	},
	/*net2_3 0x0-0x0*/
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
			.pin_bitmap = {0xffffffff, 0xffffffff, 0xffffffff, 0xffffffff},
		},
		{
			.address = 0xff841000,
			.pin_base = 160,
			.pin_bitmap = {0xffffffff, 0xffffffff, 0xffffffff},
		},
	},

	.pci_devices = {
		/*net1*/
		{
			.type = JAILHOUSE_PCI_TYPE_IVSHMEM,
			.domain = 1,
			.bar_mask = JAILHOUSE_IVSHMEM_BAR_MASK_INTX,
			.bdf = 0,
			.shmem_regions_start = -1,
			.shmem_dev_id = 0,
			.shmem_peers = 2,
			.shmem_protocol = JAILHOUSE_SHMEM_PROTO_VETH,
		},
		/*net2*/
		{
			.type = JAILHOUSE_PCI_TYPE_IVSHMEM,
			.domain = 1,
			.bar_mask = JAILHOUSE_IVSHMEM_BAR_MASK_INTX,
			.bdf = 8,
			.shmem_regions_start = -1,
			.shmem_dev_id = 0,
			.shmem_peers = 2,
			.shmem_protocol = JAILHOUSE_SHMEM_PROTO_VETH,
		},
	},

};