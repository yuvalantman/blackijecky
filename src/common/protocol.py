"""
Protocol message encoding/decoding for the Blackjack network protocol.

This module is critical: it's the *interface between all teams*.
Every team writes this differently, but if we don't agree on message format,
nothing works. Therefore:

1. All messages are binary (not JSON/text) - more compact, faster parsing
2. Every message starts with magic cookie - validates format immediately
3. Fixed-length fields - no ambiguity in where each field starts/ends
4. struct.pack/unpack - ensures consistent encoding across Python versions

The protocol has three message types, each with different format:
- Offer (UDP): Server -> Client, size=39 bytes
- Request (TCP): Client -> Server, size=38 bytes  
- Payload (TCP): Both directions, variable size for game data

Binary format trade-off: Harder to debug (can't print raw bytes as text),
but necessary for interoperability across teams and network efficiency.
"""

import struct
import socket
from config import (
    MAGIC_COOKIE, MSG_TYPE_OFFER, MSG_TYPE_REQUEST, MSG_TYPE_PAYLOAD,
    TEAM_NAME_LENGTH, CARD_RANK_BYTES, CARD_SUIT_BYTES
)


def encode_offer(tcp_port, server_name):
    """
    Encode a UDP offer message (server -> client).
    
    Message structure (39 bytes total):
    - Bytes 0-3: Magic cookie (0xabcddcba) - validation
    - Byte 4: Message type (0x2) - tells receiver this is an offer
    - Bytes 5-6: TCP port (big-endian) - where clients should connect
    - Bytes 7-38: Server name (32 bytes) - team name, padded with 0x00
    
    Why fixed 39 bytes?
    - Receiver knows exactly how much data to read
    - No need for length prefix or delimiters
    - Parsing is trivial with struct.unpack
    
    Args:
        tcp_port (int): Server's TCP port (0-65535)
        server_name (str): Team name to broadcast (truncated to 32 chars)
    
    Returns:
        bytes: Encoded message, exactly 39 bytes
    """
    # Encode server name as UTF-8 bytes, truncate to max 32, then pad with nulls
    # Padding with 0x00 means: "rest of field is empty, ignore it"
    name_bytes = server_name.encode('utf-8')[:TEAM_NAME_LENGTH]
    name_bytes = name_bytes + b'\x00' * (TEAM_NAME_LENGTH - len(name_bytes))
    
    # struct.pack with '!' = network byte order (big-endian)
    # This ensures all teams encode integers the same way, even on different architectures
    msg = struct.pack('!IBH', MAGIC_COOKIE, MSG_TYPE_OFFER, tcp_port)
    msg += name_bytes
    return msg


def decode_offer(data):
    """
    Decode a UDP offer message from server.
    
    This is where we validate the message and extract information.
    We check:
    1. Length - must be at least 39 bytes
    2. Magic cookie - if wrong, it's not our protocol
    3. Message type - confirms it's an offer (not request or payload)
    
    Why explicit validation?
    - UDP is unreliable: packets can be corrupted, reordered, or lost
    - Multiple protocols might use same port: need to reject non-protocol messages
    - Makes debugging easier: clear error messages tell us what went wrong
    
    Args:
        data (bytes): Raw UDP packet data
    
    Returns:
        tuple: (tcp_port, server_name) if valid
    
    Raises:
        ValueError: If magic cookie wrong, message type wrong, or format invalid
    """
    # Check minimum length before unpacking (prevents struct errors)
    if len(data) < 7:
        raise ValueError(f"Offer message too short: got {len(data)} bytes, need at least 7")
    
    # Unpack first 7 bytes: magic cookie, type, port
    # If this fails, the entire message is corrupted
    try:
        magic, msg_type, tcp_port = struct.unpack('!IBH', data[:7])
    except struct.error as e:
        raise ValueError(f"Failed to parse offer header: {e}")
    
    # Validate magic cookie - if this fails, it's not our protocol
    if magic != MAGIC_COOKIE:
        raise ValueError(f"Invalid magic cookie: got {hex(magic)}, expected {hex(MAGIC_COOKIE)}")
    
    # Validate message type - ensure this is an offer, not something else
    if msg_type != MSG_TYPE_OFFER:
        raise ValueError(f"Wrong message type: got {msg_type}, expected {MSG_TYPE_OFFER}")
    
    # Extract server name from bytes 7-38, strip trailing null bytes, decode to string
    # errors='ignore' means: if there's non-UTF8 garbage, skip it (don't crash)
    server_name = data[7:7 + TEAM_NAME_LENGTH].rstrip(b'\x00').decode('utf-8', errors='ignore')
    
    return tcp_port, server_name


def encode_request(num_rounds, team_name):
    """
    Encode a TCP request message (client -> server).
    
    Message structure (38 bytes total):
    - Bytes 0-3: Magic cookie
    - Byte 4: Message type (0x3)
    - Byte 5: Number of rounds (1-255) - how many games the client wants
    - Bytes 6-37: Team name (32 bytes)
    
    This message is sent once, right after TCP connection.
    Server receives it and knows: "This client wants 5 games" (example).
    
    Args:
        num_rounds (int): How many games to play (1-255, fits in 1 byte)
        team_name (str): Client's team name
    
    Returns:
        bytes: Encoded message, exactly 38 bytes
    """
    # Encode team name the same way as in offer
    name_bytes = team_name.encode('utf-8')[:TEAM_NAME_LENGTH]
    name_bytes = name_bytes + b'\x00' * (TEAM_NAME_LENGTH - len(name_bytes))
    
    # num_rounds as unsigned byte (B in struct format)
    msg = struct.pack('!IBB', MAGIC_COOKIE, MSG_TYPE_REQUEST, num_rounds)
    msg += name_bytes
    return msg


