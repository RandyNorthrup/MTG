"""MTG Commander Game - Network UI Tests

This module contains comprehensive tests for network UI components,
including lobby dialog, status widget, and integration scenarios.
"""

import unittest
import sys
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt, QTimer

# Import UI components
from ui.network_lobby_dialog import NetworkLobbyDialog, NetworkDiscoveryThread, GameServerItem
from ui.network_status_widget import NetworkStatusWidget
from network.network_game_controller import NetworkGameController
from network.network_client import NetworkClient, ClientState
from network.game_server import GameServer, ServerState


class TestNetworkLobbyDialog(unittest.TestCase):
    """Test the NetworkLobbyDialog component."""
    
    @classmethod
    def setUpClass(cls):
        """Set up QApplication for UI tests."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Set up test fixtures."""
        self.lobby = NetworkLobbyDialog()
    
    def tearDown(self):
        """Clean up after tests."""
        self.lobby.close()
        if hasattr(self, 'lobby') and self.lobby:
            self.lobby.deleteLater()
    
    def test_lobby_initialization(self):
        """Test NetworkLobbyDialog initialization."""
        self.assertEqual(self.lobby.windowTitle(), "MTG Commander - Network Multiplayer Lobby")
        self.assertIsNone(self.lobby.network_controller)
        self.assertIsNone(self.lobby.network_client)
        self.assertIsNone(self.lobby.discovery_thread)
        
        # Check tab widget has correct number of tabs
        self.assertEqual(self.lobby.tab_widget.count(), 3)
        self.assertEqual(self.lobby.tab_widget.tabText(0), "🏠 Host Game")
        self.assertEqual(self.lobby.tab_widget.tabText(1), "🚀 Join Game")
        self.assertEqual(self.lobby.tab_widget.tabText(2), "🔍 Browse Games")
    
    def test_deck_loading(self):
        """Test deck loading functionality."""
        # Test with mock deck files
        with patch('os.path.exists') as mock_exists, \
             patch('os.listdir') as mock_listdir:
            
            mock_exists.return_value = True
            mock_listdir.return_value = ['Deck1.txt', 'Deck2.txt', 'NotADeck.csv']
            
            # Create new lobby to test deck loading
            test_lobby = NetworkLobbyDialog()
            
            # Check that only .txt files are loaded
            host_combo = test_lobby.host_deck_combo
            self.assertEqual(host_combo.count(), 2)
            self.assertEqual(host_combo.itemText(0), "Deck1")
            self.assertEqual(host_combo.itemText(1), "Deck2")
            
            test_lobby.close()
            test_lobby.deleteLater()
    
    def test_deck_loading_no_decks(self):
        """Test deck loading when no decks are found."""
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False
            
            # Create new lobby to test empty deck loading
            test_lobby = NetworkLobbyDialog()
            
            # Should show "No decks found" message
            host_combo = test_lobby.host_deck_combo
            self.assertEqual(host_combo.count(), 1)
            self.assertEqual(host_combo.itemText(0), "No decks found")
            
            test_lobby.close()
            test_lobby.deleteLater()
    
    @patch('network.network_game_controller.NetworkGameController')
    def test_start_hosting_success(self, mock_controller_class):
        """Test successful game hosting."""
        # Mock network controller
        mock_controller = Mock()
        mock_controller_class.return_value = mock_controller
        mock_controller.setup_as_server.return_value = True
        
        # Set valid input values
        self.lobby.game_name_edit.setText("Test Game")
        self.lobby.host_player_name.setText("Host Player")
        self.lobby.host_deck_combo.clear()
        self.lobby.host_deck_combo.addItem("Test Deck", "TestDeck.txt")
        
        # Trigger hosting
        self.lobby.start_hosting()
        
        # Verify controller setup was called
        mock_controller.setup_as_server.assert_called_once()
        self.assertEqual(self.lobby.network_controller, mock_controller)
        
        # Check UI state changes
        self.assertFalse(self.lobby.host_button.isVisible())
        self.assertTrue(self.lobby.stop_host_button.isVisible())
    
    def test_start_hosting_validation_errors(self):
        """Test hosting validation errors."""
        # Test empty game name
        self.lobby.game_name_edit.setText("")
        self.lobby.host_player_name.setText("Host Player")
        
        with patch.object(self.lobby, 'show_error') as mock_error:
            self.lobby.start_hosting()
            mock_error.assert_called_with("Please enter a game name")
        
        # Test empty player name
        self.lobby.game_name_edit.setText("Test Game")
        self.lobby.host_player_name.setText("")
        
        with patch.object(self.lobby, 'show_error') as mock_error:
            self.lobby.start_hosting()
            mock_error.assert_called_with("Please enter your player name")
        
        # Test no deck selected
        self.lobby.host_player_name.setText("Host Player")
        self.lobby.host_deck_combo.clear()
        self.lobby.host_deck_combo.addItem("No decks found", "")
        
        with patch.object(self.lobby, 'show_error') as mock_error:
            self.lobby.start_hosting()
            mock_error.assert_called_with("Please select a valid deck")
    
    @patch('network.network_game_controller.NetworkGameController')
    def test_join_game_success(self, mock_controller_class):
        """Test successful game joining."""
        # Mock network controller and client
        mock_controller = Mock()
        mock_client = Mock()
        mock_controller_class.return_value = mock_controller
        mock_controller.setup_as_client.return_value = mock_client
        mock_controller.connect_to_server.return_value = True
        
        # Set valid input values
        self.lobby.join_player_name.setText("Test Player")
        self.lobby.join_deck_combo.clear()
        self.lobby.join_deck_combo.addItem("Test Deck", "TestDeck.txt")
        self.lobby.server_address_edit.setText("localhost")
        self.lobby.server_port_spinbox.setValue(8888)
        
        # Trigger joining
        self.lobby.join_game()
        
        # Verify setup was called
        mock_controller.setup_as_client.assert_called_once_with("Test Player", "Test Deck")
        mock_controller.connect_to_server.assert_called_once_with(
            "localhost", 8888, "Test Player", "Test Deck"
        )
        
        # Check UI state changes
        self.assertFalse(self.lobby.join_button.isVisible())
        self.assertTrue(self.lobby.disconnect_button.isVisible())
    
    def test_join_game_validation_errors(self):
        """Test join game validation errors."""
        # Test empty player name
        self.lobby.join_player_name.setText("")
        
        with patch.object(self.lobby, 'show_error') as mock_error:
            self.lobby.join_game()
            mock_error.assert_called_with("Please enter your player name")
        
        # Test no deck selected
        self.lobby.join_player_name.setText("Test Player")
        self.lobby.join_deck_combo.clear()
        self.lobby.join_deck_combo.addItem("No decks found", "")
        
        with patch.object(self.lobby, 'show_error') as mock_error:
            self.lobby.join_game()
            mock_error.assert_called_with("Please select a valid deck")
    
    def test_network_discovery_thread(self):
        """Test network discovery functionality."""
        # Create discovery thread
        discovery = NetworkDiscoveryThread(port_range=(8888, 8890))
        
        # Mock socket operations
        with patch('socket.socket') as mock_socket_class:
            mock_socket = Mock()
            mock_socket_class.return_value = mock_socket
            
            # Mock successful connection (server found)
            mock_socket.connect_ex.return_value = 0
            mock_socket.close.return_value = None
            
            # Connect signal to capture discoveries
            discovered_games = []
            discovery.game_discovered.connect(
                lambda host, port, name, count: discovered_games.append((host, port, name, count))
            )
            
            # Start discovery
            discovery.start()
            discovery.wait()
            
            # Should have found some games (mocked)
            self.assertGreater(len(discovered_games), 0)
    
    def test_game_server_item(self):
        """Test GameServerItem functionality."""
        item = GameServerItem("192.168.1.100", 8888, "Test Game", 2)
        
        self.assertEqual(item.host, "192.168.1.100")
        self.assertEqual(item.port, 8888)
        self.assertEqual(item.game_name, "Test Game")
        self.assertEqual(item.player_count, 2)
        self.assertEqual(item.text(), "Test Game (192.168.1.100:8888) - 2 players")
        self.assertIn("Host: 192.168.1.100", item.toolTip())
    
    def test_quick_join_functionality(self):
        """Test quick join from discovered games."""
        # Add a mock game to the list
        item = GameServerItem("192.168.1.100", 8888, "Test Game", 2)
        self.lobby.discovered_games_list.addItem(item)
        self.lobby.discovered_games_list.setCurrentItem(item)
        
        # Set up join fields
        self.lobby.join_player_name.setText("Test Player")
        self.lobby.join_deck_combo.clear()
        self.lobby.join_deck_combo.addItem("Test Deck", "TestDeck.txt")
        
        # Mock successful joining
        with patch.object(self.lobby, 'join_game') as mock_join:
            self.lobby.quick_join_selected()
            
            # Should switch to join tab and fill in server details
            self.assertEqual(self.lobby.tab_widget.currentIndex(), 1)  # Join tab
            self.assertEqual(self.lobby.server_address_edit.text(), "192.168.1.100")
            self.assertEqual(self.lobby.server_port_spinbox.value(), 8888)
            
            # Should trigger join
            mock_join.assert_called_once()
    
    def test_tab_switching_behavior(self):
        """Test tab switching triggers appropriate actions."""
        # Mock scan_for_games method
        with patch.object(self.lobby, 'scan_for_games') as mock_scan:
            # Switch to browse tab (index 2)
            self.lobby.tab_widget.setCurrentIndex(2)
            self.lobby.on_tab_changed(2)
            
            # Should trigger automatic scan
            mock_scan.assert_called_once()
    
    def test_status_label_updates(self):
        """Test status label updates."""
        initial_text = self.lobby.status_label.text()
        self.assertEqual(initial_text, "Ready")
        
        # Test player joined status
        self.lobby.on_player_joined(1, "TestPlayer")
        self.assertIn("Player joined: TestPlayer", self.lobby.status_label.text())
        
        # Test player left status
        self.lobby.on_player_left(1, "TestPlayer")
        self.assertIn("Player left: TestPlayer", self.lobby.status_label.text())
        
        # Test network error status
        self.lobby.on_network_error("Test error")
        self.assertIn("Network error: Test error", self.lobby.status_label.text())
    
    def test_cleanup_on_close(self):
        """Test proper cleanup when closing lobby."""
        # Mock network components
        mock_controller = Mock()
        mock_thread = Mock()
        mock_thread.isRunning.return_value = True
        
        self.lobby.network_controller = mock_controller
        self.lobby.discovery_thread = mock_thread
        
        # Close lobby
        self.lobby.close_lobby()
        
        # Verify cleanup
        mock_controller.disconnect_from_network.assert_called_once()
        mock_thread.stop_scanning.assert_called_once()
        mock_thread.wait.assert_called_once()


