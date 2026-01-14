"""
Unit tests for Deck class.

Tests deck creation, shuffling, and drawing cards.
"""

import pytest
from src.common.deck import Deck
from src.common.card import Card


class TestDeck:
    """Test Deck class functionality."""
    
    def test_deck_creation(self):
        """Test creating a fresh deck."""
        deck = Deck()
        # Should have 52 cards initially
        assert len(deck.cards) == 52
    
    def test_deck_has_all_cards(self):
        """Test deck contains all 52 unique cards."""
        deck = Deck()
        
        # Check we have 13 ranks
        ranks = set()
        suits = set()
        for card in deck.cards:
            ranks.add(card.rank)
            suits.add(card.suit)
        
        assert len(ranks) == 13  # 1-13
        assert len(suits) == 4   # 0-3
    
    def test_deck_shuffle(self):
        """Test deck is shuffled (not in order)."""
        deck1 = Deck()
        deck2 = Deck()
        
        # Both have same cards, but probably in different order
        # (extremely unlikely to shuffle to exact same order twice)
        ranks1 = [c.rank for c in deck1.cards[:10]]
        ranks2 = [c.rank for c in deck2.cards[:10]]
        
        # Chances of being identical: negligible
        # This test is probabilistic but should pass >99.99% of time
        # If it fails, that would indicate shuffle isn't working
        assert ranks1 != ranks2 or len(ranks1) == 0
    
    def test_draw_card(self):
        """Test drawing a card from deck."""
        deck = Deck()
        
        card = deck.draw()
        assert isinstance(card, Card)
        assert 1 <= card.rank <= 13
        assert 0 <= card.suit <= 3
        
        # After drawing, deck should have 51 cards remaining
        assert deck.cards_remaining() == 51
    
    def test_draw_multiple_cards(self):
        """Test drawing multiple cards."""
        deck = Deck()
        
        cards = []
        for i in range(10):
            card = deck.draw()
            cards.append(card)
            assert deck.cards_remaining() == 52 - (i + 1)
    
    def test_cannot_draw_more_than_52(self):
        """Test can't draw more than 52 cards."""
        deck = Deck()
        
        # Draw all 52 cards
        for _ in range(52):
            card = deck.draw()
            assert card is not None
        
        # 53rd card should raise IndexError
        with pytest.raises(IndexError):
            deck.draw()
    
    def test_draw_order_is_shuffled(self):
        """Test cards are drawn in shuffled order, not sequential."""
        deck = Deck()
        
        # Draw first 5 cards
        first_five = [deck.draw() for _ in range(5)]
        
        # Get their ranks
        ranks = [c.rank for c in first_five]
        
        # Should not be 1,2,3,4,5 (sequential order unlikely after shuffle)
        # This is probabilistic but failure would suggest no shuffle
        assert ranks != [1, 2, 3, 4, 5]
    
    def test_multiple_decks_different_order(self):
        """Test different Deck instances have different order."""
        decks = [Deck() for _ in range(5)]
        
        # Get first 10 cards from each
        orders = []
        for deck in decks:
            order = [c.rank for c in deck.cards[:10]]
            orders.append(order)
        
        # All 5 orders should not be identical
        # (extremely unlikely for 5 independent shuffles to produce same result)
        for i in range(1, len(orders)):
            assert orders[0] != orders[i] or len(orders[0]) == 0
