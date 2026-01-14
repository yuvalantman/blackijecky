"""
TCP communication with server during gameplay (SPEC-COMPLIANT).

Key protocol facts (from hackathon spec):
- Request: cookie(4) + type(1=0x3) + rounds(1) + team_name(32) = 38 bytes
- Payload: cookie(4) + type(1=0x4) + decision(5) + result(1) + card(3) = 14 bytes
  decision: b"Hittt" or b"Stand"
  result: 0x0 not over, 0x1 tie, 0x2 loss, 0x3 win
  card: rank(2 bytes) + suit(1 byte)
"""

import socket
import struct
from src.common.protocol import (
    encode_request,
    decode_payload_card,
    encode_payload_player_decision,
)
from src.common.card import Card
from config import SOCKET_TIMEOUT

MAGIC_COOKIE = 0xabcddcba
MSG_TYPE_PAYLOAD = 0x4

PAYLOAD_LEN = 14
CARD_SLICE = slice(11, 14)     # last 3 bytes in payload
RESULT_OFFSET = 10             # 1 byte
# decision slice is [5:10] but client doesn't need to parse it


class GameClient:
    def __init__(self, server_ip, server_port, team_name, num_rounds):
        self.server_ip = server_ip
        self.server_port = server_port
        self.team_name = team_name
        self.num_rounds = num_rounds
        self.socket = None
        self.wins = 0
        self.losses = 0
        self.ties = 0

    # ---------- TCP helpers ----------
    def _recv_exact(self, n: int) -> bytes:
        """
        Read exactly n bytes from the TCP stream (or raise if connection closes).
        TCP recv() can return fewer bytes than requested, so we loop until complete.
        """
        chunks = []
        remaining = n
        while remaining > 0:
            chunk = self.socket.recv(remaining)
            if not chunk:
                raise ConnectionError("Server closed connection unexpectedly")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    # ---------- connection ----------
    def connect(self) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(SOCKET_TIMEOUT)
            self.socket.connect((self.server_ip, self.server_port))
            print(f"Connected to server at {self.server_ip}:{self.server_port}")
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False

    def send_request(self) -> bool:
        try:
            msg = encode_request(self.num_rounds, self.team_name)
            self.socket.sendall(msg)
            return True
        except Exception as e:
            print(f"Failed to send request: {e}")
            return False

    # ---------- payload parsing ----------
    def _read_payload(self) -> tuple[int, Card]:
        """
        Read one SPEC payload (14 bytes) and return (result_code, Card).
        """
        data = self._recv_exact(PAYLOAD_LEN)

        magic = struct.unpack("!I", data[0:4])[0]
        msg_type = data[4]

        if magic != MAGIC_COOKIE:
            raise ValueError(f"Invalid magic cookie: {hex(magic)}")
        if msg_type != MSG_TYPE_PAYLOAD:
            raise ValueError(f"Invalid message type: {msg_type} (expected 0x4)")

        result_code = data[RESULT_OFFSET]
        rank, suit = decode_payload_card(data[CARD_SLICE])
        return result_code, Card(rank, suit)

    def _update_stats_if_finished(self, result_code: int) -> None:
        # 0x0 = not over, 0x1 tie, 0x2 loss, 0x3 win
        if result_code == 0x1:
            self.ties += 1
        elif result_code == 0x2:
            self.losses += 1
        elif result_code == 0x3:
            self.wins += 1

    # ---------- gameplay ----------
    def receive_cards(self):
        """
        Receive player's initial hand (2 cards) and dealer's first card.
        We read 3 payload messages and extract the card from each.
        """
        try:
            player_cards = []

            # card #1 (player)
            result, card = self._read_payload()
            player_cards.append(card)

            # card #2 (player)
            result, card = self._read_payload()
            player_cards.append(card)

            # dealer first card
            result, dealer_card = self._read_payload()

            return player_cards, dealer_card
        except Exception as e:
            print(f"Error receiving initial cards: {e}")
            return None, None

    def send_decision(self, decision: str) -> bool:
        """
        Send player's decision as a SPEC payload (14 bytes).
        encode_payload_player_decision() must build:
        cookie+type(0x4)+decision(5)+result(1 dummy)+card(3 dummy)
        """
        try:
            msg = encode_payload_player_decision(decision)
            self.socket.sendall(msg)
            return True
        except Exception as e:
            print(f"Failed to send decision: {e}")
            return False

    def play_game(self, game_handler) -> bool:
        if not self.connect():
            return False
        if not self.send_request():
            return False

        try:
            for round_num in range(1, self.num_rounds + 1):
                game_handler.show_round(round_num, self.num_rounds)

                # initial cards
                player_cards, dealer_card = self.receive_cards()
                if player_cards is None:
                    game_handler.show_error("Failed to receive initial cards")
                    return False

                game_handler.show_initial_cards(player_cards, dealer_card)
                dealer_cards = [dealer_card]

                # round loop until server says finished (result != 0x0)
                while True:
                    decision = game_handler.get_player_decision()
                    if not self.send_decision(decision):
                        game_handler.show_error("Failed to send decision")
                        return False

                    # After a decision, server may send multiple payloads:
                    # - cards (for hit: player card; for stand: dealer cards)
                    # - a final payload with result_code != 0x0
                    while True:
                        result_code, card = self._read_payload()

                        # If round not over, this payload contains a "card update"
                        if result_code == 0x0:
                            if decision.lower() == "hit":
                                player_cards.append(card)
                                game_handler.show_card(card, is_player=True)
                                # continue to read: server might immediately finish (bust) or wait for next decision
                                # We'll decide whether to stop reading now:
                                # In most flows: exactly one card for hit, then client chooses again.
                                break
                            else:
                                dealer_cards.append(card)
                                game_handler.show_card(card, is_player=False)
                                # dealer may draw multiple cards, so keep reading until result != 0x0
                                continue

                        # result_code != 0x0 means round finished
                        self._update_stats_if_finished(result_code)
                        game_handler.show_result(result_code, player_cards, dealer_cards)
                        break  # stop reading payloads for this round

                    # If round finished, exit to next round
                    if result_code != 0x0:
                        break

            return True

        except Exception as e:
            game_handler.show_error(f"Exception during gameplay: {e}")
            return False
        finally:
            self.close()

    def close(self):
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass

    def get_statistics(self):
        return {"wins": self.wins, "losses": self.losses, "ties": self.ties}

