# Configuration File Format

Autojail target configurations are written in a YAML based configuration format.

The configuration file format contains a bit of Syntactic Sugar:

- Lists of Integers can usually contain ranges, e.g. 1,4-5 is equivalent to 1,4,5 .
- Flags can omit the JAILHOUSE\_ prefix
- Memory sizes can be given using ISO/IEC 8000 (KiB, MiB, ...) or JEDEC binary (KB, MB, ...) units, e.g: 10 MB
  for a `10 * 2^20` Byte sized memory region.  
  We never use base 10 SI-units.

## Cell Configuration

The cells are configured in section `cells` of the configuration file consisting of
a dict of cell configurations. The keys are used to uniquely identify a cell configuration.

The cell configuration is modeled after the original jailhouse configuration format.
It consists of the following sections:

_type_ (`str`)
: This identifies the type of Cell, we currently distinguish between `root`, `linux` and `bare` e.g. bare metal cells.

_name_ (`str`)
: The name used for this cell. Used to identify the cell in jailhouse and to derive the jailhouse configuration file names.

_vpci_irq_base_ (optional, `int`)
: The virtual pci base interrupt. Can be derived automatically.

_hypervisor_memory_ (optional, `HypervisorMemoryConfig`)
: Hypervisor memory configuration format. Only the size must be configured, the rest of the fields are optional.

_platform_info_ (optional, `PlatformInfo`)
: Optional target specific configuration. Should normally be omitted.

_platform_info_ (optional, `dict` of `MemoryRegion` or `str`)
: Used to configure RAM and device resources used by a cell.
One can either configure a MemoryRegion directly or use a string to identify a device tree
item either by its full path or its alias.

_debug_console_ (`dict` of `DebugConsole` or `str`):
: One can either configure the DebugConsole directly or use the device tree path or alias of the uart device.

_cpus_ (optional, `IntegerList`):
: List of CPUs used by this cell. If left out one CPU will be automatically assigned to the cell.

_irqchips_ (optional, `dict` of `IRQChip`)
: Dict of irq chip configurations. Should usually be left empty and will be configured automatically.

_pci_devices_ (optional, `dict` of `PCIDevices`)
: Can be used in conjunction with `memory_regions` to setup inter-cell communication. Usage with non virtual PCI devices is not tested at the moment.
If possible it es recommended to use the global shmem config to setup inter-cell communication.

Most jailhouse configuration files are also valid _autojail_ configs when directly translated
to jailhouse config format. In the future we might provide tooling to directly import
jailhouse configurations in .c or .cell format.

## Communication Configuration

Communication between cells can be configured using a high-level configuration in the `shmem`
section of the configuration file. The shmem config consist of a Dict of `ShmemConfig`
entries. One ShmemConfig entry has the following fields:

_protocol_ (str)
: the type of Protocol, currently SHMEM\*PROTO_VETH is supported

_peers_ (list of str)
: list of cell ids participating in the communication

_common_output_region_size_ (optional ByteSize)
: Size of common output region (currently not used)

_per_device_region_size_ (optinal, ByteSize)
: Size of each devices output region (currently not used)

Currently only virtual ethernet communication is supported.

Communication between cells can also be configured using memory regions and pci device regions
of the individual cells.
