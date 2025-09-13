"""MTG Commander Game - Network Protocol Tests

This module contains comprehensive tests for the network message protocol system,
including message creation, serialization, validation, and error handling.
"""

import unittest
import json
import time
from unittest.mock import Mock, patch
from network.message_protocol import (
    MessageType, NetworkMessage, MessageProtocol, 
    create_checksum, validate_message
)


class TestMessageProtocol(unittest.TestCase):
    """Test the network message protocol system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.protocol = MessageProtocol()
        self.test_data = {
            "player_id": 1,
            "action": "test_action",
            "data": {"key": "value"}
        }
    
    def test_message_type_enum(self):
        """Test MessageType enum values."""
        # Test all message types exist
        expected_types = [
            'JOIN_GAME', 'LEAVE_GAME', 'PLAYER_ACTION', 'PLAY_CARD',
            'CAST_SPELL', 'ACTIVATE_ABILITY', 'PHASE_CHANGE', 'PASS_PRIORITY',
            'GAME_STATE_UPDATE', 'HEARTBEAT', 'ERROR', 'ACKNOWLEDGMENT'
        ]
        
        for msg_type in expected_types:
            self.assertTrue(hasattr(MessageType, msg_type))
            self.assertIsInstance(getattr(MessageType, msg_type), MessageType)
    
    def test_network_message_creation(self):
        """Test NetworkMessage creation and properties."""
        msg = NetworkMessage(
            type=MessageType.PLAYER_ACTION,
            data=self.test_data
        )
        
        self.assertEqual(msg.type, MessageType.PLAYER_ACTION)
        self.assertEqual(msg.data, self.test_data)
        self.assertIsNotNone(msg.timestamp)
        self.assertIsNotNone(msg.message_id)
        self.assertIsInstance(msg.timestamp, float)
        self.assertIsInstance(msg.message_id, str)
    
    def test_checksum_creation(self):
        """Test checksum generation and validation."""
        test_data = {"test": "data", "number": 42}
        checksum = create_checksum(test_data)
        
        # Checksum should be consistent
        checksum2 = create_checksum(test_data)
        self.assertEqual(checksum, checksum2)
        
        # Different data should produce different checksum
        different_data = {"test": "different", "number": 42}
        different_checksum = create_checksum(different_data)
        self.assertNotEqual(checksum, different_checksum)
    
    def test_message_validation(self):
        """Test message validation function."""
        # Valid message
        valid_msg = NetworkMessage(MessageType.HEARTBEAT, {})
        self.assertTrue(validate_message(valid_msg))
        
        # Invalid message type
        invalid_msg = Mock()
        invalid_msg.type = "invalid_type"
        invalid_msg.data = {}
        invalid_msg.timestamp = time.time()
        invalid_msg.message_id = "test_id"
        self.assertFalse(validate_message(invalid_msg))
        
        # Missing required fields
        incomplete_msg = Mock()
        incomplete_msg.type = MessageType.HEARTBEAT
        incomplete_msg.data = {}
        # Missing timestamp and message_id
        self.assertFalse(validate_message(incomplete_msg))
    
    def test_message_serialization(self):
        """Test message serialization to bytes."""
        msg = NetworkMessage(MessageType.PLAYER_ACTION, self.test_data)
        serialized = msg.to_bytes()
        
        # Should be bytes
        self.assertIsInstance(serialized, bytes)
        
        # Should be non-empty
        self.assertGreater(len(serialized), 0)
        
        # Should contain message data when decoded
        decoded = json.loads(serialized.decode('utf-8'))
        self.assertIn('type', decoded)
        self.assertIn('data', decoded)
        self.assertIn('timestamp', decoded)
        self.assertIn('message_id', decoded)
        self.assertIn('checksum', decoded)
    
    def test_message_deserialization(self):
        """Test message deserialization from bytes."""
        # Create and serialize a message
        original_msg = NetworkMessage(MessageType.CAST_SPELL, self.test_data)
        serialized = original_msg.to_bytes()
        
        # Deserialize back
        deserialized_msg = NetworkMessage.from_bytes(serialized)
        
        # Should match original
        self.assertEqual(deserialized_msg.type, original_msg.type)
        self.assertEqual(deserialized_msg.data, original_msg.data)
        self.assertEqual(deserialized_msg.timestamp, original_msg.timestamp)
        self.assertEqual(deserialized_msg.message_id, original_msg.message_id)
        self.assertEqual(deserialized_msg.checksum, original_msg.checksum)
    
    def test_invalid_deserialization(self):
        """Test handling of invalid serialized data."""
        # Invalid JSON
        with self.assertRaises(Exception):
            NetworkMessage.from_bytes(b"invalid json data")
        
        # Missing required fields
        incomplete_data = json.dumps({
            "type": "HEARTBEAT",
            "timestamp": time.time()
            # Missing data, message_id, checksum
        })
        with self.assertRaises(Exception):
            NetworkMessage.from_bytes(incomplete_data.encode('utf-8'))
    
    def test_protocol_message_creation_methods(self):
        """Test MessageProtocol message creation methods."""
        # Test JOIN_GAME message
        join_msg = self.protocol.create_join_game_message("TestPlayer", "TestDeck")
        self.assertEqual(join_msg.type, MessageType.JOIN_GAME)
        self.assertEqual(join_msg.data["player_name"], "TestPlayer")
        self.assertEqual(join_msg.data["deck_name"], "TestDeck")
        
        # Test PLAY_CARD message
        play_msg = self.protocol.create_play_card_message("card123", "hand", "battlefield")
        self.assertEqual(play_msg.type, MessageType.PLAY_CARD)
        self.assertEqual(play_msg.data["card_id"], "card123")
        self.assertEqual(play_msg.data["zone_from"], "hand")
        self.assertEqual(play_msg.data["zone_to"], "battlefield")
        
        # Test CAST_SPELL message
        mana_cost = {"generic": 3, "blue": 1}
        targets = ["target1", "target2"]
        spell_msg = self.protocol.create_cast_spell_message("spell456", mana_cost, targets)
        self.assertEqual(spell_msg.type, MessageType.CAST_SPELL)
        self.assertEqual(spell_msg.data["card_id"], "spell456")
        self.assertEqual(spell_msg.data["mana_cost"], mana_cost)
        self.assertEqual(spell_msg.data["targets"], targets)
        
        # Test HEARTBEAT message
        heartbeat_msg = self.protocol.create_heartbeat_message()
        self.assertEqual(heartbeat_msg.type, MessageType.HEARTBEAT)
        self.assertIn("timestamp", heartbeat_msg.data)
        
        # Test ERROR message
        error_msg = self.protocol.create_error_message("Test error message", "ERROR_CODE")
        self.assertEqual(error_msg.type, MessageType.ERROR)
        self.assertEqual(error_msg.data["message"], "Test error message")
        self.assertEqual(error_msg.data["error_code"], "ERROR_CODE")
    
    def test_protocol_game_state_message(self):
        """Test game state update message creation."""
        game_state = {
            "phase": "main_phase_1",
            "active_player": 0,
            "turn_number": 5,
            "players": [
                {"player_id": 0, "life": 20, "hand_size": 7},
                {"player_id": 1, "life": 18, "hand_size": 5}
            ]
        }
        
        state_msg = self.protocol.create_game_state_update_message(game_state)
        self.assertEqual(state_msg.type, MessageType.GAME_STATE_UPDATE)
        self.assertEqual(state_msg.data["state"], game_state)
    
    def test_protocol_phase_change_message(self):
        """Test phase change message creation."""
        phase_msg = self.protocol.create_phase_change_message("combat_phase", 1)
        self.assertEqual(phase_msg.type, MessageType.PHASE_CHANGE)
        self.assertEqual(phase_msg.data["new_phase"], "combat_phase")
        self.assertEqual(phase_msg.data["active_player"], 1)
    
    def test_message_size_limits(self):
        """Test handling of large messages."""
        # Create a large data payload
        large_data = {"data": "x" * 10000}  # 10KB of data
        large_msg = NetworkMessage(MessageType.GAME_STATE_UPDATE, large_data)
        
        # Should serialize successfully
        serialized = large_msg.to_bytes()
        self.assertIsInstance(serialized, bytes)
        
        # Should deserialize successfully
        deserialized = NetworkMessage.from_bytes(serialized)
        self.assertEqual(deserialized.data, large_data)
    
    def test_message_checksum_validation(self):
        """Test checksum validation during deserialization."""
        # Create a valid message
        msg = NetworkMessage(MessageType.PLAYER_ACTION, self.test_data)
        serialized = msg.to_bytes()
        
        # Deserialize should work normally
        deserialized = NetworkMessage.from_bytes(serialized)
        self.assertEqual(deserialized.checksum, msg.checksum)
        
        # Manually corrupt the checksum in serialized data
        data = json.loads(serialized.decode('utf-8'))
        data['checksum'] = 'invalid_checksum'
        corrupted_serialized = json.dumps(data).encode('utf-8')
        
        # Should raise an error due to checksum mismatch
        with self.assertRaises(Exception):
            NetworkMessage.from_bytes(corrupted_serialized)
    
    def test_concurrent_message_creation(self):
        """Test message creation under concurrent conditions."""
        import threading
        import queue
        
        results = queue.Queue()
        
        def create_messages():
            for i in range(100):
                msg = self.protocol.create_heartbeat_message()
                results.put(msg.message_id)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=create_messages)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Collect all message IDs
        message_ids = []
        while not results.empty():
            message_ids.append(results.get())
        
        # Should have 500 unique message IDs
        self.assertEqual(len(message_ids), 500)
        self.assertEqual(len(set(message_ids)), 500)  # All unique
    
    def test_message_timestamps(self):
        """Test message timestamp consistency and ordering."""
        # Create multiple messages with slight delays
        messages = []
        for i in range(5):
            msg = NetworkMessage(MessageType.HEARTBEAT, {"index": i})
            messages.append(msg)
            time.sleep(0.01)  # Small delay
        
        # Timestamps should be in ascending order
        for i in range(1, len(messages)):
            self.assertGreater(messages[i].timestamp, messages[i-1].timestamp)
    
    def test_error_message_handling(self):
        """Test error message creation and handling."""
        # Test various error scenarios
        error_scenarios = [
            ("CONNECTION_LOST", "Connection to server lost"),
            ("INVALID_MOVE", "Invalid game move attempted"),
            ("TIMEOUT", "Operation timed out"),
            ("AUTHENTICATION_FAILED", "Authentication failed")
        ]
        
        for error_code, error_message in error_scenarios:
            error_msg = self.protocol.create_error_message(error_message, error_code)
            
            self.assertEqual(error_msg.type, MessageType.ERROR)
            self.assertEqual(error_msg.data["message"], error_message)
            self.assertEqual(error_msg.data["error_code"], error_code)
            
            # Should serialize/deserialize properly
            serialized = error_msg.to_bytes()
            deserialized = NetworkMessage.from_bytes(serialized)
            self.assertEqual(deserialized.data["error_code"], error_code)


class TestNetworkProtocolIntegration(unittest.TestCase):
    """Integration tests for network protocol with other components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.protocol = MessageProtocol()
    
    def test_game_flow_message_sequence(self):
        """Test a complete game flow message sequence."""
        # Simulate a complete game interaction sequence
        
        # 1. Player joins game
        join_msg = self.protocol.create_join_game_message("Alice", "Dragon Deck")
        self.assertEqual(join_msg.type, MessageType.JOIN_GAME)
        
        # 2. Game state update
        initial_state = {"phase": "main_phase_1", "active_player": 0}
        state_msg = self.protocol.create_game_state_update_message(initial_state)
        self.assertEqual(state_msg.type, MessageType.GAME_STATE_UPDATE)
        
        # 3. Player plays a card
        play_msg = self.protocol.create_play_card_message("Lightning Bolt", "hand", "stack")
        self.assertEqual(play_msg.type, MessageType.PLAY_CARD)
        
        # 4. Phase change
        phase_msg = self.protocol.create_phase_change_message("end_phase", 0)
        self.assertEqual(phase_msg.type, MessageType.PHASE_CHANGE)
        
        # 5. Pass priority
        priority_msg = self.protocol.create_message(MessageType.PASS_PRIORITY, {"player_id": 0})
        self.assertEqual(priority_msg.type, MessageType.PASS_PRIORITY)
        
        # All messages should be serializable
        messages = [join_msg, state_msg, play_msg, phase_msg, priority_msg]
        for msg in messages:
            serialized = msg.to_bytes()
            deserialized = NetworkMessage.from_bytes(serialized)
            self.assertEqual(deserialized.type, msg.type)
    
    def test_message_ordering_and_timing(self):
        """Test message ordering and timing requirements."""
        # Create a sequence of messages
        messages = []
        
        # Heartbeat messages should be spaced appropriately
        for i in range(3):
            heartbeat = self.protocol.create_heartbeat_message()
            messages.append(heartbeat)
            time.sleep(0.1)
        
        # Verify timestamps are ordered
        for i in range(1, len(messages)):
            self.assertGreater(messages[i].timestamp, messages[i-1].timestamp)
        
        # Time differences should be approximately 0.1 seconds
        for i in range(1, len(messages)):
            time_diff = messages[i].timestamp - messages[i-1].timestamp
            self.assertGreater(time_diff, 0.05)  # At least 50ms
            self.assertLess(time_diff, 0.2)     # Less than 200ms


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)
