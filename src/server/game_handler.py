"""
Handles one client's entire game session (all their rounds) - SPEC COMPLIANT.

Spec reminders:
- Request (TCP): 38 bytes = cookie(4) + type(1=0x3) + rounds(1) + team_name(32)
- Payload (TCP): 14 bytes = cookie(4) + type(1=0x4) + decision(5) + result(1) + card(3)
  decision: b"Hittt" or b"Stand"
  result: 0x0 not over, 0x1 tie, 0x2 loss, 0x3 win
  card: rank(2 bytes) + suit(1 byte)

IMPORTANT:
This server implementation assumes your src/common/protocol.py was fixed so that:
- encode_payload_card(rank, suit) returns 3 bytes as struct.pack('!HB', rank, suit)
- decode_payload_card(data) parses struct.unpack('!HB', data[:3])
"""

import struct
from src.common.protocol import (
    decode_request,
    encode_payload_card,
    decode_payload_player_decision,
)
from src.common.deck import Deck
from src.common.game_logic import (
    calculate_hand_value,
    is_bust,
    determine_winner,
)
from config import (
    MAGIC_COOKIE,
    MSG_TYPE_PAYLOAD,
    RESULT_WIN,
    RESULT_LOSS,
    RESULT_TIE,
    SOCKET_TIMEOUT,
)


# Payload layout offsets (14 bytes total)
PAYLOAD_LEN = 14
DECISION_SLICE = slice(5, 10)   # 5 bytes
RESULT_OFFSET = 10              # 1 byte
CARD_SLICE = slice(11, 14)      # 3 bytes


class GameHandler:
    def __init__(self, client_socket, client_address):
        self.socket = client_socket
        self.address = client_address
        self.num_rounds = 0
        self.team_name = ""
        self.wins = 0
        self.losses = 0
        self.ties = 0

    # ----------------- TCP helpers -----------------
    def _recv_exact(self, n: int) -> bytes:
        """Read exactly n bytes from TCP (or raise if connection closes)."""
        chunks = []
        remaining = n
        while remaining > 0:
            chunk = self.socket.recv(remaining)
            if not chunk:
                raise ConnectionError("Client disconnected")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def _read_payload(self) -> bytes:
        """Read exactly one payload message (14 bytes) and validate header."""
        data = self._recv_exact(PAYLOAD_LEN)
        magic = struct.unpack("!I", data[0:4])[0]
        msg_type = data[4]
        if magic != MAGIC_COOKIE:
            raise ValueError(f"Invalid magic cookie: got {hex(magic)}")
        if msg_type != MSG_TYPE_PAYLOAD:
            raise ValueError(f"Invalid message type: got {msg_type}, expected {MSG_TYPE_PAYLOAD}")
        return data

    def _build_payload(self, decision5: bytes, result_code: int, card_rank: int, card_suit: int) -> bytes:
        """
        Build a spec payload (14 bytes):
        cookie + type + decision(5) + result(1) + card(3)
        """
        if len(decision5) != 5:
            raise ValueError("decision5 must be exactly 5 bytes")
        card_bytes = encode_payload_card(card_rank, card_suit)  # must be 3 bytes
        if len(card_bytes) != 3:
            raise ValueError("encode_payload_card must return exactly 3 bytes")
        return struct.pack("!IB", MAGIC_COOKIE, MSG_TYPE_PAYLOAD) + decision5 + struct.pack("!B", result_code) + card_bytes

    # ----------------- protocol actions -----------------
    def _get_player_decision(self) -> str:
        """
        Receive a full payload (14 bytes) from client and extract decision field.
        Returns: "hit" or "stand"
        """
        data = self._read_payload()
        decision_bytes = data[DECISION_SLICE]
        return decode_payload_player_decision(decision_bytes)

    def _send_card_update(self, card):
        """
        Send a payload that represents "round not over" with a card update.
        decision field is irrelevant server->client, so we fill with 5 null bytes.
        """
        payload = self._build_payload(decision5=b"\x00" * 5, result_code=0x0, card_rank=card.rank, card_suit=card.suit)
        self.socket.sendall(payload)

    def _send_round_result(self, result_code: int):
        """
        Send a payload that ends the round (result_code != 0x0).
        Card field must still exist; we send a neutral 0/0.
        (Alternative is sending last card again; neutral is simplest & consistent.)
        """
        payload = self._build_payload(decision5=b"\x00" * 5, result_code=result_code, card_rank=0, card_suit=0)
        self.socket.sendall(payload)

    # ----------------- main loop -----------------
    def handle_game(self):
        try:
            self.socket.settimeout(SOCKET_TIMEOUT)

            # Step 1: Receive request message (38 bytes) reliably
            request_data = self._recv_exact(38)
            self.num_rounds, self.team_name = decode_request(request_data)

            print(f"Client {self.team_name} from {self.address} wants {self.num_rounds} rounds")

            # Step 2: Play rounds
            for round_num in range(1, self.num_rounds + 1):
                self._play_round(round_num)

            # Step 3: Print final stats
            win_rate = (self.wins / self.num_rounds * 100) if self.num_rounds > 0 else 0.0
            print(f"Client {self.team_name}: {self.wins}W {self.losses}L {self.ties}T (rate: {win_rate:.1f}%)")

        except (ConnectionError, TimeoutError) as e:
            print(f"Client {self.address} disconnected/timeout: {e}")
        except struct.error as e:
            print(f"Protocol struct error from {self.address}: {e}")
        except Exception as e:
            print(f"Error handling client {self.address}: {e}")
        finally:
            try:
                self.socket.close()
            except Exception:
                pass

    def _play_round(self, round_num: int):
        # Fresh deck per round
        deck = Deck()

        # Deal initial hands
        player_hand = [deck.draw(), deck.draw()]
        dealer_hand = [deck.draw(), deck.draw()]

        # Send initial visible cards: player(2) + dealer_up(1)
        self._send_card_update(player_hand[0])
        self._send_card_update(player_hand[1])
        self._send_card_update(dealer_hand[0])

        # PLAYER TURN
        while True:
            decision = self._get_player_decision()

            if decision == "hit":
                new_card = deck.draw()
                player_hand.append(new_card)
                self._send_card_update(new_card)

                if is_bust(calculate_hand_value(player_hand)):
                    # Player bust -> immediate loss
                    self._send_round_result(RESULT_LOSS)
                    self.losses += 1
                    return

                # else: player continues (client will send another decision)
                continue

            elif decision == "stand":
                break

            else:
                # Should never happen if decode is strict
                raise ValueError(f"Invalid decision from client: {decision}")

        # DEALER TURN
        # Reveal dealer's hidden card first
        self._send_card_update(dealer_hand[1])

        while calculate_hand_value(dealer_hand) < 17:
            new_card = deck.draw()
            dealer_hand.append(new_card)
            self._send_card_update(new_card)

        # Determine winner
        player_value = calculate_hand_value(player_hand)
        dealer_value = calculate_hand_value(dealer_hand)

        player_busted = is_bust(player_value)
        dealer_busted = is_bust(dealer_value)

        result = determine_winner(player_value, dealer_value, player_busted, dealer_busted)

        # Send final result
        if result == "win":
            self._send_round_result(RESULT_WIN)
            self.wins += 1
        elif result == "loss":
            self._send_round_result(RESULT_LOSS)
            self.losses += 1
        else:
            self._send_round_result(RESULT_TIE)
            self.ties += 1