class TestNetworkStatusWidget(unittest.TestCase):
    """Test the NetworkStatusWidget component."""
    
    @classmethod
    def setUpClass(cls):
        """Set up QApplication for UI tests."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Set up test fixtures."""
        self.widget = NetworkStatusWidget()
    
    def tearDown(self):
        """Clean up after tests."""
        self.widget.close()
        if hasattr(self, 'widget') and self.widget:
            self.widget.deleteLater()
    
    def test_widget_initialization(self):
        """Test NetworkStatusWidget initialization."""
        self.assertEqual(self.widget.status_label.text(), "🔌 Not Connected")
        self.assertIsNone(self.widget.network_controller)
        self.assertIsNone(self.widget.network_client)
        self.assertFalse(self.widget.is_collapsed)
        self.assertEqual(self.widget.maximumHeight(), 200)
    
    def test_display_update_not_connected(self):
        """Test display update when not connected."""
        self.widget.update_display()
        
        # Check status label
        self.assertEqual(self.widget.status_label.text(), "🔌 Not Connected")
        self.assertIn("color: #666", self.widget.status_label.styleSheet())
        
        # Check connection info
        self.assertEqual(self.widget.connection_label.text(), "No active connection")
        
        # Check menu actions
        self.assertFalse(self.widget.disconnect_action.isEnabled())
        self.assertFalse(self.widget.ready_action.isEnabled())
        
        # Check players list
        self.assertEqual(self.widget.players_group.title(), "Connected Players (0)")
        self.assertTrue(self.widget.no_players_label.isVisible())
    
    def test_display_update_server_mode(self):
        """Test display update in server mode."""
        # Mock server controller
        mock_controller = Mock()
        mock_controller.is_server = True
        mock_controller.network_players = {0: {"name": "Host"}, 1: {"name": "Player1"}}
        mock_controller.get_network_info.return_value = {
            'server': {'host': 'localhost', 'port': 8888}
        }
        
        self.widget.set_network_controller(mock_controller)
        
        # Check status updates
        self.assertEqual(self.widget.status_label.text(), "🏠 Hosting Game")
        self.assertIn("color: green", self.widget.status_label.styleSheet())
        self.assertIn("Server: localhost:8888", self.widget.connection_label.text())
        
        # Check menu actions
        self.assertTrue(self.widget.disconnect_action.isEnabled())
        self.assertTrue(self.widget.ready_action.isEnabled())  # 2 players, ready for game
        
        # Check players list
        self.assertEqual(self.widget.players_group.title(), "Connected Players (2)")
        self.assertFalse(self.widget.no_players_label.isVisible())
    
    def test_display_update_client_mode(self):
        """Test display update in client mode."""
        # Mock client controller
        mock_controller = Mock()
        mock_controller.is_server = False
        mock_controller.network_players = {}
        mock_controller.get_network_info.return_value = {'client': {}}
        
        # Mock client
        mock_client = Mock()
        mock_client.state = ClientState.CONNECTED
        
        self.widget.set_network_controller(mock_controller)
        self.widget.set_network_client(mock_client)
        
        # Check status updates
        self.assertEqual(self.widget.status_label.text(), "🌐 Connected")
        self.assertIn("color: green", self.widget.status_label.styleSheet())
        self.assertEqual(self.widget.connection_label.text(), "Connected to server")
        
        # Check menu actions
        self.assertTrue(self.widget.disconnect_action.isEnabled())
        self.assertTrue(self.widget.ready_action.isEnabled())
    
    def test_display_update_client_connecting(self):
        """Test display update when client is connecting."""
        # Mock client controller
        mock_controller = Mock()
        mock_controller.is_server = False
        mock_controller.network_players = {}
        mock_controller.get_network_info.return_value = {'client': {}}
        
        # Mock connecting client
        mock_client = Mock()
        mock_client.state = ClientState.CONNECTING
        
        self.widget.set_network_controller(mock_controller)
        self.widget.set_network_client(mock_client)
        
        # Check status updates
        self.assertEqual(self.widget.status_label.text(), "🔄 Connecting...")
        self.assertIn("color: blue", self.widget.status_label.styleSheet())
        self.assertEqual(self.widget.connection_label.text(), "Connecting to server...")
        
        # Check progress bar
        self.assertTrue(self.widget.progress_bar.isVisible())
        
        # Check menu actions
        self.assertTrue(self.widget.disconnect_action.isEnabled())
        self.assertFalse(self.widget.ready_action.isEnabled())
    
    def test_players_list_update(self):
        """Test players list updates."""
        # Mock controller with players
        mock_controller = Mock()
        mock_controller.is_server = True
        mock_controller.network_players = {
            0: {"name": "Host"},
            1: {"name": "Player1"},
            2: {"name": "Player2"}
        }
        
        self.widget.set_network_controller(mock_controller)
        
        # Check players list
        self.assertEqual(self.widget.players_list.count(), 3)
        
        # Check host indication
        host_item = self.widget.players_list.item(0)
        self.assertIn("👤 Host (Host)", host_item.text())
        
        # Check other players
        player1_item = self.widget.players_list.item(1)
        self.assertIn("👤 Player1", player1_item.text())
        
        # Check title update
        self.assertEqual(self.widget.players_group.title(), "Connected Players (3)")
        self.assertFalse(self.widget.no_players_label.isVisible())
    
    def test_collapse_functionality(self):
        """Test widget collapse/expand functionality."""
        # Initially expanded
        self.assertFalse(self.widget.is_collapsed)
        self.assertTrue(self.widget.info_group.isVisible())
        self.assertTrue(self.widget.players_group.isVisible())
        self.assertEqual(self.widget.toggle_button.text(), "▼")
        self.assertEqual(self.widget.maximumHeight(), 200)
        
        # Collapse
        self.widget.toggle_collapse()
        self.assertTrue(self.widget.is_collapsed)
        self.assertFalse(self.widget.info_group.isVisible())
        self.assertFalse(self.widget.players_group.isVisible())
        self.assertEqual(self.widget.toggle_button.text(), "▶")
        self.assertEqual(self.widget.maximumHeight(), 50)
        
        # Expand again
        self.widget.toggle_collapse()
        self.assertFalse(self.widget.is_collapsed)
        self.assertTrue(self.widget.info_group.isVisible())
        self.assertTrue(self.widget.players_group.isVisible())
        self.assertEqual(self.widget.toggle_button.text(), "▼")
        self.assertEqual(self.widget.maximumHeight(), 200)
    
    def test_signal_connections(self):
        """Test signal connections and handlers."""
        # Mock controller for signal testing
        mock_controller = Mock()
        
        # Test player joined signal
        self.widget.set_network_controller(mock_controller)
        self.widget.on_player_joined(1, "TestPlayer")
        
        # Should update display (we can't directly test this without more complex mocking)
        # But the method should execute without error
        
        # Test player left signal
        self.widget.on_player_left(1, "TestPlayer")
        
        # Test network error signal
        self.widget.on_network_error("Test error")
        self.assertIn("❌ Error", self.widget.status_label.text())
        
        # Test status changed signal
        self.widget.on_status_changed("Connected to server")
        
        # Test client connected/disconnected
        self.widget.on_client_connected()
        self.widget.on_client_disconnected()
    
    def test_utility_methods(self):
        """Test utility methods."""
        # Test connection status
        status = self.widget.get_connection_status()
        self.assertEqual(status, "Not connected")
        
        # Test ready for game check
        self.assertFalse(self.widget.is_ready_for_game())
        
        # Test player count
        self.assertEqual(self.widget.get_player_count(), 0)
        
        # Mock server with players
        mock_controller = Mock()
        mock_controller.is_server = True
        mock_controller.network_players = {0: {"name": "Host"}, 1: {"name": "Player1"}}
        
        self.widget.set_network_controller(mock_controller)
        
        # Test with mock data
        status = self.widget.get_connection_status()
        self.assertIn("Hosting", status)
        self.assertIn("2 players", status)
        
        self.assertTrue(self.widget.is_ready_for_game())  # 2 players, ready
        self.assertEqual(self.widget.get_player_count(), 2)
    
    def test_progress_bar_control(self):
        """Test progress bar show/hide functionality."""
        # Initially hidden
        self.assertFalse(self.widget.progress_bar.isVisible())
        
        # Show progress
        self.widget.show_connecting_progress(True)
        self.assertTrue(self.widget.progress_bar.isVisible())
        self.assertEqual(self.widget.progress_bar.minimum(), 0)
        self.assertEqual(self.widget.progress_bar.maximum(), 0)  # Indeterminate
        
        # Hide progress
        self.widget.show_connecting_progress(False)
        self.assertFalse(self.widget.progress_bar.isVisible())


