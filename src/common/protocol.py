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
    Encode card data for a payload message (5 bytes).
    
    Card format:
    - Bytes 0-1: Rank (1-13) encoded as big-endian unsigned short
    - Byte 2: Suit (0-3) encoded as single byte
    
    Why 2 bytes for rank when 1 byte would fit?
    The spec says "rank encoded 01-13 in first 2 bytes" - unclear why 2 bytes needed
    for values 1-13, but we follow spec exactly. Better to be over-specified than
    incompatible with another team's implementation.
    
    Args:
        rank (int): Card rank (1-13)
        suit (int): Card suit (0-3)
    
    Returns:
        bytes: 3-byte card encoding (2 bytes rank + 1 byte suit)
    """
    return struct.pack('!HB', rank, suit)


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
    
    rank, suit = struct.unpack('!HB', data[:3])
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
    


def decode_request(data):
    """
    Decode a TCP request message.
    
    Args:
        data (bytes): Raw message data
    
    Returns:
        tuple: (num_rounds, team_name) or None if invalid
    
    Raises:
        ValueError: If message format is invalid
    """
    if len(data) < 6:
        raise ValueError("Request message too short")
    
    magic, msg_type, num_rounds = struct.unpack('!IBB', data[:6])
    
    if magic != MAGIC_COOKIE:
        raise ValueError(f"Invalid magic cookie: {hex(magic)}")
    if msg_type != MSG_TYPE_REQUEST:
        raise ValueError(f"Wrong message type: {msg_type}")
    
    team_name = data[6:6 + TEAM_NAME_LENGTH].rstrip(b'\x00').decode('utf-8', errors='ignore')
    
    return num_rounds, team_name


def encode_payload_card(card_rank, card_suit):
    """
    Encode a payload message with a card (both client→server and server→client).
    
    Format:
    - Magic cookie (4 bytes): 0xabcddcba
    - Message type (1 byte): 0x4
    - Card rank (2 bytes): 1-13
    - Card suit (1 byte): 0-3 (HDCS: Hearts, Diamonds, Clubs, Spades)
    
    Args:
        card_rank (int): 1-13
        card_suit (int): 0-3
    
    Returns:
        bytes: Encoded message
    """
    return struct.pack('!IBHB', MAGIC_COOKIE, MSG_TYPE_PAYLOAD, card_rank, card_suit)


def encode_payload_result(result_code):
    """
    Encode a payload message with a round result (server→client only).
    
    Format:
    - Magic cookie (4 bytes): 0xabcddcba
    - Message type (1 byte): 0x4
    - Result (1 byte): 0x0=not over, 0x1=tie, 0x2=loss, 0x3=win
    - Padding (2 bytes): 0x00
    
    Args:
        result_code (int): 0x0, 0x1, 0x2, or 0x3
    
    Returns:
        bytes: Encoded message
    """
    return struct.pack('!IBBBH', MAGIC_COOKIE, MSG_TYPE_PAYLOAD, result_code, 0, 0)


def encode_payload_decision(decision):
    """
    Encode a payload message with player decision (client→server only).
    
    Format:
    - Magic cookie (4 bytes): 0xabcddcba
    - Message type (1 byte): 0x4
    - Decision (5 bytes): "Hittt" or "Stand" (fixed length, null-padded)
    
    Args:
        decision (str): "Hit" or "Stand"
    
    Returns:
        bytes: Encoded message
    
    Raises:
        ValueError: If decision is not valid
    """
    if decision.lower() not in ("hit", "stand"):
        raise ValueError(f"Invalid decision: {decision}")
    
    # Pad decision to 5 bytes
    if decision.lower() == "hit":
        decision_bytes = b"Hittt"
    else:
        decision_bytes = b"Stand"
    
    return struct.pack('!IB', MAGIC_COOKIE, MSG_TYPE_PAYLOAD) + decision_bytes


def decode_payload(data):
    """
    Decode a payload message. Type depends on context (card, result, or decision).
    
    Args:
        data (bytes): Raw message data (at least 5 bytes)
    
    Returns:
        dict: Payload information with keys depending on type
        - If card: {'type': 'card', 'rank': int, 'suit': int}
        - If result: {'type': 'result', 'code': int}
        - If decision: {'type': 'decision', 'text': str}
    
    Raises:
        ValueError: If message format is invalid
    """
    if len(data) < 5:
        raise ValueError("Payload message too short")
    
    magic, msg_type = struct.unpack('!IB', data[:5])
    
    if magic != MAGIC_COOKIE:
        raise ValueError(f"Invalid magic cookie: {hex(magic)}")
    if msg_type != MSG_TYPE_PAYLOAD:
        raise ValueError(f"Wrong message type: {msg_type}")
    
    # Determine payload type by inspecting the content
    if len(data) >= 8:
        # Could be card (rank + suit) or decision (5-byte string)
        try:
            rank, suit = struct.unpack('!HB', data[5:8])
            if 1 <= rank <= 13 and 0 <= suit <= 3:
                return {'type': 'card', 'rank': rank, 'suit': suit}
        except:
            pass
    
    # Check for decision string (5 bytes after header)
    if len(data) >= 10:
        decision_bytes = data[5:10]
        decision_str = decision_bytes.decode('utf-8', errors='ignore').rstrip('\x00')
        if decision_str.lower() in ("hit", "hittt", "stand"):
            return {'type': 'decision', 'text': decision_str}
    
    # Check for result code (1 byte after header)
    if len(data) >= 6:
        result_code = struct.unpack('!B', data[5:6])[0]
        if result_code in (0x0, 0x1, 0x2, 0x3):
            return {'type': 'result', 'code': result_code}
    
    raise ValueError("Cannot determine payload type")
