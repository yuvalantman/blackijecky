"""
Core blackjack game logic and rules.
"""

from config import DEALER_HIT_THRESHOLD, MAX_HAND_VALUE, ACE_LOW_VALUE


def calculate_hand_value(cards):
    """
    Calculate the total value of a hand, handling Aces intelligently.
    
    Aces are initially counted as 11. If the total exceeds 21 and there are
    Aces in the hand, we recalculate them as 1 (one at a time) until we're
    under 21 or we've used all Aces.
    
    Args:
        cards (list): List of Card objects
    
    Returns:
        int: Total hand value (typically 0-21, can exceed for bust detection)
    """
    if not cards:
        return 0
    
    total = sum(card.value() for card in cards)
    num_aces = sum(1 for card in cards if card.is_ace())
    
    # Recalculate Aces as 1 if busting
    while total > MAX_HAND_VALUE and num_aces > 0:
        total -= 10  # Convert one Ace from 11 to 1 (11 - 10 = 1)
        num_aces -= 1
    
    return total


def is_bust(hand_value):
    """
    Check if a hand value is a bust (over 21).
    
    Args:
        hand_value (int): Total value of hand
    
    Returns:
        bool: True if busted
    """
    return hand_value > MAX_HAND_VALUE


def dealer_decision(dealer_value):
    """
    Determine if dealer should hit or stand.
    
    Dealer logic is deterministic: hit if < 17, stand if >= 17.
    
    Args:
        dealer_value (int): Current total of dealer's hand
    
    Returns:
        str: "Hit" or "Stand"
    """
    if dealer_value < DEALER_HIT_THRESHOLD:
        return "Hit"
    else:
        return "Stand"


def determine_winner(player_value, dealer_value, player_busted=False, dealer_busted=False):
    """
    Determine the outcome of a round.
    
    Args:
        player_value (int): Player's hand total
        dealer_value (int): Dealer's hand total
        player_busted (bool): Did player bust?
        dealer_busted (bool): Did dealer bust?
    
    Returns:
        str: "win", "loss", or "tie"
    """
    if player_busted:
        return "loss"
    if dealer_busted:
        return "win"
    
    if player_value > dealer_value:
        return "win"
    elif dealer_value > player_value:
        return "loss"
    else:
        return "tie"


def result_to_code(result_str):
    """
    Convert result string to protocol code.
    
    Args:
        result_str (str): "win", "loss", or "tie"
    
    Returns:
        int: 0x1 (tie), 0x2 (loss), or 0x3 (win)
    """
    codes = {"tie": 0x1, "loss": 0x2, "win": 0x3}
    return codes.get(result_str, 0x0)


def code_to_result(code):
    """
    Convert protocol code to result string.
    
    Args:
        code (int): 0x1, 0x2, or 0x3
    
    Returns:
        str: "tie", "loss", or "win"
    """
    names = {0x1: "tie", 0x2: "loss", 0x3: "win"}
    return names.get(code, "unknown")
