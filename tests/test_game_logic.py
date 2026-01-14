"""
Unit tests for game logic.

Tests hand calculation (with Ace logic), bust detection, dealer decisions, and winner determination.
"""

import pytest
from src.common.card import Card
from src.common.game_logic import (
    calculate_hand_value, is_bust, dealer_decision, determine_winner
)


class TestHandCalculation:
    """Test calculate_hand_value function."""
    
    def test_simple_hand(self):
        """Test simple hand."""
        hand = [Card(10, 0), Card(5, 0), Card(6, 0)]
        assert calculate_hand_value(hand) == 21
    
    def test_face_cards(self):
        """Test face cards count as 10."""
        hand = [Card(12, 0), Card(13, 0)]
        assert calculate_hand_value(hand) == 20
    
    def test_ace_hand(self):
        """Test Ace counts as 11."""
        hand = [Card(1, 0), Card(5, 0)]
        assert calculate_hand_value(hand) == 16
    
    def test_ace_soft_17(self):
        """Test soft 17."""
        hand = [Card(1, 0), Card(6, 0)]
        assert calculate_hand_value(hand) == 17


class TestBustDetection:
    """Test is_bust function."""
    
    def test_not_bust(self):
        """Test 21 is not bust."""
        assert is_bust(21) == False
    
    def test_bust(self):
        """Test 22 is bust."""
        assert is_bust(22) == True


class TestDealerDecision:
    """Test dealer decision."""
    
    def test_hit_16(self):
        """Dealer hits on 16."""
        assert dealer_decision(16) == "Hit"
    
    def test_stand_17(self):
        """Dealer stands on 17."""
        assert dealer_decision(17) == "Stand"


class TestWinnerDetermination:
    """Test determine_winner function."""
    
    def test_player_win(self):
        """Player wins."""
        assert determine_winner(21, 20) == "win"
    
    def test_player_loss(self):
        """Player loses."""
        assert determine_winner(20, 21) == "loss"
    
    def test_tie(self):
        """Tie."""
        assert determine_winner(20, 20) == "tie"
