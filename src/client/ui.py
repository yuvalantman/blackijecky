"""
User interface for the Blackjack client.

Handles all I/O: displaying cards, asking for decisions, showing server list, etc.
Separated from network logic so if we want to add a GUI later, only this file changes.

Design principle: Keep I/O logic away from network code.
This file is the *only* place that uses print() and input().
"""

from src.common.card import Card


def display_card(card):
    """
    Format a card as a readable string.
    
    Args:
        card (Card): Card object
    
    Returns:
        str: Human-readable card (e.g., "Ace♥", "10♦", "King♣")
    """
    # Rank names for display
    rank_names = {
        1: "Ace",
        2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 8: "8", 9: "9", 10: "10",
        11: "Jack",
        12: "Queen",
        13: "King"
    }
    
    # Suit symbols (Unicode)
    suit_symbols = {
        0: "♥",  # Hearts
        1: "♦",  # Diamonds
        2: "♣",  # Clubs
        3: "♠"   # Spades
    }
    
    rank_str = rank_names.get(card.rank, str(card.rank))
    suit_str = suit_symbols.get(card.suit, "?")
    
    return f"{rank_str}{suit_str}"


def show_hand(cards, is_player=True, hide_second=False):
    """
    Display a hand of cards nicely.
    
    Args:
        cards (list[Card]): List of cards
        is_player (bool): True for player's hand, False for dealer's
        hide_second (bool): If True, hide the second card (dealer's hole card)
    
    Returns:
        str: Formatted hand display
    """
    if not cards:
        return "No cards"
    
    # Display each card
    card_strs = []
    for i, card in enumerate(cards):
        if hide_second and i == 1:
            card_strs.append("[Hidden]")
        else:
            card_strs.append(display_card(card))
    
    hand_str = ", ".join(card_strs)
    
    # Calculate value if we're not hiding any card
    if not hide_second or len(cards) == 0:
        value = sum(c.value() for c in cards)
        # Handle Ace logic: if over 21 and we have Aces, count one as 1 instead of 11
        aces = sum(1 for c in cards if c.rank == 1)
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1
        hand_str += f" (value: {value})"
    
    return hand_str


def show_servers(servers):
    """
    Display list of available servers for user to choose.
    
    Args:
        servers (list[dict]): List of server info dicts with keys: ip, port, name
    
    Returns:
        int: Server number (1-indexed) that user selected, or 0 to refresh
    """
    if not servers:
        print("\n[No servers found yet... waiting for broadcasts]")
        return 0
    
    print("\n" + "="*60)
    print("Available Servers:")
    print("="*60)
    
    for i, server in enumerate(servers, 1):
        print(f"{i}. {server['name']} @ {server['ip']}:{server['port']}")
    
    print("0. Refresh list")
    print("="*60)
    
    while True:
        try:
            choice = input(f"Select server (0-{len(servers)}): ").strip()
            choice = int(choice)
            if 0 <= choice <= len(servers):
                return choice
            else:
                print(f"Invalid choice. Please enter 0-{len(servers)}")
        except ValueError:
            print("Please enter a valid number")


def get_player_decision():
    """
    Ask the player whether to Hit or Stand.
    
    Returns:
        str: "hit" or "stand" (lowercase)
    """
    while True:
        choice = input("\nHit or Stand? (h/s): ").strip().lower()
        if choice in ['h', 'hit']:
            return "hit"
        elif choice in ['s', 'stand']:
            return "stand"
        else:
            print("Please enter 'h' for Hit or 's' for Stand")


def show_result(result_code):
    """
    Display the result of a round.
    
    Args:
        result_code (int): 0x1=tie, 0x2=loss, 0x3=win
    """
    results = {
        0x1: "TIE",
        0x2: "LOSS - Dealer wins",
        0x3: "WIN - You win!"
    }
    
    result_str = results.get(result_code, "Unknown result")
    print(f"\nRound result: {result_str}")


def show_round_header(round_num, total_rounds):
    """Display a header for the current round."""
    print(f"\n{'='*60}")
    print(f"Round {round_num}/{total_rounds}")
    print(f"{'='*60}")


def show_game_start(team_name, num_rounds, server_name):
    """Display game start information."""
    print(f"\nConnected to {server_name}")
    print(f"Team: {team_name}")
    print(f"Rounds: {num_rounds}")
    print("Starting game...")


def show_hand_update(hand_type, cards, is_dealer=False):
    """
    Display an updated hand during gameplay.
    
    Args:
        hand_type (str): "Your hand" or "Dealer shows"
        cards (list[Card]): Cards in the hand
        is_dealer (bool): True if dealer's hand, False if player's
    """
    display = show_hand(cards, is_player=(not is_dealer), hide_second=False)
    print(f"{hand_type}: {display}")


def show_statistics(wins, losses, ties, total_rounds):
    """
    Display final game statistics.
    
    Args:
        wins (int): Number of rounds won
        losses (int): Number of rounds lost
        ties (int): Number of ties
        total_rounds (int): Total rounds played
    """
    win_rate = (wins / total_rounds * 100) if total_rounds > 0 else 0
    
    print("\n" + "="*60)
    print("FINAL STATISTICS")
    print("="*60)
    print(f"Wins:        {wins}")
    print(f"Losses:      {losses}")
    print(f"Ties:        {ties}")
    print(f"Total:       {total_rounds}")
    print(f"Win rate:    {win_rate:.1f}%")
    print("="*60)


def show_error(message):
    """Display an error message."""
    print(f"\n[ERROR] {message}")


def show_info(message):
    """Display an info message."""
    print(f"\n[INFO] {message}")


def get_team_name():
    """
    Get team name from user input.
    
    Returns:
        str: Team name (max 32 chars)
    """
    while True:
        name = input("\nEnter your team name: ").strip()
        if 1 <= len(name) <= 32:
            return name
        else:
            print("Team name must be 1-32 characters")


def get_num_rounds():
    """
    Get number of rounds from user input.
    
    Returns:
        int: Number of rounds (1-255)
    """
    while True:
        try:
            num = int(input("Enter number of rounds (1-255): ").strip())
            if 1 <= num <= 255:
                return num
            else:
                print("Number must be between 1 and 255")
        except ValueError:
            print("Please enter a valid number")


def ask_play_again():
    """
    Ask user if they want to play again.
    
    Returns:
        bool: True to play again, False to quit
    """
    while True:
        choice = input("\nPlay again? (y/n): ").strip().lower()
        if choice in ['y', 'yes']:
            return True
        elif choice in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' for yes or 'n' for no")


def show_bust_message(is_player):
    """Display bust message."""
    who = "You" if is_player else "Dealer"
    print(f"\n{who} BUST!")


def show_game_over_message():
    """Display game over message."""
    print("\n" + "="*60)
    print("GAME OVER")
    print("="*60)
