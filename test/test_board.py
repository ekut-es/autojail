from autojail.model.board import Board


def test_board():
    test_data = {
        "id": "test_id",
        "name": "test_name",
        "board": "test_board",
        "memory_regions": {
            "test_region": {
                "virtual_start_addr": 0x1000,
                "physical_start_addr": 0x1000,
                "size": 100,
                "flags": ["MEM_READ"],
            }
        },
    }

    board_model = Board(**test_data)

    assert board_model.id == "test_id"
    assert (
        board_model.memory_regions["test_region"].virtual_start_addr == 0x1000
    )
    assert (
        board_model.memory_regions["test_region"].physical_start_addr == 0x1000
    )
    assert board_model.memory_regions["test_region"].size == 100

