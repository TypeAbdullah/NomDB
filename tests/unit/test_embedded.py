import pytest
from nomdb.embedded import NomDB, open_db

def test_embedded_nomdb_basic_ops(temp_data_dir):
    db_file = temp_data_dir / "embedded.nomdb"
    db = open_db(path=db_file)

    # String
    db.set("user", "Alice")
    assert db.get("user") == b"Alice"
    assert db.get_str("user") == "Alice"
    assert db.incr("visits", 1) == 1
    assert db.incr("visits", 5) == 6

    # Hash
    db.hset("profile", mapping={"name": "Alice", "city": "SF"})
    assert db.hget("profile", "name") == b"Alice"
    assert db.hgetall("profile") == {"name": "Alice", "city": "SF"}

    # List
    db.rpush("todos", "task1", "task2")
    assert db.lrange("todos", 0, -1) == ["task1", "task2"]
    assert db.lpop("todos") == b"task1"

    # Set
    db.sadd("skills", "python", "db")
    assert set(db.smembers("skills")) == {"python", "db"}

    # Sorted Set
    db.zadd("scores", {"player1": 100.0, "player2": 250.0})
    assert db.zscore("scores", "player2") == 250.0

    db.close()

    # Reopen and test persistence
    db2 = open_db(path=db_file)
    assert db2.get_str("user") == "Alice"
    assert db2.hget("profile", "name") == b"Alice"
    db2.close()
