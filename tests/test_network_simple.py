#!/usr/bin/env python3
"""Simple Network Test

A basic test to validate that our network components can be imported and initialized.
"""

import sys
import os
import unittest

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


class TestNetworkImports(unittest.TestCase):
    """Test that network components can be imported successfully."""
    
    def test_message_protocol_import(self):
        """Test importing message protocol."""
        try:
            from network.message_protocol import MessageType, NetworkMessage, MessageProtocol
            self.assertTrue(True, "Message protocol imports successfully")
        except ImportError as e:
            self.fail(f"Failed to import message protocol: {e}")
    
    def test_message_types_exist(self):
        """Test that message types are defined."""
        from network.message_protocol import MessageType
        
        # Test a few key message types
        expected_types = ['JOIN_GAME', 'HEARTBEAT', 'PLAY_CARD', 'GAME_STATE_UPDATE']
        for msg_type in expected_types:
            self.assertTrue(hasattr(MessageType, msg_type), 
                          f"MessageType should have {msg_type}")
    
    def test_message_creation(self):
        """Test basic message creation."""
        from network.message_protocol import MessageType, MessageProtocol
        
        protocol = MessageProtocol(player_id=1)
        
        # Test creating a join game message
        join_msg = protocol.create_join_game_message("TestPlayer", "TestDeck")
        self.assertEqual(join_msg.type, MessageType.JOIN_GAME)
        self.assertEqual(join_msg.player_id, 1)
        self.assertEqual(join_msg.data["player_name"], "TestPlayer")
        self.assertEqual(join_msg.data["deck_name"], "TestDeck")
    
    def test_message_serialization(self):
        """Test basic message serialization."""
        from network.message_protocol import MessageType, MessageProtocol
        
        protocol = MessageProtocol(player_id=1)
        message = protocol.create_heartbeat_message()
        
        # Test to_dict conversion
        message_dict = message.to_dict()
        self.assertIn("type", message_dict)
        self.assertIn("player_id", message_dict)
        self.assertIn("data", message_dict)
        self.assertEqual(message_dict["type"], MessageType.HEARTBEAT.value)
    
    def test_network_client_import(self):
        """Test importing network client."""
        try:
            from network.network_client import NetworkClient, ClientState
            self.assertTrue(True, "Network client imports successfully")
        except ImportError as e:
            self.fail(f"Failed to import network client: {e}")
    
    def test_game_server_import(self):
        """Test importing game server."""
        try:
            from network.game_server import GameServer
            self.assertTrue(True, "Game server imports successfully")
        except ImportError as e:
            self.fail(f"Failed to import game server: {e}")
    
    def test_network_game_controller_import(self):
        """Test importing network game controller."""
        try:
            from network.network_game_controller import NetworkGameController
            self.assertTrue(True, "Network game controller imports successfully")
        except ImportError as e:
            self.fail(f"Failed to import network game controller: {e}")
    
    def test_basic_client_creation(self):
        """Test basic client creation."""
        from network.network_client import NetworkClient, ClientState
        
        client = NetworkClient(player_id=1)
        self.assertEqual(client.player_id, 1)
        self.assertEqual(client.state, ClientState.DISCONNECTED)
    
    def test_basic_server_creation(self):
        """Test basic server creation."""
        from network.game_server import GameServer
        
        server = GameServer()
        self.assertIsNotNone(server)
        # Test that server starts in stopped state
        self.assertFalse(server.is_running)
    
    def test_basic_controller_creation(self):
        """Test basic controller creation.""" 
        from network.network_game_controller import NetworkGameController
        
        controller = NetworkGameController()
        self.assertIsNotNone(controller)
        self.assertFalse(controller.is_server)
        self.assertFalse(controller.is_networked)


class TestNetworkBasicFunctionality(unittest.TestCase):
    """Test basic network functionality without actual connections."""
    
    def test_message_protocol_methods(self):
        """Test message protocol creation methods."""
        from network.message_protocol import MessageProtocol, MessageType
        
        protocol = MessageProtocol(player_id=1)
        
        # Test different message types
        join_msg = protocol.create_join_game_message("Player", "Deck")
        self.assertEqual(join_msg.type, MessageType.JOIN_GAME)
        
        heartbeat = protocol.create_heartbeat_message()
        self.assertEqual(heartbeat.type, MessageType.HEARTBEAT)
        
        play_msg = protocol.create_play_card_message("card123", "hand", "battlefield")
        self.assertEqual(play_msg.type, MessageType.PLAY_CARD)
        
        error_msg = protocol.create_error_message("ERR001", "Test error")
        self.assertEqual(error_msg.type, MessageType.ERROR)
    
    def test_message_validation(self):
        """Test message validation."""
        from network.message_protocol import MessageProtocol
        
        protocol = MessageProtocol(player_id=1)
        message = protocol.create_heartbeat_message()
        
        # Message should be valid when created
        self.assertTrue(message.is_valid())
        
        # Test message integrity
        self.assertIsNotNone(message.checksum)
        self.assertGreater(len(message.checksum), 0)
    
    def test_sequence_numbering(self):
        """Test message sequence numbering."""
        from network.message_protocol import MessageProtocol
        
        protocol = MessageProtocol(player_id=1)
        
        # Create multiple messages
        msg1 = protocol.create_heartbeat_message()
        msg2 = protocol.create_heartbeat_message()
        msg3 = protocol.create_heartbeat_message()
        
        # Sequence numbers should increase
        self.assertEqual(msg1.sequence, 1)
        self.assertEqual(msg2.sequence, 2)
        self.assertEqual(msg3.sequence, 3)


def run_simple_tests():
    """Run the simple network tests."""
    print("🔥 Running Simple Network Validation Tests")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestNetworkImports))
    suite.addTest(unittest.makeSuite(TestNetworkBasicFunctionality))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {result.testsRun} tests run")
    print(f"✅ Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Failed: {len(result.failures)}")
    print(f"🚨 Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n🚨 FAILURES:")
        for test, error in result.failures:
            print(f"  - {test}: {error}")
    
    if result.errors:
        print("\n🚨 ERRORS:")
        for test, error in result.errors:
            print(f"  - {test}: {error}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    print(f"\n📈 Success Rate: {success_rate:.1f}%")
    
    if result.wasSuccessful():
        print("🎉 All tests passed! Network components are working correctly.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_simple_tests()
    sys.exit(0 if success else 1)