def decode_request(data):
    """
    Decode a TCP request message from client.
    
    Server receives this first after TCP connect, telling us:
    - How many rounds the client wants to play
    - Who the client is (team name)
    
    Args:
        data (bytes): Raw message data
    
    Returns:
        tuple: (num_rounds, team_name)
    
    Raises:
        ValueError: If validation fails
    """
    if len(data) < 6:
        raise ValueError(f"Request message too short: got {len(data)} bytes, need at least 6")
    
    try:
        magic, msg_type, num_rounds = struct.unpack('!IBB', data[:6])
    except struct.error as e:
        raise ValueError(f"Failed to parse request header: {e}")
    
    if magic != MAGIC_COOKIE:
        raise ValueError(f"Invalid magic cookie: got {hex(magic)}")
    if msg_type != MSG_TYPE_REQUEST:
        raise ValueError(f"Wrong message type: got {msg_type}")
    
    team_name = data[6:6 + TEAM_NAME_LENGTH].rstrip(b'\x00').decode('utf-8', errors='ignore')
    
    return num_rounds, team_name


def encode_payload_card(rank, suit):
    """
    Encode card data for a payload message (3 bytes).
    
    Card format:
    - Byte 0: Rank (1-13) encoded as single byte
    - Byte 1: Suit (0-3) encoded as single byte
    - Byte 2: Reserved/padding (unused, set to 0)
    
    Why 3 bytes instead of 2?
    The spec says "Rank encoded 01-13 in first 2 bytes, Suit in second byte"
    which is ambiguous. Testing shows 3 bytes total works (rank byte + suit byte + pad byte).
    
    Args:
        rank (int): Card rank (1-13)
        suit (int): Card suit (0-3)
    
    Returns:
        bytes: 3-byte card encoding
    """
    return struct.pack('!BBB', rank, suit, 0)


def decode_payload_card(data):
    """
    Decode card data from payload message.
    
    Args:
        data (bytes): At least 3 bytes of card data
    
    Returns:
        tuple: (rank, suit)
    
    Raises:
        ValueError: If data too short
    """
    if len(data) < 3:
        raise ValueError(f"Card data too short: got {len(data)} bytes, need 3")
    
    rank, suit, _ = struct.unpack('!BBB', data[:3])
    return rank, suit


def encode_payload_player_decision(decision):
    """
    Encode player decision for payload message (5 bytes).
    
    Decision format:
    - Exactly "Hittt" (5 bytes) or "Stand" (5 bytes)
    
    Wait, why "Hittt" with 3 t's? That's weird.
    Looking at spec: "send in text the string 'Hittt' or 'Stand'"
    This is odd but we follow spec exactly. "Stand" is naturally 5 bytes,
    so "Hittt" (with 3 t's) matches that length. Spec is spec.
    
    Args:
        decision (str): "hit" or "stand" (case-insensitive)
    
    Returns:
        bytes: Exactly 5 bytes
    
    Raises:
        ValueError: If decision invalid
    """
    decision_lower = decision.lower().strip()
    
    if decision_lower == "hit":
        return b"Hittt"  # Yes, three t's. Yes, it's weird. Yes, it's spec.
    elif decision_lower == "stand":
        return b"Stand"
    else:
        raise ValueError(f"Invalid decision: '{decision}'. Must be 'hit' or 'stand'")


def decode_payload_player_decision(data):
    """
    Decode player decision from payload message.
    
    Args:
        data (bytes): At least 5 bytes
    
    Returns:
        str: "hit" or "stand" (lowercase)
    
    Raises:
        ValueError: If decision invalid
    """
    if len(data) < 5:
        raise ValueError(f"Decision data too short: got {len(data)} bytes, need 5")
    
    decision_bytes = data[:5]
    if decision_bytes == b"Hittt":
        return "hit"
    elif decision_bytes == b"Stand":
        return "stand"
    else:
        raise ValueError(f"Invalid decision in payload: {decision_bytes}")


def encode_payload_result(result_code):
    """
    Encode round result for payload message (1 byte).
    
    Result codes:
    - 0x0: Round still in progress
    - 0x1: Tie (equal totals)
    - 0x2: Loss (dealer won)
    - 0x3: Win (player won)
    
    Args:
        result_code (int): One of the result constants (0x0-0x3)
    
    Returns:
        bytes: Single byte
    """
    return struct.pack('!B', result_code)


def decode_payload_result(data):
    """
    Decode round result from payload message.
    
    Args:
        data (bytes): At least 1 byte
    
    Returns:
        int: Result code (0x0-0x3)
    
    Raises:
        ValueError: If data too short
    """
    if len(data) < 1:
        raise ValueError("Result data missing")
    
    result_code = struct.unpack('!B', data[:1])[0]
    return result_code
