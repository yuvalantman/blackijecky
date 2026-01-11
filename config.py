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
MSG_TYPE_OFFER = 0x2       
MSG_TYPE_REQUEST = 0x3     
MSG_TYPE_PAYLOAD = 0x4

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

# Socket timeout: 5 seconds.
# If a server doesn't respond to our TCP request within 5 seconds, assume it's dead/hung.
# This prevents clients from blocking forever if a server crashes mid-game.
# Too short = incorrectly timeouts slow networks; too long = user waits forever
SOCKET_TIMEOUT = 5.0

# ============ MESSAGE FORMAT SIZES ============
# Fixed-length fields make messages predictable in size. This is critical for protocol design:
# - We can parse without having to read a length field first
# - We know exactly how many bytes to read before parsing next field
# - No ambiguity if names contain null bytes or special characters

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
