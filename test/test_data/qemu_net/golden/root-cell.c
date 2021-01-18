#include <jailhouse/types.h>
#include <jailhouse/cell-config.h>
struct { 
	struct jailhouse_system header; 
	__u64 cpus[1];
	struct jailhouse_memory mem_regions[52];
	struct jailhouse_irqchip irqchips[1];
	struct jailhouse_pci_device pci_devices[2];
} __attribute__((packed)) config = {

.header = {
	.signature = JAILHOUSE_SYSTEM_SIGNATURE,
	.revision = JAILHOUSE_CONFIG_REVISION,
	.hypervisor_memory = {
		.phys_start = 0xa0800000,
		.size = 0x800000,
	},

	.debug_console = {
		.address = 0x9000000,
		.size = 0x1000,
		.type = JAILHOUSE_CON_TYPE_PL011,
		.flags = JAILHOUSE_CON_ACCESS_MMIO | JAILHOUSE_CON_REGDIST_4,
	},

	.platform_info = {
		.pci_mmconfig_base = 0x60006000,
		.pci_mmconfig_end_bus = 0,
		.pci_is_virtual = 1,
		.pci_domain = 1,
		.arm = {
			.maintenance_irq = 25,
			.gic_version = 3,
			.gicd_base = 0x8000000,
			.gicc_base = 0x8010000,
			.gich_base = 0x8030000,
			.gicv_base = 0x8040000,
			.gicr_base = 0x80a0000,
		},

	},

	.root_cell = {
		.name = "root cell" ,
		.vpci_irq_base = 35- 32,
		.num_memory_regions = ARRAY_SIZE(config.mem_regions),
		.num_pci_devices = ARRAY_SIZE(config.pci_devices),
		.cpu_set_size = sizeof(config.cpus),
		.num_irqchips = ARRAY_SIZE(config.irqchips),
	},
	},
	.cpus = {0b1111111111111111},
	
	.mem_regions = {
	/*Main Memory 0x40000000-0x60000000*/
	{
		.phys_start = 0x40000000,
		.virt_start = 0xa004000,
		.size = 0x20000000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_EXECUTE|JAILHOUSE_MEM_DMA,
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
		.virt_start = 0x8000000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED,
	},
	/* empty optional region */
	{ 0 },
	/*net1 0x60001000-0x60002000*/
	{
		.phys_start = 0x60001000,
		.virt_start = 0x8001000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED|JAILHOUSE_MEM_WRITE,
	},
	/*net1 0x60002000-0x60003000*/
	{
		.phys_start = 0x60002000,
		.virt_start = 0x8002000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED,
	},
	/*net2 0x60003000-0x60004000*/
	{
		.phys_start = 0x60003000,
		.virt_start = 0x8003000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED,
	},
	/* empty optional region */
	{ 0 },
	/*net2 0x60004000-0x60005000*/
	{
		.phys_start = 0x60004000,
		.virt_start = 0x8004000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED|JAILHOUSE_MEM_WRITE,
	},
	/*net2 0x60005000-0x60006000*/
	{
		.phys_start = 0x60005000,
		.virt_start = 0x8005000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_ROOTSHARED,
	},
	/*flash@0 0x0-0x4000000*/
	{
		.phys_start = 0x0,
		.virt_start = 0x0,
		.size = 0x4000000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*flash@0.0 0x4000000-0x8000000*/
	{
		.phys_start = 0x4000000,
		.virt_start = 0x4000000,
		.size = 0x4000000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*pl031@9010000 0x9010000-0x9011000*/
	{
		.phys_start = 0x9010000,
		.virt_start = 0x9010000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*fw-cfg@9020000 0x9020000-0x9020018*/
	{
		.phys_start = 0x9020000,
		.virt_start = 0x9020000,
		.size = 0x18,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*pl061@9030000 0x9030000-0x9031000*/
	{
		.phys_start = 0x9030000,
		.virt_start = 0x9030000,
		.size = 0x1000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a000000 0xa000000-0xa000200*/
	{
		.phys_start = 0xa000000,
		.virt_start = 0xa000000,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a000200 0xa000200-0xa000400*/
	{
		.phys_start = 0xa000200,
		.virt_start = 0xa000200,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a000400 0xa000400-0xa000600*/
	{
		.phys_start = 0xa000400,
		.virt_start = 0xa000400,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a000600 0xa000600-0xa000800*/
	{
		.phys_start = 0xa000600,
		.virt_start = 0xa000600,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a000800 0xa000800-0xa000a00*/
	{
		.phys_start = 0xa000800,
		.virt_start = 0xa000800,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a000a00 0xa000a00-0xa000c00*/
	{
		.phys_start = 0xa000a00,
		.virt_start = 0xa000a00,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a000c00 0xa000c00-0xa000e00*/
	{
		.phys_start = 0xa000c00,
		.virt_start = 0xa000c00,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a000e00 0xa000e00-0xa001000*/
	{
		.phys_start = 0xa000e00,
		.virt_start = 0xa000e00,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a001000 0xa001000-0xa001200*/
	{
		.phys_start = 0xa001000,
		.virt_start = 0xa001000,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a001200 0xa001200-0xa001400*/
	{
		.phys_start = 0xa001200,
		.virt_start = 0xa001200,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a001400 0xa001400-0xa001600*/
	{
		.phys_start = 0xa001400,
		.virt_start = 0xa001400,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a001600 0xa001600-0xa001800*/
	{
		.phys_start = 0xa001600,
		.virt_start = 0xa001600,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a001800 0xa001800-0xa001a00*/
	{
		.phys_start = 0xa001800,
		.virt_start = 0xa001800,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a001a00 0xa001a00-0xa001c00*/
	{
		.phys_start = 0xa001a00,
		.virt_start = 0xa001a00,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a001c00 0xa001c00-0xa001e00*/
	{
		.phys_start = 0xa001c00,
		.virt_start = 0xa001c00,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a001e00 0xa001e00-0xa002000*/
	{
		.phys_start = 0xa001e00,
		.virt_start = 0xa001e00,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a002000 0xa002000-0xa002200*/
	{
		.phys_start = 0xa002000,
		.virt_start = 0xa002000,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a002200 0xa002200-0xa002400*/
	{
		.phys_start = 0xa002200,
		.virt_start = 0xa002200,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a002400 0xa002400-0xa002600*/
	{
		.phys_start = 0xa002400,
		.virt_start = 0xa002400,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a002600 0xa002600-0xa002800*/
	{
		.phys_start = 0xa002600,
		.virt_start = 0xa002600,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a002800 0xa002800-0xa002a00*/
	{
		.phys_start = 0xa002800,
		.virt_start = 0xa002800,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a002a00 0xa002a00-0xa002c00*/
	{
		.phys_start = 0xa002a00,
		.virt_start = 0xa002a00,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a002c00 0xa002c00-0xa002e00*/
	{
		.phys_start = 0xa002c00,
		.virt_start = 0xa002c00,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a002e00 0xa002e00-0xa003000*/
	{
		.phys_start = 0xa002e00,
		.virt_start = 0xa002e00,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a003000 0xa003000-0xa003200*/
	{
		.phys_start = 0xa003000,
		.virt_start = 0xa003000,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a003200 0xa003200-0xa003400*/
	{
		.phys_start = 0xa003200,
		.virt_start = 0xa003200,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a003400 0xa003400-0xa003600*/
	{
		.phys_start = 0xa003400,
		.virt_start = 0xa003400,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a003600 0xa003600-0xa003800*/
	{
		.phys_start = 0xa003600,
		.virt_start = 0xa003600,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a003800 0xa003800-0xa003a00*/
	{
		.phys_start = 0xa003800,
		.virt_start = 0xa003800,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a003a00 0xa003a00-0xa003c00*/
	{
		.phys_start = 0xa003a00,
		.virt_start = 0xa003a00,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a003c00 0xa003c00-0xa003e00*/
	{
		.phys_start = 0xa003c00,
		.virt_start = 0xa003c00,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*virtio_mmio@a003e00 0xa003e00-0xa004000*/
	{
		.phys_start = 0xa003e00,
		.virt_start = 0xa003e00,
		.size = 0x200,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64,
	},
	/*mmio_0 0x4010000000-0x4020000000*/
	{
		.phys_start = 0x4010000000,
		.virt_start = 0x4010000000,
		.size = 0x10000000,
		.flags = JAILHOUSE_MEM_IO|JAILHOUSE_MEM_IO_16|JAILHOUSE_MEM_IO_32|JAILHOUSE_MEM_IO_64|JAILHOUSE_MEM_IO_8|JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*boot@guest 0x60106000-0x60206000*/
	{
		.phys_start = 0x60106000,
		.virt_start = 0x60106000,
		.size = 0x100000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*main@guest 0x60206000-0x80206000*/
	{
		.phys_start = 0x60206000,
		.virt_start = 0x60206000,
		.size = 0x20000000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_DMA,
	},
	/*boot@guest1 0x80207000-0x80307000*/
	{
		.phys_start = 0x80207000,
		.virt_start = 0x80207000,
		.size = 0x100000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE,
	},
	/*main@guest1 0x80307000-0xa0307000*/
	{
		.phys_start = 0x80307000,
		.virt_start = 0x80307000,
		.size = 0x20000000,
		.flags = JAILHOUSE_MEM_READ|JAILHOUSE_MEM_WRITE|JAILHOUSE_MEM_DMA,
	},
	},
	.irqchips = {
		{
			.address = 0x8000000,
			.pin_base = 32,
			.pin_bitmap = {
				0xffff00ff, 
				0xffff, 
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
		/*net2*/
		{
			.type = JAILHOUSE_PCI_TYPE_IVSHMEM,
			.domain = 1,
			.bar_mask = JAILHOUSE_IVSHMEM_BAR_MASK_INTX,
			.bdf = 0 << 8 | 1 << 3 | 0,
			.shmem_regions_start = 6,
			.shmem_dev_id = 0,
			.shmem_peers = 2,
			.shmem_protocol = JAILHOUSE_SHMEM_PROTO_VETH,
		},
	},

};