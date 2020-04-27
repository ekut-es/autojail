import os.path
import yaml

from autojail.model import ShmemConfig

test_data_folder = os.path.join(os.path.dirname(__file__), "test_data")


def test_shmem_config_yaml():
    shmem_yaml = os.path.join(test_data_folder, "test_shmem_config.yml")
    with open(shmem_yaml) as shmem_yaml_file:
        shmem_dict = yaml.safe_load(shmem_yaml_file)
        shmem_model = ShmemConfig(**shmem_dict)

        assert shmem_model.protocol == "SHMEM_PROTO_UNDEFINED"
        assert "root" in shmem_model.peers
        assert shmem_model.common_output_region_size == 0x9000
