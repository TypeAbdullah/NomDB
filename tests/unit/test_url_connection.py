import pytest
import nomdb

def test_from_url_embedded(temp_data_dir):
    db_file = temp_data_dir / "url_test.db"
    db = nomdb.connect(f"nomdb://{db_file}")
    db.set("key_url", "val_url")
    assert db.get_str("key_url") == "val_url"
    db.close()

def test_from_url_client():
    client = nomdb.from_url("nomdb://127.0.0.1:6379/0")
    assert client.host == "127.0.0.1"
    assert client.port == 6379
