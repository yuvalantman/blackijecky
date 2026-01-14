"""
Protocol message encoding/decoding for the Blackjack network protocol.

Offer (UDP): 39 bytes
  cookie(4) + type(1=0x2) + tcp_port(2) + server_name(32)

Request (TCP): 38 bytes
  cookie(4) + type(1=0x3) + num_rounds(1) + team_name(32)

Payload helpers:
  decision: 5 bytes ("Hittt" or "Stand")
  result:   1 byte (0x0/0x1/0x2/0x3)
  card:     3 bytes rank(2) + suit(1)
"""

import struct
from config import (
    MAGIC_COOKIE,
    MSG_TYPE_OFFER,
    MSG_TYPE_REQUEST,
    TEAM_NAME_LENGTH,
)

# -------------------------
# Offer (UDP)
# -------------------------
def encode_offer(tcp_port: int, server_name: str) -> bytes:
    name_bytes = server_name.encode("utf-8")[:TEAM_NAME_LENGTH]
    name_bytes = name_bytes + b"\x00" * (TEAM_NAME_LENGTH - len(name_bytes))
    return struct.pack("!IBH", MAGIC_COOKIE, MSG_TYPE_OFFER, tcp_port) + name_bytes


def decode_offer(data: bytes) -> tuple[int, str]:
    if len(data) < 39:
        raise ValueError(f"Offer message too short: got {len(data)} bytes, need 39")

    try:
        magic, msg_type, tcp_port = struct.unpack("!IBH", data[:7])
    except struct.error as e:
        raise ValueError(f"Failed to parse offer header: {e}")

    if magic != MAGIC_COOKIE:
        raise ValueError(f"Invalid magic cookie: got {hex(magic)}, expected {hex(MAGIC_COOKIE)}")
    if msg_type != MSG_TYPE_OFFER:
        raise ValueError(f"Wrong message type: got {msg_type}, expected {MSG_TYPE_OFFER}")

    server_name = data[7:7 + TEAM_NAME_LENGTH].rstrip(b"\x00").decode("utf-8", errors="ignore")
    return tcp_port, server_name


# -------------------------
# Request (TCP)
# -------------------------
def encode_request(num_rounds: int, team_name: str) -> bytes:
    name_bytes = team_name.encode("utf-8")[:TEAM_NAME_LENGTH]
    name_bytes = name_bytes + b"\x00" * (TEAM_NAME_LENGTH - len(name_bytes))
    return struct.pack("!IBB", MAGIC_COOKIE, MSG_TYPE_REQUEST, num_rounds) + name_bytes


def decode_request(data: bytes) -> tuple[int, str]:
    if len(data) < 38:
        raise ValueError(f"Request message too short: got {len(data)} bytes, need 38")

    try:
        magic, msg_type, num_rounds = struct.unpack("!IBB", data[:6])
    except struct.error as e:
        raise ValueError(f"Failed to parse request header: {e}")

    if magic != MAGIC_COOKIE:
        raise ValueError(f"Invalid magic cookie: got {hex(magic)}")
    if msg_type != MSG_TYPE_REQUEST:
        raise ValueError(f"Wrong message type: got {msg_type}, expected {MSG_TYPE_REQUEST}")

    team_name = data[6:6 + TEAM_NAME_LENGTH].rstrip(b"\x00").decode("utf-8", errors="ignore")
    return num_rounds, team_name


# -------------------------
# Payload field helpers
# -------------------------
def encode_payload_card(rank: int, suit: int) -> bytes:
    """
    Card is exactly 3 bytes:
      rank: 2 bytes big-endian (01-13)
      suit: 1 byte (0-3)
    """
    return struct.pack("!HB", rank, suit)


def decode_payload_card(data: bytes) -> tuple[int, int]:
    if len(data) < 3:
        raise ValueError(f"Card data too short: got {len(data)} bytes, need 3")
    rank, suit = struct.unpack("!HB", data[:3])
    return rank, suit


def encode_payload_player_decision(decision: str) -> bytes:
    """
    Decision is exactly 5 bytes: b"Hittt" or b"Stand"
    """
    d = decision.lower().strip()
    if d == "hit":
        return b"Hittt"
    if d == "stand":
        return b"Stand"
    raise ValueError(f"Invalid decision: '{decision}'. Must be 'hit' or 'stand'")


def decode_payload_player_decision(data: bytes) -> str:
    if len(data) < 5:
        raise ValueError(f"Decision data too short: got {len(data)} bytes, need 5")

    decision_bytes = data[:5]
    if decision_bytes == b"Hittt":
        return "hit"
    if decision_bytes == b"Stand":
        return "stand"
    raise ValueError(f"Invalid decision in payload: {decision_bytes!r}")


def encode_payload_result(result_code: int) -> bytes:
    """
    Result is 1 byte:
      0x0 not over, 0x1 tie, 0x2 loss, 0x3 win
    """
    return struct.pack("!B", result_code)


def decode_payload_result(data: bytes) -> int:
    if len(data) < 1:
        raise ValueError("Result data missing")
    return struct.unpack("!B", data[:1])[0]

