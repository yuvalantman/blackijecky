"""
Central configuration for the Blackjack Server-Client application.
All constants defined here to avoid magic numbers scattered throughout code.
This single file is the source of truth for protocol format, network behavior, and game rules.
"""

# ============ PROTOCOL CONSTANTS ============
# Magic cookie: 0xabcddcba
# Every message in our protocol must start with this 4-byte value. It serves as a sanity check:
# if we receive data that doesn't start with this, we know it's either:
#   - Garbage data from the network
#   - A message from a different protocol/application
#   - Corrupted data
# This is cheap to check (one equality) and prevents misinterpreting bad data.
MAGIC_COOKIE = 0xabcddcba

# Message types: single byte identifies what kind of message this is.
# This matters because the payload format differs:
#   0x2 (offer): Server -> Client, announces availability
#   0x3 (request): Client -> Server, joins a game session
#   0x4 (payload): Both directions, game communication (cards, decisions)
#   0x5 (result): Server -> Client, round result
MSG_TYPE_OFFER = 0x2       
MSG_TYPE_REQUEST = 0x3     
MSG_TYPE_PAYLOAD = 0x4
MSG_TYPE_RESULT = 0x5

# Result codes in payload messages
# These tell the client what happened in a round.
# We send only these specific codes to avoid ambiguity across teams.
RESULT_ROUND_NOT_OVER = 0x0  # Still playing, more cards coming
RESULT_TIE = 0x1             # Equal totals
RESULT_LOSS = 0x2            # Player lost (dealer won)
RESULT_WIN = 0x3             # Player won

# ============ NETWORK CONSTANTS ============
# UDP port 13122: Hardcoded per specification.
# Every client is hard-wired to listen on this port. This is the "well-known" port for our service.
# If this changes, every team's code breaks (hence why it's in the spec).
OFFER_UDP_PORT = 13122

# Broadcast address: 255.255.255.255 reaches all devices on the local network.
# Why broadcast instead of multicast? Simpler, more compatible, works even if multicast is disabled.
# Drawback: generates network traffic everyone sees, but for a hackathon that's fine.
BROADCAST_ADDRESS = "255.255.255.255"

# Broadcast interval: 1 second per spec.
# Servers constantly announce their availability. If we go longer, clients take longer to discover us.
# If we go shorter, network gets flooded. 1 second is the specified trade-off.
OFFER_BROADCAST_INTERVAL = 1.0

# Socket timeout: 30 seconds.
# If a server doesn't respond to our TCP request within 30 seconds, assume it's dead/hung.
# This prevents clients from blocking forever if a server crashes mid-game.
# We set this high because during gameplay, a user might take several seconds deciding Hit/Stand.
# Individual network recv() calls will complete much faster, so 30s is really a max per message.
SOCKET_TIMEOUT = 30.0

# ============ MESSAGE FORMAT SIZES ============
# Fixed-length fields make messages predictable in size. This is critical for protocol design:
# - We can parse without having to read a length field first
# - We know exactly how many bytes to read before parsing next field
# - No ambiguity if names contain null bytes or special characters

# Magic cookie size: 4 bytes (0xabcddcba as uint32)
# Packed as big-endian unsigned integer. Fixed size ensures no parsing ambiguity.
MAGIC_COOKIE_BYTES = 4

# Message type: 1 byte (0x2, 0x3, or 0x4)
# Fits in a single byte. Easy to extract after magic cookie.
MESSAGE_TYPE_BYTES = 1

# TCP port number: 2 bytes (uint16)
# Fits in 2 bytes, supports ports 0-65535. Big-endian encoding in offers.
TCP_PORT_BYTES = 2

# Round counter: 1 byte (0-255)
# Max rounds = 255 per spec. Fits in a single byte. Allows up to 255 rounds per session.
ROUND_BYTES = 1

# Team name: 32 bytes, padded with 0x00 if shorter.
# Names longer than 32 are truncated. This is fixed-size because:
#   1. Predictable total message size (must multiply message size by many bytes over network)
#   2. Easy to parse with struct.unpack (all fields are predictable offsets)
#   3. Prevents name-injection attacks (someone putting extra data in name field)
TEAM_NAME_LENGTH = 32

# Card encoding in payload: rank in 2 bytes, suit in 1 byte
# Rank: 01-13 (fits in 2 bytes, but we use exact value for clarity)
# Suit: 0-3 (fits in 1 byte)
CARD_RANK_BYTES = 2
CARD_SUIT_BYTES = 1

# ============ GAME RULES ============
DEALER_HIT_THRESHOLD = 17   # Dealer hits if < 17, stands if >= 17
MAX_HAND_VALUE = 21
ACE_HIGH_VALUE = 11
ACE_LOW_VALUE = 1
FACE_CARD_VALUE = 10

# ============ DECK CONSTANTS ============
DECK_SIZE = 52
RANKS_PER_SUIT = 13
SUITS = 4

# Rank constants (1-13)
RANK_ACE = 1
RANK_JACK = 11
RANK_QUEEN = 12
RANK_KING = 13

# Suit constants (0-3)
SUIT_HEARTS = 0
SUIT_DIAMONDS = 1
SUIT_CLUBS = 2
SUIT_SPADES = 3

# ============ GAME PARAMETERS ============
MAX_ROUNDS = 255  # Fits in 1 byte per protocol spec
INITIAL_HAND_SIZE = 2  # Cards dealt at start of round
