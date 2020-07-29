import pytest

from autojail.utils import SortedCollection, get_overlap, remove_prefix


@pytest.mark.parametrize(
    "a, b, res",
    [
        ((0, 1), (1, 2), 0),
        ((0, 2), (1, 2), 1),
        ((0, 2), (0, 2), 2),
        ((0, 5), (1, 3), 2),
    ],
)
def test_overlap(a, b, res):
    assert res == get_overlap(a, b)
    assert res == get_overlap(b, a)


@pytest.mark.parametrize(
    "input, prefix, expected",
    [("pre_test", "pre_", "test"), ("autojail_init", "autojail_", "init"),],
)
def test_remove_prefix(input, prefix, expected):
    assert remove_prefix(input, prefix) == expected


def test_sorted_collection():
    collection = SortedCollection([1, 2, 3])
    collection.insert(3)

    assert list(collection) == [1, 2, 3, 3]
    assert collection.count(3) == 2
    assert collection.count(10) == 0

    collection.remove(1)
    collection.remove(2)
    collection.remove(3)
    collection.remove(3)

    assert list(collection) == []
    assert collection.count(10) == 0
    assert 10 not in collection

    collection.insert(4)
    collection.insert(3)
    collection.insert(2)
    collection.insert(1)

    assert list(collection) == [1, 2, 3, 4]
    assert collection.count(2) == 1
    assert 2 in collection
    assert collection.count(10) == 0

    assert list(reversed(collection)) == [4, 3, 2, 1]

    assert collection[0] == 1
    assert collection[1] == 2
    assert collection[2] == 3
    assert collection[3] == 4

    collection.clear()


def test_sorted_2():
    collection = SortedCollection(key=lambda x: x[0])
    collection.insert((1, "b"))
    collection.insert_right((1, "c"))
    collection.insert((1, "a"))

    assert "".join([x[1] for x in collection]) == "abc"

    assert collection.find(1) == (1, "a")
    assert collection.find_ge(1) == (1, "a")

    collection.insert((2, "a"))
    collection.index((2, "a")) == 4
