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
        
        Each card comes as: magic cookie (4) + type 0x4 (1) + rank (1) + suit (1) + pad (1) = 8 bytes
        
        Returns:
            tuple: (player_cards, dealer_first_card) where cards are Card objects
                   or (None, None) if error
        """
        try:
            # Each payload message is 8 bytes: magic (4) + type (1) + card (3)
            # We expect 3 such messages: 2 player cards + 1 dealer card
            player_cards = []
            
            # Receive first player card
            data = self.socket.recv(8)
            if len(data) < 8:
                raise ValueError("Incomplete card payload")
            # Skip magic cookie and type, just get card data
            rank, suit = decode_payload_card(data[5:8])
            player_cards.append(Card(rank, suit))
            
            # Receive second player card
            data = self.socket.recv(8)
            if len(data) < 8:
                raise ValueError("Incomplete card payload")
            rank, suit = decode_payload_card(data[5:8])
            player_cards.append(Card(rank, suit))
            
            # Receive dealer's first card
            data = self.socket.recv(8)
            if len(data) < 8:
                raise ValueError("Incomplete card payload")
            rank, suit = decode_payload_card(data[5:8])
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
        
        Format: magic cookie (4) + type (1) + data (3)
        - Card: type=0x4, rank (1) + suit (1) + pad (1)
        - Result: type=0x5, result_code (1) + pad (2)
        
        To distinguish: cards have valid ranks 1-13, results are 0x1/0x2/0x3
        
        Returns:
            dict: {type: "card"|"result", card: Card or code: int}
                  or None if error
        """
        try:
            # Read full 8-byte payload
            data = self.socket.recv(8)
            if len(data) < 8:
                raise ValueError("Incomplete payload")
            
            # Verify magic cookie and type
            magic = struct.unpack('!I', data[0:4])[0]
            msg_type = data[4]
            
            if magic != 0xabcddcba:
                raise ValueError(f"Invalid magic cookie: {hex(magic)}")
            if msg_type not in [0x4, 0x5]:
                raise ValueError(f"Invalid message type: {msg_type}")
            
            # Extract payload data (last 3 bytes)
            payload = data[5:8]
            
            # Distinguish based on message type, not rank value
            if msg_type == 0x4:
                # Card message (type 0x4): rank (1-13) + suit (0-3) + pad (0)
                rank = payload[0]
                suit = payload[1]
                return {
                    'type': 'card',
                    'card': Card(rank, suit)
                }
            else:  # msg_type == 0x5
                # Result message (type 0x5): result_code (0x1/0x2/0x3) + pad (0) + pad (0)
                result_code = payload[0]
                
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
            
            dealer_cards = [dealer_card]  # Track dealer's cards
            
            # Player turn loop
            while True:
                decision = game_handler.get_player_decision()
                
                if not self.send_decision(decision):
                    game_handler.show_error("Failed to send decision")
                    return False
                
                # Receive server response (could be card, cards, or result)
                game_result = None
                player_busted = False
                
                while True:
                    response = self.receive_server_response()
                    if response is None:
                        game_handler.show_error("Failed to receive server response")
                        return False
                    
                    if response['type'] == 'card':
                        card = response['card']
                        
                        if decision.lower() == 'hit':
                            # Hit: receive one card
                            player_cards.append(card)
                            game_handler.show_card(card, is_player=True)
                            
                            # Check if we bust after hitting
                            hand_value = sum(c.value() for c in player_cards)
                            aces = sum(1 for c in player_cards if c.rank == 1)
                            while hand_value > 21 and aces > 0:
                                hand_value -= 10
                                aces -= 1
                            
                            if hand_value > 21:
                                game_handler.show_bust(is_player=True)
                                # Player busted - server will send result code next
                                player_busted = True
                                # Continue reading to get result code
                                continue
                            else:
                                # Hit but no bust - back to decision loop
                                break
                        else:
                            # Stand: receive dealer cards until result
                            dealer_cards.append(card)
                            game_handler.show_card(card, is_player=False)
                            # Keep reading more responses
                            continue
                    
                    elif response['type'] == 'result':
                        # Game over - received result code
                        game_result = response['code']
                        game_handler.show_result(game_result, player_cards, dealer_cards)
                        break  # Exit response loop
                
                # If we got a result (bust or stand complete), round is over
                if game_result is not None:
                    break  # Exit decision loop to next round
        
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
