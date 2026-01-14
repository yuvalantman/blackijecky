"""
Main client entry point for Blackjack game.

Flow:
1. Get team name and number of rounds from user
2. Start background offer_listener thread
3. Main loop:
   - Show available servers
   - User picks server
   - Connect and play game
   - Show statistics
   - Ask to play again
4. Exit

Design principle: Background listener for discovery, foreground loop for user input.
"""

import threading
import time
from src.client.offer_listener import OfferListener
from src.client.game_client import GameClient
from src.client.ui import (
    get_team_name, get_num_rounds, show_servers, get_player_decision,
    show_round_header, show_hand, show_result, show_statistics,
    show_error, show_info, ask_play_again, show_bust_message,
    show_game_start, display_card
)


class GameSessionHandler:
    """Handles UI interactions during a game session."""
    
    def __init__(self):
        self.player_cards = []
        self.dealer_cards = []
    
    def show_round(self, round_num, total_rounds):
        """Show round header."""
        show_round_header(round_num, total_rounds)
    
    def show_initial_cards(self, player_cards, dealer_first_card):
        """Show initial dealt cards."""
        self.player_cards = player_cards
        self.dealer_cards = [dealer_first_card]
        
        print("\nInitial deal:")
        print(f"Your hand: {show_hand(self.player_cards, is_player=True)}")
        print(f"Dealer showing: {display_card(dealer_first_card)}")
    
    def get_player_decision(self):
        """Get Hit or Stand decision from player."""
        return get_player_decision()
    
    def show_card(self, card, is_player):
        """Show a card that was dealt."""
        if is_player:
            # Card already appended to player_cards in game_client.py
            print(f"You drew: {display_card(card)}")
            print(f"Your hand: {show_hand(self.player_cards, is_player=True)}")
        else:
            # Card already appended to dealer_cards in game_client.py
            print(f"Dealer drew: {display_card(card)}")
    
    def show_bust(self, is_player):
        """Show bust message."""
        show_bust_message(is_player)
    
    def show_result(self, result_code, player_cards=None, dealer_cards=None):
        """Show round result with optional hand details."""
        show_result(result_code, player_cards, dealer_cards)
    
    def show_error(self, msg):
        """Show error message."""
        show_error(msg)


def main():
    """Main client application."""
    
    # Get team name and number of rounds from user
    print("\n" + "="*60)
    print("BLACKJACK CLIENT")
    print("="*60)
    
    team_name = get_team_name()
    num_rounds = get_num_rounds()
    
    # Start background listener thread
    print("\nStarting server discovery...")
    listener = OfferListener()
    listener_thread = threading.Thread(target=listener.run, daemon=True)
    listener_thread.start()
    
    # Give listener time to receive some offers
    time.sleep(2)
    
    # Main loop: play games
    while True:
        # Show available servers
        while True:
            offers = listener.get_offers()
            choice = show_servers(offers)
            
            if choice == 0:
                # Refresh
                time.sleep(1)
                continue
            
            if choice > 0 and choice <= len(offers):
                # User selected a server
                selected = offers[choice - 1]
                break
        
        # Connect and play
        try:
            show_game_start(team_name, num_rounds, selected['name'])
            
            # Create game client
            game_client = GameClient(
                selected['ip'],
                selected['port'],
                team_name,
                num_rounds
            )
            
            # Create UI handler
            handler = GameSessionHandler()
            
            # Play game
            if game_client.play_game(handler):
                # Get statistics
                stats = game_client.get_statistics()
                show_statistics(
                    stats['wins'],
                    stats['losses'],
                    stats['ties'],
                    num_rounds
                )
            else:
                show_error("Game session failed")
        
        except Exception as e:
            show_error(f"Exception during gameplay: {e}")
        
        # Ask to play again
        if not ask_play_again():
            print("\nThanks for playing!")
            break
    
    # Cleanup
    listener.stop()


if __name__ == "__main__":
    main()
