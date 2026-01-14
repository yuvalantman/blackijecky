"""
Unit tests for Card class.

Tests card rank/suit encoding, value calculation, and Ace handling.
"""

import pytest
from src.common.card import Card


class TestCard:
    """Test Card class functionality."""
    
    def test_card_creation(self):
        """Test creating a card."""
        card = Card(5, 0)  # 5 of Hearts
        assert card.rank == 5
        assert card.suit == 0
    
    def test_card_numeric_values(self):
        """Test numeric cards have correct blackjack value."""
        for rank in range(2, 11):  # 2-10
            card = Card(rank, 0)
            assert card.value() == rank
    
    def test_face_cards_value_10(self):
        """Test Jack, Queen, King have value 10."""
        for rank in [11, 12, 13]:  # Jack, Queen, King
            card = Card(rank, 0)
            assert card.value() == 10
    
    def test_ace_value_11(self):
        """Test Ace has value 11 in blackjack."""
        card = Card(1, 0)  # Ace
        assert card.value() == 11
    
    def test_all_suits(self):
        """Test all four suits."""
        suits = [0, 1, 2, 3]  # Hearts, Diamonds, Clubs, Spades
        for suit in suits:
            card = Card(5, suit)
            assert card.suit == suit
    
    def test_card_str_representation(self):
        """Test card string representation."""
        card = Card(1, 0)
        str_repr = str(card)
        assert "Ace" in str_repr or "1" in str_repr
        
        card = Card(5, 0)
        str_repr = str(card)
        assert "5" in str_repr
    
    def test_card_equality(self):
        """Test two cards with same rank/suit are equal."""
        card1 = Card(5, 0)
        card2 = Card(5, 0)
        assert card1.rank == card2.rank
        assert card1.suit == card2.suit
    
    def test_card_inequality(self):
        """Test different cards are not equal."""
        card1 = Card(5, 0)
        card2 = Card(5, 1)  # Different suit
        assert card1.suit != card2.suit
        
        card3 = Card(6, 0)  # Different rank
        assert card1.rank != card3.rank
    
    def test_all_ranks_and_suits(self):
        """Test all valid rank/suit combinations."""
        for rank in range(1, 14):  # 1-13
            for suit in range(0, 4):  # 0-3
                card = Card(rank, suit)
                assert card.rank == rank
                assert card.suit == suit
