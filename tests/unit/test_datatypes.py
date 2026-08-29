"""
Unit tests for core in-memory data structures: StringStore, HashStore, ListStore, SetStore.
"""

from nomdb.storage.datatypes.string_store import StringStore
from nomdb.storage.datatypes.hash_store import HashStore
from nomdb.storage.datatypes.list_store import ListStore
from nomdb.storage.datatypes.set_store import SetStore


def test_string_store_numeric_ops():
    b_val, i_val = StringStore.incrby(None, 5)
    assert b_val == b"5" and i_val == 5

    b_val, i_val = StringStore.incrby(b"10", 3)
    assert b_val == b"13" and i_val == 13

    b_val, f_val = StringStore.incrbyfloat(b"10.5", 2.25)
    assert f_val == 12.75

    b_val, l_val = StringStore.append(b"hello", b" world")
    assert b_val == b"hello world" and l_val == 11

    assert StringStore.getrange(b"hello world", 0, 4) == b"hello"
    assert StringStore.getrange(b"hello world", -5, -1) == b"world"


def test_hash_store():
    h = HashStore()
    assert h.hset([(b"name", b"Noman"), (b"role", b"engineer")]) == 2
    assert h.hlen() == 2
    assert h.hget(b"name") == b"Noman"
    assert h.hexists(b"role") is True
    assert h.hexists(b"unknown") is False
    assert h.hincrby(b"count", 5) == 5
    assert h.hdel([b"name"]) == 1
    assert h.hget(b"name") is None


def test_list_store():
    lst = ListStore()
    assert lst.rpush([b"a", b"b", b"c"]) == 3
    assert lst.lpush([b"start"]) == 4
    assert lst.llen() == 4
    assert lst.lrange(0, -1) == [b"start", b"a", b"b", b"c"]
    assert lst.lpop(1) == [b"start"]
    assert lst.rpop(1) == [b"c"]
    assert lst.lindex(0) == b"a"
    lst.lset(0, b"updated_a")
    assert lst.lindex(0) == b"updated_a"


def test_set_store():
    s1 = SetStore()
    assert s1.sadd([b"apple", b"banana", b"cherry"]) == 3
    assert s1.scard() == 3
    assert s1.sismember(b"apple") is True
    assert s1.sismember(b"grape") is False

    s2 = SetStore({b"banana", b"date", b"elderberry"})
    inter = SetStore.sinter([s1, s2])
    assert inter == {b"banana"}

    union = SetStore.sunion([s1, s2])
    assert union == {b"apple", b"banana", b"cherry", b"date", b"elderberry"}

    diff = SetStore.sdiff([s1, s2])
    assert diff == {b"apple", b"cherry"}
