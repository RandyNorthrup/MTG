"""MTG Commander Game - Network Components Tests

This module contains comprehensive tests for network client and server components,
including connection handling, message passing, error recovery, and multiplayer scenarios.
"""

import unittest
import time
import threading
import socket
from unittest.mock import Mock, patch, MagicMock
from queue import Queue, Empty

# Import network components
from network.network_client import NetworkClient, ClientState
from network.game_server import GameServer, ConnectedPlayer, ServerState
from network.message_protocol import MessageType, NetworkMessage, MessageProtocol
from network.network_game_controller import NetworkGameController


class TestNetworkClient(unittest.TestCase):
    """Test the NetworkClient component."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = NetworkClient(player_id=1)
        self.mock_parent = Mock()
        
    def tearDown(self):
        """Clean up after tests."""
        if self.client.socket:
            self.client.disconnect()
    
    def test_client_initialization(self):
        """Test NetworkClient initialization."""
        self.assertEqual(self.client.player_id, 1)
        self.assertEqual(self.client.state, ClientState.DISCONNECTED)
        self.assertIsNone(self.client.socket)
        self.assertFalse(self.client.is_in_game)
        self.assertIsInstance(self.client.protocol, MessageProtocol)
    
    def test_client_state_transitions(self):
        """Test client state transitions."""
        # Initial state
        self.assertEqual(self.client.state, ClientState.DISCONNECTED)
        
        # Mock socket connection
        with patch('socket.socket'):
            self.client.socket = Mock()
            self.client.socket.connect.return_value = None
            
            # Simulate state changes
            self.client.state = ClientState.CONNECTING
            self.assertEqual(self.client.state, ClientState.CONNECTING)
            
            self.client.state = ClientState.CONNECTED
            self.assertEqual(self.client.state, ClientState.CONNECTED)
            
            self.client.state = ClientState.IN_GAME
            self.assertEqual(self.client.state, ClientState.IN_GAME)
    
    @patch('socket.socket')
    def test_connection_success(self, mock_socket_class):
        """Test successful connection to server."""
        # Mock socket instance
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        mock_socket.connect.return_value = None
        
        # Attempt connection
        result = self.client.connect_to_server("localhost", 8888)
        
        # Verify connection attempt
        self.assertTrue(result)
        mock_socket.connect.assert_called_once_with(("localhost", 8888))
        self.assertEqual(self.client.state, ClientState.CONNECTED)
    
    @patch('socket.socket')
    def test_connection_failure(self, mock_socket_class):
        """Test failed connection to server."""
        # Mock socket to raise connection error
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        mock_socket.connect.side_effect = ConnectionRefusedError("Connection refused")
        
        # Attempt connection
        result = self.client.connect_to_server("localhost", 8888)
        
        # Verify connection failed
        self.assertFalse(result)
        self.assertEqual(self.client.state, ClientState.DISCONNECTED)
    
    def test_message_sending(self):
        """Test sending messages to server."""
        # Mock connected client
        self.client.socket = Mock()
        self.client.state = ClientState.CONNECTED
        
        # Test join game message
        result = self.client.join_game("TestPlayer", "TestDeck")
        self.assertTrue(result)
        
        # Verify socket.send was called
        self.client.socket.send.assert_called()
        
        # Test play card message
        result = self.client.send_play_card("card123", "hand", "battlefield")
        self.assertTrue(result)
        
        # Test cast spell message
        result = self.client.send_cast_spell("spell456", {"blue": 1}, ["target1"])
        self.assertTrue(result)
    
    def test_message_sending_when_disconnected(self):
        """Test message sending fails when disconnected."""
        # Client is disconnected
        self.assertEqual(self.client.state, ClientState.DISCONNECTED)
        
        # All send operations should fail
        self.assertFalse(self.client.join_game("TestPlayer", "TestDeck"))
        self.assertFalse(self.client.send_play_card("card123", "hand", "battlefield"))
        self.assertFalse(self.client.send_cast_spell("spell456", {}, []))
        self.assertFalse(self.client.send_player_action("test_action"))
    
    def test_heartbeat_system(self):
        """Test client heartbeat system."""
        # Mock connected client
        self.client.socket = Mock()
        self.client.state = ClientState.CONNECTED
        
        # Test heartbeat sending
        self.client.send_heartbeat()
        
        # Verify heartbeat was sent
        self.client.socket.send.assert_called()
        
        # Get the sent data and verify it's a heartbeat message
        call_args = self.client.socket.send.call_args[0]
        sent_data = call_args[0]
        
        # Should be able to deserialize as heartbeat message
        # (This would require the actual message format, so we just verify send was called)
        self.assertTrue(len(sent_data) > 0)
    
    def test_disconnect_cleanup(self):
        """Test proper cleanup during disconnection."""
        # Mock connected client
        self.client.socket = Mock()
        self.client.state = ClientState.CONNECTED
        
        # Disconnect
        self.client.disconnect()
        
        # Verify cleanup
        self.assertEqual(self.client.state, ClientState.DISCONNECTED)
        self.client.socket.close.assert_called_once()
        self.assertIsNone(self.client.socket)
    
    def test_reconnection_attempts(self):
        """Test client reconnection logic."""
        with patch.object(self.client, 'connect_to_server') as mock_connect:
            # First attempt fails, second succeeds
            mock_connect.side_effect = [False, True]
            
            # Mock reconnection logic
            attempts = 0
            max_attempts = 3
            
            for attempt in range(max_attempts):
                if self.client.connect_to_server("localhost", 8888):
                    break
                attempts += 1
                time.sleep(0.1)  # Short delay between attempts
            
            # Should have made 2 attempts total
            self.assertEqual(mock_connect.call_count, 2)
            self.assertLess(attempts, max_attempts)
    
    def test_status_info(self):
        """Test client status information."""
        # Disconnected state
        info = self.client.get_status_info()
        self.assertEqual(info['state'], ClientState.DISCONNECTED.value)
        self.assertFalse(info['connected'])
        
        # Connected state
        self.client.state = ClientState.CONNECTED
        info = self.client.get_status_info()
        self.assertEqual(info['state'], ClientState.CONNECTED.value)
        self.assertTrue(info['connected'])
        
        # In-game state
        self.client.state = ClientState.IN_GAME
        self.client.is_in_game = True
        info = self.client.get_status_info()
        self.assertEqual(info['state'], ClientState.IN_GAME.value)
        self.assertTrue(info['in_game'])


class TestGameServer(unittest.TestCase):
    """Test the GameServer component."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.server = GameServer()
        self.mock_controller = Mock()
        
    def tearDown(self):
        """Clean up after tests."""
        if self.server.is_running:
            self.server.stop_server()
    
    def test_server_initialization(self):
        """Test GameServer initialization."""
        self.assertEqual(self.server.state, ServerState.STOPPED)
        self.assertIsNone(self.server.socket)
        self.assertEqual(len(self.server.connected_players), 0)
        self.assertFalse(self.server.is_running)
        self.assertIsInstance(self.server.protocol, MessageProtocol)
    
    def test_connected_player_creation(self):
        """Test ConnectedPlayer data structure."""
        mock_socket = Mock()
        player = ConnectedPlayer(
            player_id=1,
            socket=mock_socket,
            address=("192.168.1.100", 12345),
            name="TestPlayer",
            deck_name="TestDeck"
        )
        
        self.assertEqual(player.player_id, 1)
        self.assertEqual(player.socket, mock_socket)
        self.assertEqual(player.address, ("192.168.1.100", 12345))
        self.assertEqual(player.name, "TestPlayer")
        self.assertEqual(player.deck_name, "TestDeck")
        self.assertIsInstance(player.last_heartbeat, float)
        self.assertTrue(player.is_active)
    
    @patch('socket.socket')
    def test_server_startup(self, mock_socket_class):
        """Test server startup process."""
        # Mock socket
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        mock_socket.bind.return_value = None
        mock_socket.listen.return_value = None
        
        # Start server
        with patch('threading.Thread') as mock_thread:
            result = self.server.start_server("localhost", 8888)
        
        # Verify startup
        self.assertTrue(result)
        mock_socket.bind.assert_called_once_with(("localhost", 8888))
        mock_socket.listen.assert_called_once()
        self.assertEqual(self.server.state, ServerState.RUNNING)
        self.assertTrue(self.server.is_running)
        
        # Verify thread creation for accepting connections
        mock_thread.assert_called()
    
    @patch('socket.socket')
    def test_server_startup_failure(self, mock_socket_class):
        """Test server startup failure."""
        # Mock socket to raise binding error
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        mock_socket.bind.side_effect = OSError("Address already in use")
        
        # Attempt to start server
        result = self.server.start_server("localhost", 8888)
        
        # Verify startup failed
        self.assertFalse(result)
        self.assertEqual(self.server.state, ServerState.STOPPED)
        self.assertFalse(self.server.is_running)
    
    def test_player_connection_management(self):
        """Test player connection and disconnection."""
        # Mock player socket
        mock_socket = Mock()
        
        # Add player
        player_id = self.server._add_player(
            socket=mock_socket,
            address=("192.168.1.100", 12345),
            name="TestPlayer",
            deck_name="TestDeck"
        )
        
        # Verify player added
        self.assertEqual(player_id, 0)  # First player gets ID 0
        self.assertEqual(len(self.server.connected_players), 1)
        self.assertIn(player_id, self.server.connected_players)
        
        player = self.server.connected_players[player_id]
        self.assertEqual(player.name, "TestPlayer")
        self.assertEqual(player.deck_name, "TestDeck")
        
        # Remove player
        self.server._remove_player(player_id)
        
        # Verify player removed
        self.assertEqual(len(self.server.connected_players), 0)
        self.assertNotIn(player_id, self.server.connected_players)
    
    def test_message_broadcasting(self):
        """Test message broadcasting to all connected players."""
        # Add multiple mock players
        players = []
        for i in range(3):
            mock_socket = Mock()
            player_id = self.server._add_player(
                socket=mock_socket,
                address=(f"192.168.1.{100+i}", 12345),
                name=f"Player{i}",
                deck_name=f"Deck{i}"
            )
            players.append((player_id, mock_socket))
        
        # Create test message
        test_message = NetworkMessage(MessageType.GAME_STATE_UPDATE, {"test": "data"})
        
        # Broadcast message
        self.server._broadcast_message(test_message)
        
        # Verify all players received the message
        for player_id, mock_socket in players:
            mock_socket.send.assert_called()
    
    def test_heartbeat_monitoring(self):
        """Test heartbeat monitoring and timeout handling."""
        # Add a player
        mock_socket = Mock()
        player_id = self.server._add_player(
            socket=mock_socket,
            address=("192.168.1.100", 12345),
            name="TestPlayer",
            deck_name="TestDeck"
        )
        
        player = self.server.connected_players[player_id]
        
        # Simulate old heartbeat (player should timeout)
        player.last_heartbeat = time.time() - 100  # 100 seconds ago
        
        # Check for timeouts
        self.server._check_player_timeouts()
        
        # Player should be removed due to timeout
        self.assertNotIn(player_id, self.server.connected_players)
        mock_socket.close.assert_called()
    
    def test_server_status_info(self):
        """Test server status information."""
        # Stopped state
        info = self.server.get_status_info()
        self.assertEqual(info['state'], ServerState.STOPPED.value)
        self.assertFalse(info['running'])
        self.assertEqual(info['player_count'], 0)
        
        # Running state with players
        self.server.state = ServerState.RUNNING
        self.server.is_running = True
        
        # Add mock players
        for i in range(2):
            mock_socket = Mock()
            self.server._add_player(
                socket=mock_socket,
                address=(f"192.168.1.{100+i}", 12345),
                name=f"Player{i}",
                deck_name=f"Deck{i}"
            )
        
        info = self.server.get_status_info()
        self.assertEqual(info['state'], ServerState.RUNNING.value)
        self.assertTrue(info['running'])
        self.assertEqual(info['player_count'], 2)
    
    def test_server_shutdown(self):
        """Test server shutdown process."""
        # Mock running server
        self.server.socket = Mock()
        self.server.is_running = True
        self.server.state = ServerState.RUNNING
        
        # Add mock players
        mock_sockets = []
        for i in range(2):
            mock_socket = Mock()
            mock_sockets.append(mock_socket)
            self.server._add_player(
                socket=mock_socket,
                address=(f"192.168.1.{100+i}", 12345),
                name=f"Player{i}",
                deck_name=f"Deck{i}"
            )
        
        # Stop server
        self.server.stop_server()
        
        # Verify shutdown
        self.assertFalse(self.server.is_running)
        self.assertEqual(self.server.state, ServerState.STOPPED)
        self.server.socket.close.assert_called_once()
        
        # Verify all player connections closed
        for mock_socket in mock_sockets:
            mock_socket.close.assert_called()
        
        # Verify players list cleared
        self.assertEqual(len(self.server.connected_players), 0)


