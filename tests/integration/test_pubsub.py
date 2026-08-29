"""
Integration tests for Pub/Sub channels and pattern subscriptions.
"""

import socket
import pytest
from nomdb.client.client import Client
from nomdb.protocol.encoder import RESPEncoder
from nomdb.protocol.parser import RESPParser


def test_pubsub_channels_and_patterns(running_server):
    # 1. Open dedicated raw socket connection for subscriber
    sub_sock = socket.create_connection(
        (running_server.settings.host, running_server.settings.port), timeout=5.0
    )

    # 2. Subscribe to 'chat' and 'news.*'
    sub_sock.sendall(RESPEncoder.encode_command("SUBSCRIBE", "chat"))
    sub_sock.sendall(RESPEncoder.encode_command("PSUBSCRIBE", "news.*"))

    parser = RESPParser()
    # Read subscription confirmations
    while len(parser.get_parsed_commands()) < 2:
        chunk = sub_sock.recv(4096)
        if not chunk:
            break
        parser.feed(chunk)

    # 3. Publish using regular client
    pub_client = Client(host=running_server.settings.host, port=running_server.settings.port)
    rec1 = pub_client.execute_command("PUBLISH", "chat", "Hello Chat!")
    assert rec1 == 1

    rec2 = pub_client.execute_command("PUBLISH", "news.tech", "Breaking Tech!")
    assert rec2 == 1

    # 4. Subscriber receives the broadcast messages
    messages = []
    while len(messages) < 2:
        chunk = sub_sock.recv(4096)
        if not chunk:
            break
        parser.feed(chunk)
        cmds = parser.get_parsed_commands()
        messages.extend(cmds)

    assert messages[0] == [b"message", b"chat", b"Hello Chat!"]
    assert messages[1] == [b"pmessage", b"news.*", b"news.tech", b"Breaking Tech!"]

    sub_sock.close()
    pub_client.close()
