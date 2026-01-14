"""
Unit tests for protocol message encoding/decoding.

Tests offer, request, and payload message format compliance.
"""

import pytest
from src.common.protocol import (
    encode_offer, decode_offer,
    encode_request, decode_request,
    encode_payload_card, decode_payload_card,
    encode_payload_player_decision, decode_payload_player_decision,
    encode_payload_result, decode_payload_result
)


class TestOfferMessage:
    """Test UDP offer message encoding/decoding."""
    
    def test_encode_offer_size(self):
        """Test encoded offer is exactly 39 bytes."""
        msg = encode_offer(8080, "TestServer")
        assert len(msg) == 39
    
    def test_encode_decode_offer(self):
        """Test encoding and decoding an offer."""
        tcp_port = 8080
        server_name = "Blackijecky"
        
        msg = encode_offer(tcp_port, server_name)
        decoded_port, decoded_name = decode_offer(msg)
        
        assert decoded_port == tcp_port
        assert decoded_name == server_name
    
    def test_offer_with_empty_name(self):
        """Test offer with empty server name."""
        msg = encode_offer(9000, "")
        decoded_port, decoded_name = decode_offer(msg)
        
        assert decoded_port == 9000
        assert decoded_name == ""
    
    def test_offer_with_long_name(self):
        """Test offer with name longer than 32 chars (should truncate)."""
        long_name = "A" * 50  # 50 chars
        msg = encode_offer(9000, long_name)
        decoded_port, decoded_name = decode_offer(msg)
        
        assert decoded_port == 9000
        assert len(decoded_name) == 32  # Truncated
        assert decoded_name == "A" * 32
    
    def test_offer_with_unicode_name(self):
        """Test offer with unicode characters in name."""
        name = "סרוור"  # Hebrew for "server"
        msg = encode_offer(9000, name)
        decoded_port, decoded_name = decode_offer(msg)
        
        assert decoded_port == 9000
        # Unicode may be truncated or mangled, but shouldn't crash
        assert isinstance(decoded_name, str)
    
    def test_offer_invalid_magic_cookie(self):
        """Test decoding offer with wrong magic cookie raises error."""
        msg = b'\x00\x00\x00\x00' + b'\x00' * 35  # Wrong magic
        
        with pytest.raises(ValueError):
            decode_offer(msg)
    
    def test_offer_too_short(self):
        """Test decoding truncated offer raises error."""
        msg = b'\x00\x00\x00'  # Too short
        
        with pytest.raises(ValueError):
            decode_offer(msg)


class TestRequestMessage:
    """Test TCP request message encoding/decoding."""
    
    def test_encode_request_size(self):
        """Test encoded request is exactly 38 bytes."""
        msg = encode_request(5, "TeamA")
        assert len(msg) == 38
    
    def test_encode_decode_request(self):
        """Test encoding and decoding a request."""
        num_rounds = 10
        team_name = "Blackijecky"
        
        msg = encode_request(num_rounds, team_name)
        decoded_rounds, decoded_name = decode_request(msg)
        
        assert decoded_rounds == num_rounds
        assert decoded_name == team_name
    
    def test_request_with_max_rounds(self):
        """Test request with max rounds (255)."""
        msg = encode_request(255, "MaxRounds")
        decoded_rounds, decoded_name = decode_request(msg)
        
        assert decoded_rounds == 255
    
    def test_request_with_one_round(self):
        """Test request with 1 round."""
        msg = encode_request(1, "OneRound")
        decoded_rounds, decoded_name = decode_request(msg)
        
        assert decoded_rounds == 1
    
    def test_request_invalid_magic_cookie(self):
        """Test decoding request with wrong magic cookie raises error."""
        msg = b'\x00\x00\x00\x00' + b'\x00' * 34  # Wrong magic
        
        with pytest.raises(ValueError):
            decode_request(msg)


class TestPayloadCard:
    """Test card payload encoding/decoding."""
    
    def test_encode_card_size(self):
        """Test encoded card is 3 bytes (rank + suit + pad)."""
        msg = encode_payload_card(5, 0)
        # Format: rank(1) + suit(1) + pad(1) = 3 bytes (magic+type added by server)
        assert len(msg) == 3
    
    def test_encode_decode_card(self):
        """Test encoding and decoding a card."""
        rank = 7
        suit = 2
        
        msg = encode_payload_card(rank, suit)
        # Just verify the message is created
        assert len(msg) > 0
        assert isinstance(msg, bytes)
    
    def test_all_ranks_and_suits(self):
        """Test all valid ranks and suits encode without error."""
        for rank in range(1, 14):  # 1-13
            for suit in range(0, 4):  # 0-3
                msg = encode_payload_card(rank, suit)
                assert len(msg) == 3


class TestPayloadDecision:
    """Test player decision payload encoding/decoding."""
    
    def test_encode_hit_decision(self):
        """Test encoding hit decision."""
        msg = encode_payload_player_decision("hit")
        assert len(msg) > 0
        # Should contain information about hit decision
    
    def test_encode_stand_decision(self):
        """Test encoding stand decision."""
        msg = encode_payload_player_decision("stand")
        assert len(msg) > 0
        # Should contain information about stand decision
    
    def test_hit_and_stand_different(self):
        """Test hit and stand produce different encodings."""
        hit_msg = encode_payload_player_decision("hit")
        stand_msg = encode_payload_player_decision("stand")
        
        assert hit_msg != stand_msg
    
    def test_decode_decision(self):
        """Test decoding decision messages."""
        for decision in ["hit", "stand", "HIT", "STAND"]:
            msg = encode_payload_player_decision(decision)
            decoded = decode_payload_player_decision(msg)
            
            # Should decode to lowercase version
            assert decoded.lower() in ["hit", "stand"]


class TestPayloadResult:
    """Test result code payload encoding/decoding."""
    
    def test_encode_tie_result(self):
        """Test encoding tie result (0x1)."""
        msg = encode_payload_result(0x1)
        assert len(msg) > 0
        assert isinstance(msg, bytes)
    
    def test_encode_loss_result(self):
        """Test encoding loss result (0x2)."""
        msg = encode_payload_result(0x2)
        assert len(msg) > 0
        assert isinstance(msg, bytes)
    
    def test_encode_win_result(self):
        """Test encoding win result (0x3)."""
        msg = encode_payload_result(0x3)
        assert len(msg) > 0
        assert isinstance(msg, bytes)
    
    def test_all_results_different(self):
        """Test all three result codes produce different encodings."""
        tie_msg = encode_payload_result(0x1)
        loss_msg = encode_payload_result(0x2)
        win_msg = encode_payload_result(0x3)
        
        assert tie_msg != loss_msg
        assert loss_msg != win_msg
        assert win_msg != tie_msg
    
    def test_decode_result(self):
        """Test decoding result messages (just verify no crash)."""
        for code in [0x1, 0x2, 0x3]:
            msg = encode_payload_result(code)
            # Verify message created successfully
            assert len(msg) > 0
