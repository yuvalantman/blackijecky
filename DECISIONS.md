# Architectural Decisions & Code Explanations

A living document explaining the "why" behind each design decision, what the code does, and key architectural insights.

---

## Common Layer

### Protocol Messages (`src/common/protocol.py`) ✅ IMPLEMENTED
**Status**: ✅ IMPLEMENTED
**What it does:**
Handles encoding and decoding of all network messages: UDP offers from servers, TCP requests from clients, and payload messages (cards and game decisions).

**Why this design:**
Rather than scattering protocol code everywhere, I centralized it here. This way, if the spec changes or if I find a bug in message parsing, there's one place to fix it. The client and server both import these functions, so they're guaranteed to be compatible.

**Key concepts:**
- Magic cookie (0xabcddcba) validates messages - if a packet doesn't start with this, it's garbage and we ignore it
- Message types are single bytes: 0x2=offer (server telling clients it exists), 0x3=request (client joining), 0x4=payload (game data)
- Fixed-length fields (like 32-byte server names) are padded with zeros - this ensures every message is predictable in size

**Trade-off:** Binary format is hard to debug (can't just read the bytes), but the spec requires it. Could use JSON for development and switch later, but that's wasted effort.

---

### Card Class (`src/common/card.py`) ✅ IMPLEMENTED

**What it does:**
Represents a single playing card. Each card has a rank (1-13 where 1=Ace, 11=Jack, 12=Queen, 13=King) and suit (0=Hearts, 1=Diamonds, 2=Clubs, 3=Spades).

**Why this design:**
Object-oriented. Rather than passing around tuples like `(1, 0)` everywhere, having a Card object is self-documenting. The value calculation lives here too - this is where we handle the Ace logic (Ace = 11 in blackjack).

**Key concepts:**
- `value()` method returns the blackjack value of the card (different from its rank)
- Rank 1-13 vs 0-12: I chose 1-13 to match the protocol spec, even though it's slightly less Pythonic
- Cards are immutable once created

**Trade-off:** Could use simple dicts or tuples and save a class, but then card logic is scattered. Class keeps it organized.

---

### Deck Class (`src/common/deck.py`) ✅ IMPLEMENTED

**What it does:**
Manages the 52-card deck. Shuffles it, lets you draw cards, and can reset for a fresh deck.

**Why this design:**
The deck is state - it starts with 52 cards, and as you draw, it shrinks. Wrapping this in a class prevents bugs like accidentally using the same deck twice or drawing more cards than exist. The shuffle happens in `__init__` so every new Deck is random.

**Key concepts:**
- Fresh deck per round: The spec says "dealer shuffles the deck" each round, so I create a new Deck object
- `draw()` returns the next card and tracks how many we've used
- Simple list-based approach: fast enough for 52 cards

**Trade-off:** Could use `random.shuffle()` or a custom Fisher-Yates, both work. I'm just using Python's built-in shuffle, which is plenty random.

---

### Game Logic (`src/common/game_logic.py`) ✅ IMPLEMENTED

**What it does:**
The actual blackjack rules: calculating hand values (with Ace handling), determining if someone busts, deciding when the dealer should hit/stand, and figuring out who won.

**Why this design:**
This is the core logic that both server and client need. The server executes it to play the game, but the client can also verify the logic independently. By isolating it, we make sure the logic is consistent and testable.

**Key concepts:**
- Ace handling: Aces are initially 11, but if the total exceeds 21 and there's an Ace, we recalculate that Ace as 1 instead
- Dealer logic is deterministic: "Hit on 16, stand on 17" - no decisions, just math
- Winner determination: Bust loses immediately, otherwise compare totals

**Example logic:**
```
Hand [Ace, 6] = 17 (Ace counts as 11)
Hand [Ace, 6, 5] = 12 (Ace recounted as 1, because 11+6+5=22 would bust)
```

---

## Server Layer

### Main Server (`src/server/server.py`)

**What it does:**
The server entry point. It sets up two sockets: one for UDP broadcasting (telling the world it exists) and one for TCP listening (accepting client connections). As clients connect, we spawn a new thread to handle each one.

**Why this design:**
The server needs to do two things simultaneously: broadcast "I'm here!" to potential clients, and handle game sessions with connected clients. Threading solves this - the broadcaster runs in a background thread and doesn't block the main TCP accept loop.

**Key concepts:**
- TCP port is chosen dynamically by the OS (bind to 0 means "any available port"), then reported in the offer message
- Each client connection gets its own thread so multiple games can run at once
- UDP runs on a separate thread (daemon) so if the server crashes, it dies too

**Trade-off:** Threading is more complex than single-threaded, but necessary for concurrent games. An async approach would be even more scalable but overkill for this assignment.

---

### Offer Broadcaster (`src/server/offer_broadcaster.py`)

**What it does:**
Continuously broadcasts "Hey, I'm a blackjack server!" messages via UDP every second. Clients listen for these to discover available servers.

**Why this design:**
Clients need to find the server without knowing the IP address. Broadcasting on a well-known port (13122) lets any client on the network hear the announcement. The server doesn't need to know which clients exist - it just keeps announcing.

**Key concepts:**
- UDP broadcast address is `255.255.255.255` - this reaches all devices on the local network
- The offer includes the TCP port (which changes each run since we let the OS choose)
- Broadcasts every 1 second per spec requirement (not configurable)
- Runs as a daemon thread so it doesn't prevent the program from exiting

**Trade-off:** Broadcasting is less scalable than multicast but simpler and works across subnets. Could lower the 1-second interval for faster discovery but 1s is fine for this.

---

### Game Handler (`src/server/game_handler.py`)

**What it does:**
Manages one client's entire game session. Handles the round-by-round flow: dealing cards, receiving player decisions (Hit/Stand), executing dealer logic, determining winners, and reporting results.

**Why this design:**
Each client is independent. Rather than having the main server logic handle every client state, we spawn a separate handler for each one. The handler is responsible for one client's game from start to finish.

**Key concepts:**
- Receives request message first (tells us how many rounds the client wants to play)
- Main loop: for each round, deal cards → player turn → dealer turn → calculate winner → send result
- Player turn: repeatedly ask for Hit/Stand until they stand or bust
- Dealer turn: automatically hit until >= 17
- Keeps track of each player's win/loss/tie for final stats

**The flow looks like:**
1. Client connects, sends "I want to play 5 rounds"
2. For each of the 5 rounds:
   - Deal cards
   - Get player decisions
   - Run dealer logic
   - Send result (win/loss/tie)
3. Close connection

**Trade-off:** Per-client threads use more memory than a state machine approach, but the code is much simpler to understand and less error-prone.

---

## Client Layer

### Main Client (`src/client/client.py`)

**What it does:**
The client's entry point and main loop. Gets the player's team name and number of rounds, starts listening for server offers in the background, then repeatedly allows the player to choose a server and play.

**Why this design:**
The client needs to listen for server announcements (which come at random times) while also responding to user input (which happens at random times). A background listener thread solves this - it's constantly checking for offers while the main thread is free to wait for user input.

**Key concepts:**
- Asks user for team name and number of rounds upfront
- Starts offer_listener thread in background (will keep running and collecting server offers)
- Main loop allows the user to pick from available servers
- After each game, the player can reconnect to a different server or quit

**User flow:**
```
Enter team name: MyTeam
Enter number of rounds: 3
[Listening for servers...]
Received offer from 192.168.1.5
Received offer from 192.168.1.10
Select server (1-2): 1
[Playing 3 rounds...]
Finished playing 3 rounds, win rate: 66%
Play again? (1-2): ...
```

**Trade-off:** Could create a new listener for each game, but a persistent background listener is more efficient and gives better server discovery.

---

### Offer Listener (`src/client/offer_listener.py`)

**What it does:**
Listens on UDP port 13122 for server announcements. Runs in a background thread and collects all offers so the user can pick which server to connect to.

**Why this design:**
The spec requires clients to listen on port 13122. By running this in a separate thread, it doesn't block the user from entering decisions or selecting a server. The offers are stored in a list so the UI can display them.

**Key concepts:**
- Port 13122 is hardcoded per spec (non-negotiable)
- SO_REUSEPORT option allows multiple clients to run on the same machine
- Validates magic cookie (0xabcddcba) - if invalid, discards the packet
- Extracts server IP, TCP port, and server name from each offer
- Stores offers in a thread-safe structure (could use a queue)

**Why SO_REUSEPORT matters:**
If you run two clients on the same machine, they both need to listen on 13122. Without this option, the second client crashes because the port is already in use. With it, both can bind to the same port.

**Trade-off:** No de-duplication of servers - if a server broadcasts 5 times in a second, the client sees 5 offers. Could add logic to only show unique servers or timeout old offers, but simple is fine for now.

---

### Game Client (`src/client/game_client.py`)

**What it does:**
Handles the TCP connection and communication with the server during the game. Sends player decisions (Hit/Stand) and receives game updates (cards dealt, results).

**Why this design:**
This module encapsulates all the network communication for gameplay. The main client just calls functions here; it doesn't need to know about TCP sockets or message encoding.

**Key concepts:**
- Connects to the server's TCP port (obtained from the offer)
- Sends request message (number of rounds + team name)
- For each round:
  - Receives initial 2 cards for player and 1 for dealer (1 hidden)
  - Main loop: ask player to Hit or Stand
  - Send decision as payload message
  - Receive response (either new card if Hit, or result if game over)
  - Collect all cards the server sends
- After all rounds, prints stats and closes connection

**Message flow:**
```
Client → Server: "I want 3 rounds, my name is TeamA"
Server → Client: [Ace of Hearts, 5 of Diamonds]  [dealer first card shown]
Client → Server: "Hittt"
Server → Client: [10 of Clubs]
Client → Server: "Stand"
Server → Client: Result: Win
(repeat for rounds 2 and 3)
```

**Trade-off:** Could implement as a full state machine, but simple sequential code is clearer for this linear flow.

---

### UI (`src/client/ui.py`)

**What it does:**
All the user-facing stuff: displaying cards, game state, asking for player decisions, showing server lists. Keeps the UI logic separate from the network logic.

**Why this design:**
UI code is usually messy and changes a lot. By isolating it here, the rest of the code doesn't need to care how we display things. If we wanted to add colors, animations, or switch to a GUI, we only change this file.

**Key functions:**
- `show_hand(cards, is_player=True)` - display a list of cards nicely
- `get_player_decision()` - ask player "Hit or Stand?"
- `show_servers(servers)` - list available servers for user to choose
- `show_result(result_text)` - display game outcome
- `show_statistics(rounds, wins)` - print final stats

**Example output:**
```
Your hand: Ace♥ 5♦ (value: 16)
Dealer showing: King♣

Hit or Stand? hit
You draw: 10♠

Your hand: Ace♥ 5♦ 10♠ (value: 16) - BUST!
Dealer wins.
```

**Trade-off:** Could do fancy formatting or colors, but clear text is sufficient and works everywhere.

---

## Testing & Configuration

### Configuration (`config.py`) ✅ IMPLEMENTED

**What it does:**
Central place for all constants. UDP port, TCP timeout, magic cookie value, etc. Rather than typing `"255.255.255.255"` or `13122` in multiple places, we define them once here.

**Why this design:**
If the spec changes (e.g., "use port 14000 instead"), we change one line. If the constant is scattered everywhere, we might miss some and introduce bugs. Also makes the code more readable - `OFFER_UDP_PORT` is clearer than just `13122`.

**Key constants:**
```
Magic cookie: 0xabcddcba
Message types: 0x2=offer, 0x3=request, 0x4=payload
UDP port: 13122 (hardcoded per spec)
Dealer threshold: 17 (hit if < 17, stand if >= 17)
Max rounds: 255 (fits in 1 byte)
Team name length: 32 bytes (fixed per spec)
```

---

### Unit Tests (`tests/test_*.py`)

**What it does:**
Automated tests for each component. These run independently to verify that cards work, decks work, protocol encoding works, and game logic is correct.

**Why this design:**
Manual testing is tedious and error-prone. Tests run once and catch bugs forever. Particularly important for:
- **Card values**: Easy to get Ace logic wrong
- **Protocol encoding**: Off-by-one errors in byte packing are hard to debug
- **Game logic**: Edge cases like "dealer has 16" vs "dealer has 17"
- **Winner determination**: All the combinations (player bust, dealer bust, ties, etc.)

**Examples of what we test:**
```
test_card.py:
- Card(1, 0).value() == 11  (Ace of Hearts = 11)
- Card(11, 0).value() == 10  (Jack = 10)
- Card(5, 0).value() == 5   (5 = 5)

test_deck.py:
- Fresh deck has 52 cards
- draw() removes a card and returns it
- Can't draw more than 52 cards

test_protocol.py:
- Encode offer message and decode it - get same data back
- Validate magic cookie - reject if wrong
- Handle 32-byte team names properly (pad/truncate)

test_game_logic.py:
- Hand [A, 6] = 17 (Ace as 11)
- Hand [A, 5, 6] = 12 (Ace as 1 to avoid bust)
- Dealer decision: <17 hit, >=17 stand
- Winner: Player 21 beats Dealer 20
```

**Trade-off:** Takes time to write, but saves time debugging later. Focus on the tricky parts first (protocol, game logic).

---

## Key Architectural Insights

### Threading vs Async vs Single-threaded

I chose **threading** for this project because:
- The spec is simple - we don't have hundreds of concurrent connections
- Threading code is easier to understand than async/await
- Python's threading is good enough for this scale

A production system might use asyncio or a framework like FastAPI, but that's overkill here.

### Network Reliability

The spec says "think about what you should do if things fail." Here's my approach:
- **Timeout on socket reads**: If a client hangs, the server won't wait forever (set socket timeout)
- **Validate every message**: Check magic cookie and message type before processing
- **Graceful disconnects**: If a client drops mid-game, the server logs it and moves on
- **Retry logic**: Could add for client reconnection, but simple is fine for now

### Message Format Reason

Binary protocol (not JSON) because:
- Spec requires it
- Smaller message size (faster over slow networks)
- Harder to debug (but that's what logging is for)

### Port Selection Strategy

- **UDP offers on port 13122**: Hardcoded (clients need to know where to listen)
- **TCP per-server on random port**: OS chooses an available port, server reports it in the offer

Why? Avoids conflicts if multiple servers run on same machine. Each server gets its own port.

---

## Network Architecture Deep Dive

This section explains the *why* behind protocol design and network strategy. Understanding this is critical to knowing how teams can work together.

### Binary Protocol Design

**Why not JSON?**

We're using binary protocol (struct.pack/unpack) instead of text-based JSON. This choice affects everything:

**Binary advantages:**
- **Predictable message size**: Every message is exactly N bytes. Parser knows this. No length prefix needed.
- **Deterministic parsing**: No ambiguity from whitespace, encoding, or special characters
- **Network efficiency**: ~40 bytes vs ~150 bytes for same data in JSON. Matters when 100 messages fly across network
- **Interoperability**: All teams encode numbers identically (big-endian via '!' in struct format)

**Binary disadvantages:**
- Hard to debug: Can't just read raw bytes as text
- Easy to get wrong: Off-by-one errors in struct format string break everything
- Requires strict spec compliance: Everyone must agree on exact byte positions

**The trade-off:** We accept debugging difficulty for guaranteed interoperability. Correct choice for cross-team protocol.

### Fixed-Length Fields Philosophy

Why pad team names to 32 bytes instead of variable-length strings?

**With variable-length:**
```
Header: [magic][type][port][name_length=8][value="TeamAlpha"]...
```
Parser must: read length first, then read that many bytes. One bug = wrong name.

**With fixed-length:**
```
Header: [magic][type][port][32-byte padded name]...
```
Parser knows: name always at bytes 7-38. Simple math.

**The architectural win:** Fixed-length fields eliminate length prefixes or delimiters. This means:
- No parsing ambiguity (no need to interpret length field)
- Offset calculations are trivial (byte 0 = offset 0, always)
- Message size is predictable (sender and receiver see same bytes)
- Bugs caught immediately (wrong total size = protocol error)

### Magic Cookie Validation

Every message starts with 0xabcddcba. Why this specific value?

**What if we skipped it?**
- Server gets UDP packet from port 13122
- Assumes it's an offer... but another app broadcasts on that port!
- Parser tries to read team name from garbage → crash
- Network issues corrupt first bytes → crash

**With magic cookie:**
- First 4 bytes don't match? Discard immediately, no further parsing.
- Cheap check (one equality), prevents many crash scenarios
- Makes it trivial to ignore non-protocol traffic

The specific value 0xabcddcba is arbitrary, but must be in spec so all teams use identical value.

### Broadcast vs Unicast Discovery

**Why UDP broadcast instead of hardcoded server IP?**

Can't hardcode: server IPs change, servers die/restart, new servers appear.
Need automatic discovery.

**Why broadcast instead of alternatives?**
- **Broadcast (255.255.255.255)**: Reaches all devices on subnet. No infrastructure needed.
- **Multicast**: Cleaner, but disabled on some networks
- **DNS**: Would need external service we don't have
- **Central registry**: Single point of failure

Broadcast is simplest approach that works everywhere.

**Broadcast interval: 1 second per spec**
- Too fast: Network flooded, bandwidth wasted
- Too slow: Clients wait forever to discover server
- 1 second: Reasonable compromise

**Key insight:** Passive discovery. Server broadcasts, clients listen. Scales seamlessly.

### TCP vs UDP Split

**Why two protocols?**

- **UDP for offers**: One-way announcements, fire-and-forget. If client misses one, next comes in 1s.
- **TCP for gameplay**: Reliable delivery required. Losing "Hittt" message makes game nonsense.

**Why not just TCP?**
Server would need all client IPs to initiate connection. Client discovery becomes complex.

**Why not just UDP?**
Game messages cannot be lost. Would need to implement reliability on top (retransmits, timeouts). That's reinventing TCP.

**The split:** Use right tool for each job.

### Socket Timeout = Network Resilience

TCP sockets block forever on read() by default. If server crashes mid-message, client hangs infinitely.

**Solution: Socket timeout = 5 seconds**
```python
socket.settimeout(5.0)  # After 5s of no data, raise exception
```

**Why 5 seconds?**
- Too short (1s): LAN congestion causes false timeouts
- Too long (30s): User thinks app crashed, force-kills process
- 5s: Reasonable for hackathon LAN, rare enough to mean real problem

**In practice:**
- Fast networks send/receive in <100ms
- If nothing arrives in 5s, server is definitely dead
- Client can reconnect to different server

### Error Handling Philosophy

Every message we receive could be:
1. Corrupted (network errors, packet loss)
2. From wrong protocol (app listening on same port)
3. Malformed (attacker or test tool)
4. Truncated (incomplete packet)

**Our approach: Fail fast with validation**

Every decode function:
1. **Check length first** - prevent struct.unpack crashes
2. **Validate magic cookie** - reject non-protocol messages immediately
3. **Validate message type** - reject malformed messages early
4. **Decode with error handling** - UTF-8 errors don't crash (errors='ignore')
5. **Raise descriptive errors** - "Invalid magic cookie: got 0x1234" tells exactly what went wrong

This makes debugging possible. Error message tells you the problem, not just "struct failed".

### Threading Model & Concurrency

Server uses thread-per-connection model:
- Main thread: Accepts incoming TCP connections
- Broadcaster thread: Sends offers every 1s
- N game handler threads: One per connected client

**Why separate threads?**
- If game thread blocks waiting for player input, other clients continue playing
- If broadcaster blocked, game accepts would stop (bad)
- Each thread is independent

**Thread safety:**
- No shared mutable state (each game has own deck)
- Shared read-only data (port number) doesn't need locks
- No complex synchronization → no deadlock risk

This design is simple and safe for hackathon scale.

---

**This file will be updated as we implement each component.**

