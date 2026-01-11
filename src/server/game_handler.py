"""
Handles one client's entire game session (all their rounds).

Flow:
1. Receive request (how many rounds, client's team name)
2. For each round:
   - Create fresh deck
   - Deal cards
   - Player turn (Hit/Stand loop)
   - Dealer turn (auto-play until >= 17)
   - Determine winner
   - Send result to client
3. Close connection

This runs in its own thread so multiple clients can play simultaneously.
"""

import struct
from src.common.protocol import (
    decode_request, encode_payload_card, encode_payload_result,
    decode_payload_player_decision
)
from src.common.deck import Deck
from src.common.game_logic import (
    calculate_hand_value, is_bust, dealer_decision, determine_winner
)
from config import RESULT_WIN, RESULT_LOSS, RESULT_TIE, SOCKET_TIMEOUT


class GameHandler:
    def __init__(self, client_socket, client_address):
        """
        Initialize handler for one client connection.
        
        Args:
            client_socket: Connected TCP socket
            client_address: (IP, port) tuple
        """
        self.socket = client_socket
        self.address = client_address
        self.num_rounds = 0
        self.team_name = ""
        self.wins = 0
        self.losses = 0
        self.ties = 0
    
    def handle_game(self):
        """
        Main game loop for this client.
        Handles all their rounds, then closes connection.
        """
        try:
            self.socket.settimeout(SOCKET_TIMEOUT)
            
            # Step 1: Receive request message (num_rounds, team_name)
            request_data = self.socket.recv(38)  # Request is 38 bytes
            if not request_data:
                print(f"Client {self.address} disconnected before sending request")
                return
            
            self.num_rounds, self.team_name = decode_request(request_data)
            print(f"Client {self.team_name} from {self.address} wants {self.num_rounds} rounds")
            
            # Step 2: Play each round
            for round_num in range(1, self.num_rounds + 1):
                self._play_round(round_num)
            
            # Step 3: Print final stats
            win_rate = (self.wins / self.num_rounds * 100) if self.num_rounds > 0 else 0
            print(f"Client {self.team_name}: {self.wins}W {self.losses}L {self.ties}T (rate: {win_rate:.1f}%)")
            
        except struct.error as e:
            print(f"Protocol error from {self.address}: {e}")
        except Exception as e:
            print(f"Error handling client {self.address}: {e}")
        
        finally:
            try:
                self.socket.close()
            except:
                pass
    
    def _play_round(self, round_num):
        """
        Play one round of blackjack.
        
        Args:
            round_num: Round number (for logging)
        """
        # Create fresh deck for this round
        deck = Deck()
        
        # Deal initial cards: player gets 2, dealer gets 2
        player_hand = [deck.draw(), deck.draw()]
        dealer_hand = [deck.draw(), deck.draw()]
        
        # Send initial cards to player
        # Format: player's two cards (no dealer's second card yet - it's hidden)
        self._send_card(player_hand[0])
        self._send_card(player_hand[1])
        self._send_card(dealer_hand[0])  # Only first dealer card is visible
        
        # PLAYER TURN: Hit or Stand loop
        while True:
            player_value = calculate_hand_value(player_hand)
            
            # Ask for decision
            decision = self._get_player_decision()
            
            if decision == "hit":
                new_card = deck.draw()
                player_hand.append(new_card)
                self._send_card(new_card)
                
                # Check for bust
                if is_bust(calculate_hand_value(player_hand)):
                    # Player busts, they lose immediately
                    self._send_result(RESULT_LOSS)
                    self.losses += 1
                    return
            
            elif decision == "stand":
                break
        
        # DEALER TURN: Dealer plays automatically
        # First, reveal the hidden card to player
        self._send_card(dealer_hand[1])
        
        # Dealer hits/stands automatically until >= 17
        dealer_value = calculate_hand_value(dealer_hand)
        while dealer_value < 17:
            new_card = deck.draw()
            dealer_hand.append(new_card)
            self._send_card(new_card)
            dealer_value = calculate_hand_value(dealer_hand)
        
        # DETERMINE WINNER
        player_value = calculate_hand_value(player_hand)
        dealer_value = calculate_hand_value(dealer_hand)
        player_busted = is_bust(player_value)
        dealer_busted = is_bust(dealer_value)
        
        result = determine_winner(player_value, dealer_value, player_busted, dealer_busted)
        
        # Send result code to client
        if result == "win":
            self._send_result(RESULT_WIN)
            self.wins += 1
        elif result == "loss":
            self._send_result(RESULT_LOSS)
            self.losses += 1
        else:  # tie
            self._send_result(RESULT_TIE)
            self.ties += 1
    
    def _send_card(self, card):
        """
        Send a card to the client as a payload message.
        
        Format: magic cookie (4) + type 0x4 (1) + card_rank (2) + card_suit (1) = 8 bytes
        """
        card_data = encode_payload_card(card.rank, card.suit)
        # Construct full payload: magic cookie + type + card
        payload = struct.pack('!IB', 0xabcddcba, 0x4) + card_data
        self.socket.sendall(payload)
    
    def _get_player_decision(self):
        """
        Wait for player to send Hit or Stand decision.
        
        Expected format: 5 bytes ("Hittt" or "Stand")
        """
        decision_data = self.socket.recv(5)
        if not decision_data:
            raise ConnectionError("Client disconnected during game")
        
        return decode_payload_player_decision(decision_data)
    
    def _send_result(self, result_code):
        """
        Send round result to client.
        
        Args:
            result_code: 0x1=tie, 0x2=loss, 0x3=win
        """
        result_msg = encode_payload_result(result_code)
        # Construct full payload: magic cookie + type + result
        payload = struct.pack('!IB', 0xabcddcba, 0x4) + result_msg
        self.socket.sendall(payload)
