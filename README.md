# Blackijecky - Client-Server Blackjack Game

A network-based blackjack implementation using Python 3.11+. Binary protocol with UDP discovery and TCP gameplay.

## Quick Start

### Prerequisites
```bash
pip install -r requirements.txt
```

### Run Server
```bash
python -m src.server.server
```
Output: `Server started, listening on IP address X.X.X.X`

### Run Client(s)
```bash
python -m src.client.client
```
Client will discover servers via UDP broadcast and let you choose which one to play against.

### Run Tests
```bash
python -m pytest tests/ -v
```

## Project Structure

- **`src/common/`** - Shared: Card, Deck, GameLogic, Protocol encoding/decoding
- **`src/server/`** - Server: main loop, UDP broadcaster, game handler
- **`src/client/`** - Client: main loop, UDP listener, TCP connection, UI
- **`tests/`** - Unit tests (52 tests, all passing)
- **`config.py`** - All constants (ports, timeouts, game rules)
- **`DECISIONS.md`** - Architectural decisions & exam prep material
- **`ARCHITECTURE.md`** - Complete file/function reference (learn the codebase here)

## Game Rules (Simplified Blackjack)

**Deck & Values:**
- Standard 52-card deck
- 2-10: numeric value
- J, Q, K: 10 points
- A (Ace): 11 points

**Round Flow:**
1. Server deals 2 cards to player, 2 to dealer (player sees 1 dealer card)
2. Player: repeatedly choose Hit (get card) or Stand (keep total)
3. Player busts (>21)? Lose immediately
4. Dealer: automatically hits if <17, stands if ≥17
5. Compare totals: higher wins, equal is tie

**Result:** Player bust = loss, Dealer bust = win, higher total = win, lower total = loss, equal = tie

## Network Protocol

**Three message types:**

| Type | Direction | Format | Notes |
|------|-----------|--------|-------|
| **Offer** (0x2) | Server→Client UDP | Magic cookie + type + TCP port + server name | Sent every 1 sec on port 13122 (broadcast) |
| **Request** (0x3) | Client→Server TCP | Magic cookie + type + num_rounds + team name | Join request |
| **Payload** (0x4) | Both TCP | Magic cookie + type + data | Card / Decision / Result |

All messages start with magic cookie `0xabcddcba` (validates authenticity).

## Documentation Guide

- **Running tests?** All 52 tests pass: `python -m pytest tests/ -v`

## Key Implementation Details

- **Threading:** One thread per client + daemon broadcaster thread
- **Protocol:** Binary (struct.pack/unpack), fixed-length fields, big-endian byte order
- **Discovery:** UDP broadcast on port 13122, clients listen for server offers
- **Gameplay:** TCP connection, deterministic dealer logic (no randomness)
- **Game State:** Fresh deck per round, no reshuffling
