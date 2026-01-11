"""
Card class representing a single playing card.

Why a class instead of just tuples?
- Type clarity: Card(1, 0) vs (1, 0) - the former is obvious it's a card
- Encapsulates value logic: Card knows its blackjack value without asking caller
- Self-documenting: reader sees Card.value() and knows what to expect
"""

from config import (
    RANK_ACE, RANK_JACK, RANK_QUEEN, RANK_KING,
    SUIT_HEARTS, SUIT_DIAMONDS, SUIT_CLUBS, SUIT_SPADES,
    ACE_HIGH_VALUE, FACE_CARD_VALUE
)


class Card:
    """
    Represents a single playing card.
    
    Rank: 1-13 where:
    - 1 = Ace (special: value is 11 by default, 1 if hand would bust)
    - 2-10 = numeric cards (value = rank)
    - 11 = Jack (value = 10)
    - 12 = Queen (value = 10)
    - 13 = King (value = 10)
    
    Suit: 0-3 where:
    - 0 = Hearts ♥
    - 1 = Diamonds ♦
    - 2 = Clubs ♣
    - 3 = Spades ♠
    
    Cards are immutable once created: rank and suit never change.
    This means we can safely use them in collections without worrying about modification.
    """
    
    # Lookup tables for human-readable display
    RANK_NAMES = {
        1: "Ace", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7",
        8: "8", 9: "9", 10: "10", 11: "Jack", 12: "Queen", 13: "King"
    }
    
    SUIT_NAMES = {0: "Hearts", 1: "Diamonds", 2: "Clubs", 3: "Spades"}
    SUIT_SYMBOLS = {0: "♥", 1: "♦", 2: "♣", 3: "♠"}
    
    def __init__(self, rank, suit):
        """
        Initialize a card.
        
        Args:
            rank (int): 1-13 (must be valid)
            suit (int): 0-3 (must be valid)
        """
        self.rank = rank
        self.suit = suit
    
    def value(self):
        """
        Return the blackjack value of this card (not the rank).
        
        Examples:
        - Ace (rank 1) → 11 (caller handles Ace-as-1 logic separately)
        - 5 (rank 5) → 5
        - Jack (rank 11) → 10
        - King (rank 13) → 10
        
        Why separate value() from rank?
        The rank stays 1-13 (encoded in protocol), but blackjack value is different.
        This method does the conversion. Caller (game_logic.py) handles Ace-as-1 recalculation
        when hand exceeds 21.
        """
        if self.rank == RANK_ACE:
            return ACE_HIGH_VALUE  # 11
        elif self.rank >= RANK_JACK:
            return FACE_CARD_VALUE  # 10
        else:
            return self.rank
    
    def __str__(self):
        """
        Return human-readable card name.
        Example: "Ace of Hearts" or "King♠"
        """
        return f"{self.RANK_NAMES[self.rank]} of {self.SUIT_NAMES[self.suit]}"
    
    def __repr__(self):
        """
        Return concise representation for debugging.
        Example: "Card(1, 0)" or "A♥"
        """
        return f"{self.RANK_NAMES[self.rank][0]}{self.SUIT_SYMBOLS[self.suit]}"
    
    def is_ace(self):
        """Return True if this card is an Ace."""
        return self.rank == RANK_ACE
    
    def __str__(self):
        """Return readable representation (e.g., 'Ace of Hearts')."""
        return f"{self.RANK_NAMES[self.rank]} of {self.SUIT_NAMES[self.suit]}"
    
    def __repr__(self):
        """Return compact representation with symbols (e.g., 'A♥')."""
        return f"{self.RANK_NAMES[self.rank][0]}{'23456789X'[self.rank-1] if 2 <= self.rank <= 10 else ''}{self.SUIT_SYMBOLS[self.suit]}"
    
    def encode(self):
        """
        Encode card for protocol transmission.
        Returns: (rank_bytes, suit_byte) as 3 total bytes
        """
        return (self.rank, self.suit)
