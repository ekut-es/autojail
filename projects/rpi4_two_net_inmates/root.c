#include <jailhouse/types.h>
#include <jailhouse/cell-config.h>
struct { 
	struct jailhouse_system header; 
	__u64 cpus[1];
	struct jailhouse_memory mem_regions[38];
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
		.pci_mmconfig_base = 0xfefff000,
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
	/*System RAM 0x0-0x40000000*/	{
		.phys_start = 0x0,
		.virt_start = 0x0,
		.size = 0x40000000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_EXECUTE,
	},
	/*net1_0 0xfbffd000-0xfbffe000*/	{
		.phys_start = 0xfbffd000,
		.virt_start = 0xfbffd000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED,
	},
	/* empty optional region */ { 0 },
	/*net1_2 0xfbffe000-0xfbfff000*/	{
		.phys_start = 0xfbffe000,
		.virt_start = 0xfbffe000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED|JAILHOUSE_MEM_WRITE,
	},
	/*net1_3 0xfbfff000-0xfc000000*/	{
		.phys_start = 0xfbfff000,
		.virt_start = 0xfbfff000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED,
	},
	/*net2_0 0xfbffa000-0xfbffb000*/	{
		.phys_start = 0xfbffa000,
		.virt_start = 0xfbffa000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED,
	},
	/* empty optional region */ { 0 },
	/*net2_2 0xfbffb000-0xfbffc000*/	{
		.phys_start = 0xfbffb000,
		.virt_start = 0xfbffb000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED|JAILHOUSE_MEM_WRITE,
	},
	/*net2_3 0xfbffc000-0xfbffd000*/	{
		.phys_start = 0xfbffc000,
		.virt_start = 0xfbffc000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED,
	},
	/*System RAM_2 0x40000000-0xebfd9000*/	{
		.phys_start = 0x40000000,
		.virt_start = 0x40000000,
		.size = 0xabfd9000,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_EXECUTE,
	},
	/*fd500000.pcie 0xfd500000-0xfd509310*/	{
		.phys_start = 0xfd500000,
		.virt_start = 0xfd500000,
		.size = 0x9310,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO | JAILHOUSE_MEM_IO_8 | JAILHOUSE_MEM_IO_16 | JAILHOUSE_MEM_IO_32 | JAILHOUSE_MEM_IO_64,
	},
	/*fd580000.genet 0xfd580000-0xfd590000*/	{
		.phys_start = 0xfd580000,
		.virt_start = 0xfd580000,
		.size = 0x10000,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO | JAILHOUSE_MEM_IO_8 | JAILHOUSE_MEM_IO_16 | JAILHOUSE_MEM_IO_32 | JAILHOUSE_MEM_IO_64,
	},
	/*fd5d2200.thermal 0xfd5d2200-0xfd5d222c*/	{
		.phys_start = 0xfd5d2200,
		.virt_start = 0xfd5d2200,
		.size = 0x2c,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO | JAILHOUSE_MEM_IO_8 | JAILHOUSE_MEM_IO_16 | JAILHOUSE_MEM_IO_32 | JAILHOUSE_MEM_IO_64,
	},
	/*fe007000.dma 0xfe007000-0xfe007b00*/	{
		.phys_start = 0xfe007000,
		.virt_start = 0xfe007000,
		.size = 0xb00,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO | JAILHOUSE_MEM_IO_8 | JAILHOUSE_MEM_IO_16 | JAILHOUSE_MEM_IO_32 | JAILHOUSE_MEM_IO_64,
	},
	/*fe007b00.dma 0xfe007b00-0xfe007f00*/	{
		.phys_start = 0xfe007b00,
		.virt_start = 0xfe007b00,
		.size = 0x400,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO | JAILHOUSE_MEM_IO_8 | JAILHOUSE_MEM_IO_16 | JAILHOUSE_MEM_IO_32 | JAILHOUSE_MEM_IO_64,
	},
	/*fe100000.watchdog 0xfe00a000-0xfe00a024*/	{
		.phys_start = 0xfe00a000,
		.virt_start = 0xfe00a000,
		.size = 0x24,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO | JAILHOUSE_MEM_IO_8 | JAILHOUSE_MEM_IO_16 | JAILHOUSE_MEM_IO_32 | JAILHOUSE_MEM_IO_64,
	},
	/*dwc_otg 0xfe00b200-0xfe00b400*/	{
		.phys_start = 0xfe00b200,
		.virt_start = 0xfe00b200,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO | JAILHOUSE_MEM_IO_8 | JAILHOUSE_MEM_IO_16 | JAILHOUSE_MEM_IO_32 | JAILHOUSE_MEM_IO_64,
	},
	/*fe00b840.mailbox 0xfe00b840-0xfe00b87c*/	{
		.phys_start = 0xfe00b840,
		.virt_start = 0xfe00b840,
		.size = 0x3c,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO | JAILHOUSE_MEM_IO_8 | JAILHOUSE_MEM_IO_16 | JAILHOUSE_MEM_IO_32 | JAILHOUSE_MEM_IO_64,
	},
	/*fe00b880.mailbox 0xfe00b880-0xfe00b8c0*/	{
		.phys_start = 0xfe00b880,
		.virt_start = 0xfe00b880,
		.size = 0x40,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO | JAILHOUSE_MEM_IO_8 | JAILHOUSE_MEM_IO_16 | JAILHOUSE_MEM_IO_32 | JAILHOUSE_MEM_IO_64,
	},
	/*fe100000.watchdog_2 0xfe100000-0xfe100114*/	{
		.phys_start = 0xfe100000,
		.virt_start = 0xfe100000,
		.size = 0x114,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO | JAILHOUSE_MEM_IO_8 | JAILHOUSE_MEM_IO_16 | JAILHOUSE_MEM_IO_32 | JAILHOUSE_MEM_IO_64,
	},
	/*fe101000.cprman 0xfe101000-0xfe103000*/	{
		.phys_start = 0xfe101000,
		.virt_start = 0xfe101000,
		.size = 0x2000,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO | JAILHOUSE_MEM_IO_8 | JAILHOUSE_MEM_IO_16 | JAILHOUSE_MEM_IO_32 | JAILHOUSE_MEM_IO_64,
	},
	/*fe104000.rng 0xfe104000-0xfe104010*/	{
		.phys_start = 0xfe104000,
		.virt_start = 0xfe104000,
		.size = 0x10,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO | JAILHOUSE_MEM_IO_8 | JAILHOUSE_MEM_IO_16 | JAILHOUSE_MEM_IO_32 | JAILHOUSE_MEM_IO_64,
	},
	/*fe200000.gpio 0xfe200000-0xfe2000b4*/	{
		.phys_start = 0xfe200000,
		.virt_start = 0xfe200000,
		.size = 0xb4,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO | JAILHOUSE_MEM_IO_8 | JAILHOUSE_MEM_IO_16 | JAILHOUSE_MEM_IO_32 | JAILHOUSE_MEM_IO_64,
	},
	/*serial@7e201000 0xfe201000-0xfe201200*/	{
		.phys_start = 0xfe201000,
		.virt_start = 0xfe201000,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO | JAILHOUSE_MEM_IO_8 | JAILHOUSE_MEM_IO_16 | JAILHOUSE_MEM_IO_32 | JAILHOUSE_MEM_IO_64,
	},
	/*fe204000.spi 0xfe204000-0xfe204200*/	{
		.phys_start = 0xfe204000,
		.virt_start = 0xfe204000,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO | JAILHOUSE_MEM_IO_8 | JAILHOUSE_MEM_IO_16 | JAILHOUSE_MEM_IO_32 | JAILHOUSE_MEM_IO_64,
	},
	/*fe215000.aux 0xfe215000-0xfe215008*/	{
		.phys_start = 0xfe215000,
		.virt_start = 0xfe215000,
		.size = 0x8,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO | JAILHOUSE_MEM_IO_8 | JAILHOUSE_MEM_IO_16 | JAILHOUSE_MEM_IO_32 | JAILHOUSE_MEM_IO_64,
	},
	/*fe215040.serial 0xfe215040-0xfe215080*/	{
		.phys_start = 0xfe215040,
		.virt_start = 0xfe215040,
		.size = 0x40,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO | JAILHOUSE_MEM_IO_8 | JAILHOUSE_MEM_IO_16 | JAILHOUSE_MEM_IO_32 | JAILHOUSE_MEM_IO_64,
	},
	/*fe300000.mmcnr 0xfe300000-0xfe300100*/	{
		.phys_start = 0xfe300000,
		.virt_start = 0xfe300000,
		.size = 0x100,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO | JAILHOUSE_MEM_IO_8 | JAILHOUSE_MEM_IO_16 | JAILHOUSE_MEM_IO_32 | JAILHOUSE_MEM_IO_64,
	},
	/*fe340000.emmc2 0xfe340000-0xfe340100*/	{
		.phys_start = 0xfe340000,
		.virt_start = 0xfe340000,
		.size = 0x100,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO | JAILHOUSE_MEM_IO_8 | JAILHOUSE_MEM_IO_16 | JAILHOUSE_MEM_IO_32 | JAILHOUSE_MEM_IO_64,
	},
	/*fe804000.i2c 0xfe804000-0xfe805000*/	{
		.phys_start = 0xfe804000,
		.virt_start = 0xfe804000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO | JAILHOUSE_MEM_IO_8 | JAILHOUSE_MEM_IO_16 | JAILHOUSE_MEM_IO_32 | JAILHOUSE_MEM_IO_64,
	},
	/*dwc_otg_2 0xfe980000-0xfe990000*/	{
		.phys_start = 0xfe980000,
		.virt_start = 0xfe980000,
		.size = 0x10000,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO | JAILHOUSE_MEM_IO_8 | JAILHOUSE_MEM_IO_16 | JAILHOUSE_MEM_IO_32 | JAILHOUSE_MEM_IO_64,
	},
	/*fe100000.watchdog_3 0xfec11000-0xfec11020*/	{
		.phys_start = 0xfec11000,
		.virt_start = 0xfec11000,
		.size = 0x20,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO | JAILHOUSE_MEM_IO_8 | JAILHOUSE_MEM_IO_16 | JAILHOUSE_MEM_IO_32 | JAILHOUSE_MEM_IO_64,
	},
	/*pcie@7d500000 0x600000000-0x604000000*/	{
		.phys_start = 0x600000000,
		.virt_start = 0x600000000,
		.size = 0x4000000,
		.flags = JAILHOUSE_MEM_READ | JAILHOUSE_MEM_WRITE | JAILHOUSE_MEM_IO | JAILHOUSE_MEM_IO_8 | JAILHOUSE_MEM_IO_16 | JAILHOUSE_MEM_IO_32 | JAILHOUSE_MEM_IO_64,
	},
	/*linux1_RAM 1 0xfbfea000-0xfbffa000*/	{
		.phys_start = 0xfbfea000,
		.virt_start = 0xfbfea000,
		.size = 0x10000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_EXECUTE|JAILHOUSE_MEM_LOADABLE,
	},
	/*linux1_RAM 2 0xf3fea000-0xfbfea000*/	{
		.phys_start = 0xf3fea000,
		.virt_start = 0xf3fea000,
		.size = 0x8000000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_EXECUTE|JAILHOUSE_MEM_DMA|JAILHOUSE_MEM_LOADABLE,
	},
	/*linux1_communication_region 0xf3fe9000-0xf3fea000*/	{
		.phys_start = 0xf3fe9000,
		.virt_start = 0xf3fe9000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_COMM_REGION,
	},
	/*linux2_RAM 2.1 0xf3fd9000-0xf3fe9000*/	{
		.phys_start = 0xf3fd9000,
		.virt_start = 0xf3fd9000,
		.size = 0x10000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_EXECUTE|JAILHOUSE_MEM_LOADABLE,
	},
	/*linux2_RAM 2.2 0xebfd9000-0xf3fd9000*/	{
		.phys_start = 0xebfd9000,
		.virt_start = 0xebfd9000,
		.size = 0x8000000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_EXECUTE|JAILHOUSE_MEM_DMA|JAILHOUSE_MEM_LOADABLE,
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