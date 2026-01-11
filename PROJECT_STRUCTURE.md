# Blackjack Server-Client Network Application

**Team:** Blackijecky  
**Assignment:** Intro to Computer Networks 2025 Hackathon  
**Deadline:** January 14, 2026 (Moodle)

## Project Overview

This is a client-server blackjack game application using Python sockets for network communication. The implementation uses:
- **UDP** for server discovery (offer broadcasting)
- **TCP** for game session management
- **Threading** for concurrent client handling

## Project Structure

```
blackijecky/
├── src/
│   ├── common/                 # Shared modules used by both client & server
│   │   ├── protocol.py        # Message encoding/decoding (offers, requests, payloads)
│   │   ├── card.py            # Card class with rank, suit, and value calculation
│   │   ├── deck.py            # Standard 52-card deck with shuffle & draw
│   │   └── game_logic.py      # Core blackjack logic (hand evaluation, winner determination)
│   │
│   ├── server/                 # Server-side implementation
│   │   ├── server.py          # Main server entry point (TCP listener + threading)
│   │   ├── offer_broadcaster.py  # UDP offer announcements (threaded, sends every 1s)
│   │   └── game_handler.py    # Individual client session management
│   │
│   └── client/                 # Client-side implementation
│       ├── client.py          # Main client entry point
│       ├── offer_listener.py  # UDP listener on port 13122
│       ├── game_client.py     # TCP connection & communication with server
│       └── ui.py              # User interface & I/O handling
│
├── tests/                      # Unit tests
│   ├── test_card.py           # Card class tests
│   ├── test_deck.py           # Deck functionality tests
│   ├── test_protocol.py       # Protocol message encoding/decoding tests
│   └── test_game_logic.py     # Game logic & winner determination tests
│
├── config.py                   # Configuration constants (ports, timeouts, magic cookie)
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore file
└── README.md                   # This file (contains assignment requirements)
```

## Architecture Explanation

### **Common Layer** (`src/common/`)

**Protocol (`protocol.py`)**
- Encodes/decodes UDP offer messages (4-byte magic cookie: `0xabcddcba`)
- Encodes/decodes TCP request messages (client asks for N rounds)
- Encodes/decodes TCP payload messages (card data and game decisions)
- Constants: Magic cookie, message types (0x2=offer, 0x3=request, 0x4=payload)

**Card (`card.py`)**
- Represents a single playing card (rank 1-13, suit 0-3)
- Converts card ranks to blackjack values (2-10=numeric, J/Q/K=10, A=11)
- Provides string representation for display

**Deck (`deck.py`)**
- Manages a standard 52-card deck
- Shuffle algorithm for randomized card order
- Draw function to deal cards one at a time

**Game Logic (`game_logic.py`)**
- Hand evaluation (calculate sum, detect busts)
- Dealer logic (auto-hit if < 17, stand if ≥ 17)
- Winner determination algorithm

### **Server Layer** (`src/server/`)

**Main Server (`server.py`)**
- Initializes UDP broadcast socket and TCP listening socket
- Creates thread pool to handle multiple concurrent clients
- Graceful shutdown handling
- Logs: "Server started, listening on IP address [X.X.X.X]"

**Offer Broadcaster (`offer_broadcaster.py`)**
- Runs in separate thread
- Broadcasts offer message every 1 second via UDP to all clients
- Contains: magic cookie + message type (0x2) + TCP port + server name (32 bytes)
- Handles socket errors gracefully

**Game Handler (`game_handler.py`)**
- Accepts individual TCP connections from clients
- Receives number of rounds from client
- Executes game rounds in sequence
- After each round: evaluates winner and sends result (0x1=tie, 0x2=loss, 0x3=win)
- Handles card transmission (sends drawn cards to client in payload format)
- Manages deck shuffling

### **Client Layer** (`src/client/`)

**Main Client (`client.py`)**
- Entry point asking user for team name and number of rounds
- Starts UDP listener in background thread
- Loops waiting for user server selection
- Creates TCP connection and manages game session

**Offer Listener (`offer_listener.py`)**
- Binds to UDP port 13122 (hardcoded per spec)
- Listens for server offers
- Validates magic cookie
- Displays available servers to user: "Received offer from [IP]"
- Stores multiple offers for user to choose from

**Game Client (`game_client.py`)**
- Establishes TCP connection to selected server
- Sends request message (number of rounds + team name)
- Receives initial 2-card deal
- Main game loop: handles "Hit" vs "Stand" decisions
- Receives each card from server via payload message
- Shows dealer's hidden card when dealer's turn begins
- Tracks wins/losses/ties
- Prints final statistics: "Finished playing {x} rounds, win rate: {rate}%"

**UI (`ui.py`)**
- Display functions (show cards, hands, game state)
- Input functions (get player decisions, server selection)
- Statistics display
- Error messages and validation

### **Testing Layer** (`tests/`)

- Unit tests for card values and deck operations
- Protocol message encoding/decoding validation
- Game logic correctness (winner determination edge cases)
- Integration tests for client-server compatibility

## Key Design Decisions

1. **Modular Architecture**: Common code isolated to prevent duplication
2. **Threading**: Server uses thread pool for concurrent clients; client uses separate thread for offer listening
3. **Error Handling**: Message validation (magic cookie), timeout handling, graceful disconnects
4. **No Hard-coded IPs/Ports**: Only hardcoded UDP port 13122 (per spec); TCP port in offer message
5. **Protocol Compliance**: Exact message format as specified (byte-by-byte format)

## Protocol Summary

| Message | Direction | Format |
|---------|-----------|--------|
| **Offer** | Server→Client (UDP) | Magic cookie (4) + Type 0x2 (1) + TCP port (2) + Server name (32) |
| **Request** | Client→Server (TCP) | Magic cookie (4) + Type 0x3 (1) + Rounds (1) + Team name (32) |
| **Payload** | Both directions (TCP) | Magic cookie (4) + Type 0x4 (1) + Decision "Hittt"/"Stand" (5) OR Result (1) + Card rank (2) + Suit (1) |

## Implementation Notes

- No busy-waiting (uses select/socket timeouts)
- SO_REUSEPORT for multiple clients on same machine
- Proper exception handling for network failures
- Clear logging at each game stage
- Timeout handling for hung clients

---

**Status:** Structure created - Ready for implementation
