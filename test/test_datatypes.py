from pydantic import BaseModel

from autojail.model.datatypes import IntegerList


def test_integer_list_constructor():
    my_list = IntegerList([3])
    assert 3 in my_list


class ModelForTest(BaseModel):
    lst: IntegerList


def test_integer_list_model():

    m1 = ModelForTest(lst="3")
    m2 = ModelForTest(lst=[])
    m3 = ModelForTest(lst="1-3")

    assert 3 in m1.lst
    assert len(m2.lst) == 0
    assert 1 in m3.lst
    assert 2 in m3.lst
    assert 3 in m3.lst
    assert 4 not in m3.lst


def test_integer_list_assignment():
    m1 = ModelForTest(lst=[])

    m1.lst = IntegerList.validate("3")  # noqa

    assert isinstance(m1.lst, list)

    assert 3 in m1.lst
