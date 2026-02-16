"""Integration test: IPC roundtrip between Python client and mock WhatsApp server."""

import asyncio

import pytest
import pytest_asyncio

from brain.core.events import ConnectionChanged, EventBus, MessageReceived
from brain.ipc.client import IPCClient
from brain.tests.fixtures.mock_whatsapp import MockWhatsAppServer

SOCKET_PATH = "/tmp/outbot-ipc-test.sock"


@pytest_asyncio.fixture
async def mock_server():
    """Start a mock WhatsApp IPC server."""
    server = MockWhatsAppServer(SOCKET_PATH)
    await server.start()
    yield server
    await server.stop()


@pytest_asyncio.fixture
async def ipc_client(mock_server):
    """Connect an IPC client to the mock server."""
    event_bus = EventBus()
    client = IPCClient(SOCKET_PATH, event_bus)
    await client.connect(retries=3, delay=0.5)
    yield client, event_bus
    await client.disconnect()


class TestIPCRoundtrip:
    @pytest.mark.asyncio
    async def test_send_message_arrives_at_server(self, mock_server, ipc_client):
        client, _ = ipc_client
        await client.send_message("troy@s.whatsapp.net", "Hello Troy!")
        await asyncio.sleep(0.1)  # Let server process

        assert len(mock_server.sent_messages) == 1
        assert mock_server.sent_messages[0]["chat_jid"] == "troy@s.whatsapp.net"
        assert mock_server.sent_messages[0]["text"] == "Hello Troy!"

    @pytest.mark.asyncio
    async def test_typing_indicator(self, mock_server, ipc_client):
        client, _ = ipc_client
        jid = "troy@s.whatsapp.net"

        await client.set_typing(jid, True)
        await asyncio.sleep(0.1)
        assert mock_server.typing_states.get(jid) is True

        await client.set_typing(jid, False)
        await asyncio.sleep(0.1)
        assert mock_server.typing_states.get(jid) is False

    @pytest.mark.asyncio
    async def test_receive_message_publishes_event(self, mock_server, ipc_client):
        client, event_bus = ipc_client
        received = []
        event_bus.subscribe(MessageReceived, lambda e: received.append(e))

        await mock_server.inject_message(
            chat_jid="troy@s.whatsapp.net",
            sender="61400000000@s.whatsapp.net",
            sender_name="Troy",
            content="Hey OutBot!",
        )
        await asyncio.sleep(0.2)  # Let read loop process

        assert len(received) == 1
        assert received[0].message.content == "Hey OutBot!"
        assert received[0].message.sender_name == "Troy"
        assert received[0].chat_jid == "troy@s.whatsapp.net"

    @pytest.mark.asyncio
    async def test_multiple_messages_roundtrip(self, mock_server, ipc_client):
        client, event_bus = ipc_client
        received = []
        event_bus.subscribe(MessageReceived, lambda e: received.append(e))

        # Send outgoing
        await client.send_message("troy@s.whatsapp.net", "Message 1")
        await client.send_message("troy@s.whatsapp.net", "Message 2")

        # Inject incoming
        await mock_server.inject_message(
            chat_jid="troy@s.whatsapp.net",
            sender="61400000000@s.whatsapp.net",
            sender_name="Troy",
            content="Reply 1",
        )

        await asyncio.sleep(0.2)

        assert len(mock_server.sent_messages) == 2
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_client_connection_state(self, mock_server, ipc_client):
        client, _ = ipc_client
        assert client.connected is True

        await client.disconnect()
        assert client.connected is False
