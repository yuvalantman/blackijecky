"""
Deck class for managing a standard 52-card deck.

Why encapsulate deck management in a class?
- Prevents mistakes: Can't accidentally draw from an exhausted deck
- Tracks state: Knows which cards have been drawn
- Single responsibility: Only deck cares about deck internals
- Easy to shuffle and reset for new rounds

Design choice: Fresh deck per round
The spec says "dealer shuffles the deck" each round. We interpret this as:
create a fresh deck and shuffle it. This avoids complex state tracking
(what happens after 100 draws from same deck? Reshuffle? Start new?).
Fresh deck is simpler and matches typical blackjack.
"""

import random
from config import DECK_SIZE, RANKS_PER_SUIT, SUITS
from .card import Card


class Deck:
    """
    Standard 52-card deck (13 ranks × 4 suits).
    
    Creates and shuffles automatically on init. Cards are drawn in shuffle order.
    For a new round, create a new Deck() object.
    
    Why not reset an existing deck?
    - Less state to track
    - Clearer intent: new Deck = new game
    - Avoids off-by-one bugs in index management
    """
    
    def __init__(self):
        """
        Create a new deck with all 52 cards and shuffle.
        
        The deck is ready to draw from immediately.
        """
        self.cards = []
        self._create_deck()
        # Don't shuffle in _create_deck; separate concerns
        self.shuffle()
        self.index = 0  # Track position in deck (0-51)
    
    def _create_deck(self):
        """
        Create all 52 cards in order (not shuffled yet).
        
        Iterates: Suit 0 Ranks 1-13, Suit 1 Ranks 1-13, ...
        This is deterministic so we can verify the deck is complete.
        """
        for suit in range(SUITS):
            for rank in range(1, RANKS_PER_SUIT + 1):
                self.cards.append(Card(rank, suit))
    
    def shuffle(self):
        """
        Randomize card order using Fisher-Yates shuffle (via random.shuffle).
        
        Called automatically by __init__, but available if you need to reshuffle.
        Resets index to 0 so drawing starts from the beginning.
        
        Why shuffle in place instead of creating new list?
        - More efficient (no copy)
        - Clearer intent (shuffle this deck, don't create new one)
        """
        random.shuffle(self.cards)
        self.index = 0
    
    def draw(self):
        """
        Draw and return the next card from the deck.
        
        Returns:
            Card: Next card in shuffled order
        
        Raises:
            IndexError: If all 52 cards have been drawn already
        
        Why raise IndexError instead of returning None?
        - Explicit error tells caller exactly what went wrong
        - Prevents silent bugs (None wouldn't crash, but causes confusion later)
        - Matches Python conventions (list indexing raises IndexError)
        """
        if self.index >= len(self.cards):
            raise IndexError(f"Deck exhausted - drew all 52 cards, no more available")
        card = self.cards[self.index]
        self.index += 1
        return card
    
    def cards_remaining(self):
        """
        Return the number of cards left in deck.
        
        Useful for: debugging, deciding whether to reshuffle (advanced feature)
        """
        return len(self.cards) - self.index
    
    def is_empty(self):
        """Return True if all cards have been drawn."""
        return self.index >= len(self.cards)