class TestUIIntegration(unittest.TestCase):
    """Integration tests for UI components."""
    
    @classmethod
    def setUpClass(cls):
        """Set up QApplication for UI tests."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.lobby = NetworkLobbyDialog()
        self.status_widget = NetworkStatusWidget()
    
    def tearDown(self):
        """Clean up integration test fixtures."""
        self.lobby.close()
        self.status_widget.close()
        if hasattr(self, 'lobby') and self.lobby:
            self.lobby.deleteLater()
        if hasattr(self, 'status_widget') and self.status_widget:
            self.status_widget.deleteLater()
    
    def test_lobby_status_widget_integration(self):
        """Test integration between lobby and status widget."""
        # Mock network controller created by lobby
        mock_controller = Mock()
        mock_controller.is_server = True
        mock_controller.network_players = {0: {"name": "Host"}}
        mock_controller.get_network_info.return_value = {'server': {'host': 'localhost', 'port': 8888}}
        
        # Simulate lobby creating a server
        self.lobby.network_controller = mock_controller
        
        # Connect status widget to the same controller
        self.status_widget.set_network_controller(mock_controller)
        
        # Both should show consistent state
        self.assertEqual(self.status_widget.status_label.text(), "🏠 Hosting Game")
        self.assertEqual(self.status_widget.get_player_count(), 1)
        
        # Simulate player joining
        mock_controller.network_players[1] = {"name": "Player1"}
        self.status_widget.on_player_joined(1, "Player1")
        
        # Status widget should update
        self.assertEqual(self.status_widget.get_player_count(), 2)
    
    def test_signal_based_communication(self):
        """Test signal-based communication between components."""
        # Track signal emissions
        lobby_signals = []
        status_signals = []
        
        # Connect to signals
        self.lobby.game_created.connect(lambda ctrl: lobby_signals.append('game_created'))
        self.lobby.game_joined.connect(lambda ctrl, client: lobby_signals.append('game_joined'))
        self.lobby.lobby_closed.connect(lambda: lobby_signals.append('lobby_closed'))
        
        self.status_widget.open_lobby_requested.connect(lambda: status_signals.append('open_lobby'))
        self.status_widget.disconnect_requested.connect(lambda: status_signals.append('disconnect'))
        self.status_widget.game_ready_requested.connect(lambda: status_signals.append('game_ready'))
        
        # Emit signals manually to test connections
        self.status_widget.open_lobby_requested.emit()
        self.status_widget.disconnect_requested.emit()
        self.status_widget.game_ready_requested.emit()
        self.lobby.lobby_closed.emit()
        
        # Verify signals were received
        self.assertIn('open_lobby', status_signals)
        self.assertIn('disconnect', status_signals)
        self.assertIn('game_ready', status_signals)
        self.assertIn('lobby_closed', lobby_signals)
    
    def test_ui_responsiveness(self):
        """Test UI responsiveness during operations."""
        # This test ensures UI updates don't block
        # and that operations complete in reasonable time
        
        import time
        start_time = time.time()
        
        # Perform multiple UI operations
        self.lobby.update()
        self.status_widget.update()
        self.status_widget.update_display()
        self.lobby.load_available_decks(self.lobby.host_deck_combo)
        
        # Operations should complete quickly
        elapsed = time.time() - start_time
        self.assertLess(elapsed, 1.0)  # Should take less than 1 second
    
    def test_error_handling_in_ui(self):
        """Test error handling in UI components."""
        # Test lobby error handling
        with patch.object(self.lobby, 'show_error') as mock_show_error:
            self.lobby.on_network_error("Test network error")
            mock_show_error.assert_called()
        
        # Test status widget error handling
        self.status_widget.on_network_error("Test error message")
        self.assertIn("❌ Error", self.status_widget.status_label.text())
        
        # Test error recovery
        self.status_widget.on_status_changed("Connected to server")
        # Error state should be cleared by status change
    
    def test_memory_cleanup(self):
        """Test proper memory cleanup of UI components."""
        # Create temporary components
        temp_lobby = NetworkLobbyDialog()
        temp_status = NetworkStatusWidget()
        
        # Set up some connections
        mock_controller = Mock()
        temp_status.set_network_controller(mock_controller)
        
        # Close and delete
        temp_lobby.close()
        temp_status.close()
        temp_lobby.deleteLater()
        temp_status.deleteLater()
        
        # Components should clean up properly
        # (This test mainly ensures no exceptions are raised during cleanup)


if __name__ == '__main__':
    # Create QApplication if needed
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Run the tests
    unittest.main(verbosity=2, exit=False)
    
    # Clean up QApplication
    app.quit()