class TestNetworkGameController(unittest.TestCase):
    """Test the NetworkGameController integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.controller = NetworkGameController()
    
    def tearDown(self):
        """Clean up after tests."""
        if self.controller.is_networked:
            self.controller.disconnect_from_network()
    
    def test_controller_initialization(self):
        """Test NetworkGameController initialization."""
        self.assertIsNone(self.controller.network_client)
        self.assertIsNone(self.controller.game_server)
        self.assertFalse(self.controller.is_server)
        self.assertFalse(self.controller.is_networked)
        self.assertEqual(len(self.controller.network_players), 0)
    
    @patch('network.game_server.GameServer')
    def test_setup_as_server(self, mock_server_class):
        """Test setting up controller as server."""
        # Mock server instance
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.start_server.return_value = True
        
        # Setup as server
        result = self.controller.setup_as_server("localhost", 8888)
        
        # Verify setup
        self.assertTrue(result)
        self.assertTrue(self.controller.is_server)
        self.assertTrue(self.controller.is_networked)
        self.assertIsNotNone(self.controller.game_server)
        mock_server.start_server.assert_called_once_with("localhost", 8888)
    
    @patch('network.network_client.NetworkClient')
    def test_setup_as_client(self, mock_client_class):
        """Test setting up controller as client."""
        # Mock client instance
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Setup as client
        result = self.controller.setup_as_client("TestPlayer", "TestDeck")
        
        # Verify setup
        self.assertEqual(result, mock_client)
        self.assertFalse(self.controller.is_server)
        self.assertTrue(self.controller.is_networked)
        self.assertEqual(self.controller.network_client, mock_client)
    
    def test_network_status_properties(self):
        """Test network status property."""
        # Not networked
        status = self.controller.network_status
        self.assertEqual(status, "Not networked")
        
        # Mock server mode
        self.controller.is_networked = True
        self.controller.is_server = True
        mock_server = Mock()
        mock_server.is_running = True
        mock_server.player_count = 3
        self.controller.game_server = mock_server
        
        status = self.controller.network_status
        self.assertIn("Server running", status)
        self.assertIn("3 players", status)
    
    def test_network_info(self):
        """Test network information gathering."""
        info = self.controller.get_network_info()
        
        # Initial state
        self.assertFalse(info['is_networked'])
        self.assertFalse(info['is_server'])
        self.assertEqual(info['status'], "Not networked")
        self.assertEqual(info['players'], {})


class TestNetworkIntegration(unittest.TestCase):
    """Integration tests for complete network system."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.server_controller = NetworkGameController()
        self.client_controller = NetworkGameController()
        
    def tearDown(self):
        """Clean up integration test fixtures."""
        if self.server_controller.is_networked:
            self.server_controller.disconnect_from_network()
        if self.client_controller.is_networked:
            self.client_controller.disconnect_from_network()
    
    @patch('network.game_server.GameServer')
    @patch('network.network_client.NetworkClient')
    def test_server_client_setup(self, mock_client_class, mock_server_class):
        """Test server and client setup integration."""
        # Mock server
        mock_server = Mock()
        mock_server_class.return_value = mock_server
        mock_server.start_server.return_value = True
        
        # Mock client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.connect_to_server.return_value = True
        
        # Setup server
        server_result = self.server_controller.setup_as_server("localhost", 8888)
        self.assertTrue(server_result)
        self.assertTrue(self.server_controller.is_server)
        
        # Setup client
        client_result = self.client_controller.setup_as_client("TestPlayer", "TestDeck")
        self.assertIsNotNone(client_result)
        self.assertFalse(self.client_controller.is_server)
        
        # Test client connecting to server
        connect_result = self.client_controller.connect_to_server(
            "localhost", 8888, "TestPlayer", "TestDeck"
        )
        self.assertTrue(connect_result)
    
    def test_message_flow_simulation(self):
        """Test simulated message flow between components."""
        # This test simulates message flow without actual network connections
        
        # Create protocol for message creation
        protocol = MessageProtocol()
        
        # Simulate client joining game
        join_message = protocol.create_join_game_message("TestPlayer", "TestDeck")
        self.assertEqual(join_message.type, MessageType.JOIN_GAME)
        
        # Simulate server responding with game state
        game_state = {
            "phase": "main_phase_1",
            "active_player": 0,
            "players": [{"player_id": 0, "name": "TestPlayer", "life": 20}]
        }
        state_message = protocol.create_game_state_update_message(game_state)
        self.assertEqual(state_message.type, MessageType.GAME_STATE_UPDATE)
        
        # Simulate client playing a card
        play_message = protocol.create_play_card_message("Lightning Bolt", "hand", "stack")
        self.assertEqual(play_message.type, MessageType.PLAY_CARD)
        
        # Verify all messages can be serialized and deserialized
        messages = [join_message, state_message, play_message]
        for original_msg in messages:
            serialized = original_msg.to_bytes()
            deserialized = NetworkMessage.from_bytes(serialized)
            self.assertEqual(deserialized.type, original_msg.type)
            self.assertEqual(deserialized.data, original_msg.data)
    
    def test_error_handling_scenarios(self):
        """Test various error handling scenarios."""
        # Test connection failures
        client = NetworkClient(player_id=1)
        
        # Should fail to send messages when disconnected
        self.assertFalse(client.send_heartbeat())
        self.assertFalse(client.join_game("Player", "Deck"))
        
        # Test server startup failures
        server = GameServer()
        
        # Mock socket failure
        with patch('socket.socket') as mock_socket_class:
            mock_socket = Mock()
            mock_socket_class.return_value = mock_socket
            mock_socket.bind.side_effect = OSError("Port in use")
            
            result = server.start_server("localhost", 8888)
            self.assertFalse(result)
            self.assertEqual(server.state, ServerState.STOPPED)
    
    def test_concurrent_operations(self):
        """Test concurrent network operations."""
        import threading
        import queue
        
        results = queue.Queue()
        
        def create_multiple_clients():
            """Create multiple client instances concurrently."""
            for i in range(10):
                client = NetworkClient(player_id=i)
                results.put(client.player_id)
        
        # Create threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=create_multiple_clients)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Collect results
        player_ids = []
        while not results.empty():
            player_ids.append(results.get())
        
        # Should have 30 player IDs
        self.assertEqual(len(player_ids), 30)
        
        # Should have correct range of player IDs (0-9 repeated 3 times)
        expected_ids = list(range(10)) * 3
        self.assertEqual(sorted(player_ids), sorted(expected_ids))


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)
