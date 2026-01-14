"""
TCP communication with server during gameplay.

This handles the game-session part of the protocol:
1. Connect to server TCP port
2. Send request (num_rounds, team_name)
3. For each round:
   - Receive initial cards
   - Hit/Stand loop
   - Receive result
4. Close

Separated from offer_listener so we can have discovery (UDP) independent from gameplay (TCP).
"""

import socket
import struct
from src.common.protocol import (
    encode_request, decode_payload_card, decode_payload_result,
    encode_payload_player_decision
)
from src.common.card import Card
from config import SOCKET_TIMEOUT


class GameClient:
    def __init__(self, server_ip, server_port, team_name, num_rounds):
        """
        Initialize game client.
        
        Args:
            server_ip (str): IP address to connect to
            server_port (int): TCP port to connect to
            team_name (str): This team's name
            num_rounds (int): How many rounds to play
        """
        self.server_ip = server_ip
        self.server_port = server_port
        self.team_name = team_name
        self.num_rounds = num_rounds
        self.socket = None
        self.wins = 0
        self.losses = 0
        self.ties = 0
    
    def connect(self):
        """
        Connect to server.
        
        Returns:
            bool: True if connection successful
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(SOCKET_TIMEOUT)
            self.socket.connect((self.server_ip, self.server_port))
            print(f"Connected to server at {self.server_ip}:{self.server_port}")
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
    
    def send_request(self):
        """
        Send initial request message (team name, num rounds).
        
        Returns:
            bool: True if successful
        """
        try:
            msg = encode_request(self.num_rounds, self.team_name)
            self.socket.sendall(msg)
            return True
        except Exception as e:
            print(f"Failed to send request: {e}")
            return False
    
    def receive_cards(self):
        """
        Receive player's initial hand (2 cards) and dealer's first card.
        
        Returns:
            tuple: (player_cards, dealer_first_card) where cards are Card objects
                   or (None, None) if error
        """
        try:
            # Each card is 3 bytes: 2 for rank, 1 for suit
            # We expect 3 cards: 2 player + 1 dealer
            player_cards = []
            
            # Receive first player card
            data = self.socket.recv(3)
            if len(data) < 3:
                raise ValueError("Incomplete card data")
            rank, suit = decode_payload_card(data)
            player_cards.append(Card(rank, suit))
            
            # Receive second player card
            data = self.socket.recv(3)
            if len(data) < 3:
                raise ValueError("Incomplete card data")
            rank, suit = decode_payload_card(data)
            player_cards.append(Card(rank, suit))
            
            # Receive dealer's first card
            data = self.socket.recv(3)
            if len(data) < 3:
                raise ValueError("Incomplete card data")
            rank, suit = decode_payload_card(data)
            dealer_card = Card(rank, suit)
            
            return player_cards, dealer_card
        
        except Exception as e:
            print(f"Error receiving initial cards: {e}")
            return None, None
    
    def send_decision(self, decision):
        """
        Send player's Hit or Stand decision.
        
        Args:
            decision (str): "hit" or "stand"
        
        Returns:
            bool: True if successful
        """
        try:
            msg = encode_payload_player_decision(decision)
            self.socket.sendall(msg)
            return True
        except Exception as e:
            print(f"Failed to send decision: {e}")
            return False
    
    def receive_server_response(self):
        """
        Receive response from server after sending decision.
        Could be a card (if we hit) or a result code (if game over).
        
        Returns:
            dict: {type: "card"|"result", card: Card or code: int}
                  or None if error
        """
        try:
            # First byte tells us what we're receiving
            data = self.socket.recv(1)
            if len(data) < 1:
                raise ValueError("Empty response")
            
            msg_type = data[0]
            
            # 0x4 = payload type, next byte tells us specific type
            if msg_type == 0x4:
                # Read next byte to see if it's card or result
                data = self.socket.recv(1)
                if len(data) < 1:
                    raise ValueError("Incomplete payload type")
                
                payload_type = data[0]
                
                # 0x0 = card (rank/suit follows)
                if payload_type == 0x0:
                    card_data = self.socket.recv(3)
                    if len(card_data) < 3:
                        raise ValueError("Incomplete card data")
                    rank, suit = decode_payload_card(card_data)
                    return {
                        'type': 'card',
                        'card': Card(rank, suit)
                    }
                
                # 0x1 or other = result code
                else:
                    result_data = self.socket.recv(1)
                    if len(result_data) < 1:
                        raise ValueError("Incomplete result")
                    result_code = result_data[0]
                    
                    # Update statistics
                    if result_code == 0x1:
                        self.ties += 1
                    elif result_code == 0x2:
                        self.losses += 1
                    elif result_code == 0x3:
                        self.wins += 1
                    
                    return {
                        'type': 'result',
                        'code': result_code
                    }
        
        except Exception as e:
            print(f"Error receiving server response: {e}")
            return None
    
    def play_game(self, game_handler):
        """
        Main game loop: play all rounds.
        
        Args:
            game_handler: Callback object with methods:
                - show_initial_cards(player_cards, dealer_card)
                - get_player_decision() -> "hit" or "stand"
                - show_card(card, is_player)
                - show_result(result_code)
                - show_error(msg)
        
        Returns:
            bool: True if all rounds completed
        """
        if not self.connect():
            return False
        
        if not self.send_request():
            return False
        
        for round_num in range(1, self.num_rounds + 1):
            game_handler.show_round(round_num, self.num_rounds)
            
            # Get initial cards
            player_cards, dealer_card = self.receive_cards()
            if player_cards is None:
                game_handler.show_error("Failed to receive initial cards")
                return False
            
            # Show initial state
            game_handler.show_initial_cards(player_cards, dealer_card)
            
            # Player turn loop
            while True:
                decision = game_handler.get_player_decision()
                
                if not self.send_decision(decision):
                    game_handler.show_error("Failed to send decision")
                    return False
                
                # Receive server response
                response = self.receive_server_response()
                if response is None:
                    game_handler.show_error("Failed to receive server response")
                    return False
                
                if response['type'] == 'card':
                    # We hit and got a card
                    card = response['card']
                    player_cards.append(card)
                    game_handler.show_card(card, is_player=True)
                    
                    # Check if we bust
                    hand_value = sum(c.value() for c in player_cards)
                    aces = sum(1 for c in player_cards if c.rank == 1)
                    while hand_value > 21 and aces > 0:
                        hand_value -= 10
                        aces -= 1
                    
                    if hand_value > 21:
                        game_handler.show_bust(is_player=True)
                        break
                
                elif response['type'] == 'result':
                    # Game over
                    result_code = response['code']
                    game_handler.show_result(result_code)
                    break
        
        self.close()
        return True
    
    def close(self):
        """Close connection to server."""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
    
    def get_statistics(self):
        """
        Get game statistics.
        
        Returns:
            dict: {wins, losses, ties}
        """
        return {
            'wins': self.wins,
            'losses': self.losses,
            'ties': self.ties
        }
