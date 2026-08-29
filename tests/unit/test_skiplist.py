"""
Unit tests for SkipList and SortedSetStore data structures.
"""

from nomdb.storage.datatypes.sorted_set_store import SortedSetStore, SkipList


def test_skiplist_insert_and_rank():
    sl = SkipList()
    sl.insert(10.0, b"alice")
    sl.insert(5.0, b"bob")
    sl.insert(20.0, b"charlie")
    sl.insert(15.0, b"david")

    assert sl.length == 4

    # Ranks (1-based)
    assert sl.get_rank(5.0, b"bob") == 1
    assert sl.get_rank(10.0, b"alice") == 2
    assert sl.get_rank(15.0, b"david") == 3
    assert sl.get_rank(20.0, b"charlie") == 4
    assert sl.get_rank(99.0, b"nobody") == 0


def test_skiplist_delete():
    sl = SkipList()
    sl.insert(10.0, b"alice")
    sl.insert(20.0, b"bob")

    assert sl.delete(10.0, b"alice") is True
    assert sl.length == 1
    assert sl.get_rank(20.0, b"bob") == 1
    assert sl.delete(10.0, b"alice") is False


def test_sorted_set_store_full():
    zset = SortedSetStore()
    added = zset.zadd([(100.0, b"player1"), (250.0, b"player2"), (50.0, b"player3")])
    assert added == 3
    assert zset.zcard() == 3

    assert zset.zscore(b"player1") == 100.0
    assert zset.zrank(b"player3") == 0
    assert zset.zrank(b"player1") == 1
    assert zset.zrank(b"player2") == 2

    assert zset.zrevrank(b"player2") == 0
    assert zset.zrevrank(b"player3") == 2

    # Range
    assert zset.zrange(0, 1) == [b"player3", b"player1"]
    assert zset.zrevrange(0, 1) == [b"player2", b"player1"]

    # Increment
    new_score = zset.zincrby(200.0, b"player3")
    assert new_score == 250.0
    assert zset.zscore(b"player3") == 250.0

    # Count
    assert zset.zcount(100.0, 300.0) == 3

    # Remove
    assert zset.zrem([b"player1"]) == 1
    assert zset.zcard() == 2
