#include <jailhouse/types.h>
#include <jailhouse/cell-config.h>
struct { 
	struct jailhouse_system header; 
	__u64 cpus[1];
	struct jailhouse_memory mem_regions[11];
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
			.gic_version = 2,
			.gicd_base = 0xff841000,
			.gicc_base = 0xff842000,
			.gich_base = 0xff844000,
			.gicv_base = 0xff846000,
			.maintenance_irq = 25,
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
	.cpus = {0b1111},
	
	.mem_regions = {
	/*System RAM 0x0-0x4fa10000*/	{
		.phys_start = 0x0,
		.virt_start = 0x0,
		.size = 0x4fa10000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_EXECUTE,
	},
	/*net1_0 0x4fa0d000-0x4fa0e000*/	{
		.phys_start = 0x4fa0d000,
		.virt_start = 0x4fa0d000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED,
	},
	/* empty optional region */ { 0 },
	/*net1_2 0x4fa0e000-0x4fa0f000*/	{
		.phys_start = 0x4fa0e000,
		.virt_start = 0x4fa0e000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED|JAILHOUSE_MEM_WRITE,
	},
	/*net1_3 0x4fa0f000-0x4fa10000*/	{
		.phys_start = 0x4fa0f000,
		.virt_start = 0x4fa0f000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED,
	},
	/*net2_0 0x4fa0a000-0x4fa0b000*/	{
		.phys_start = 0x4fa0a000,
		.virt_start = 0x4fa0e000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED,
	},
	/* empty optional region */ { 0 },
	/*net2_2 0x4fa0b000-0x4fa0c000*/	{
		.phys_start = 0x4fa0b000,
		.virt_start = 0x4fa0f000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED|JAILHOUSE_MEM_WRITE,
	},
	/*net2_3 0x4fa0c000-0x4fa0d000*/	{
		.phys_start = 0x4fa0c000,
		.virt_start = 0x4fa10000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED,
	},
	/*MMIO_1 0xfd500000-0xff000000*/	{
		.phys_start = 0xfd500000,
		.virt_start = 0xfd500000,
		.size = 0x1b00000,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO,
	},
	/*MMIO_2 0x600000000-0x604000000*/	{
		.phys_start = 0x600000000,
		.virt_start = 0x600000000,
		.size = 0x4000000,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO,
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
			.bdf = 0 << 3,
			.shmem_regions_start = 1,
			.shmem_dev_id = 0,
			.shmem_peers = 2,
			.shmem_protocol = JAILHOUSE_SHMEM_PROTO_VETH,
		},
		/*net2*/
		{
			.type = JAILHOUSE_PCI_TYPE_IVSHMEM,
			.domain = 1,
			.bar_mask = JAILHOUSE_IVSHMEM_BAR_MASK_INTX,
			.bdf = 1 << 3,
			.shmem_regions_start = 5,
			.shmem_dev_id = 0,
			.shmem_peers = 2,
			.shmem_protocol = JAILHOUSE_SHMEM_PROTO_VETH,
		},
	},

};