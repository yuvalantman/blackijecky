# Server Implementation - Phase 2 Complete

**Status**: ✅ IMPLEMENTED

## What Was Built

### 1. **Main Server** (`src/server/server.py`)
- TCP socket bound to any available port (OS chooses)
- Prints local IP and port for clients to know where to connect
- Accepts client connections in a loop
- Spawns GameHandler thread per client
- Graceful shutdown on Ctrl+C

**Key decision**: Bind to port 0 lets OS choose, avoiding conflicts if multiple servers run on same machine.

### 2. **Offer Broadcaster** (`src/server/offer_broadcaster.py`)
- Runs as daemon thread
- Every 1 second: encode offer + broadcast to 255.255.255.255:13122
- Clients on the network hear these announcements and learn the server exists
- Resilient: if one broadcast fails, just retries next second

**Key decision**: Independent thread means broadcaster never blocks game handlers, and vice versa.

### 3. **Game Handler** (`src/server/game_handler.py`)
- Receives client's request (how many rounds, team name)
- For each round:
  - Creates fresh deck
  - Deals initial cards
  - Sends cards to client one at a time
  - Receives Hit/Stand decisions
  - Plays dealer automatically (deterministic: <17 hit, >=17 stand)
  - Determines winner
  - Sends result code (0x1=tie, 0x2=loss, 0x3=win)
- Tracks wins/losses/ties
- Prints statistics when done

**Key decision**: Fresh deck per round is simpler than reshuffle + reuse.

---

## How Server Works (Big Picture)

```
1. Start server.py
   ├─ Create TCP socket, bind to port 0 (OS picks port)
   ├─ Print "Server started on IP X.X.X.X"
   └─ Spawn OfferBroadcaster thread (daemon)
      └─ Every 1s: send "I'm here at X.X.X.X:PORT" to all devices

2. Main server thread: accept() loop
   └─ Client connects
      └─ Spawn GameHandler thread
         ├─ Receive request (5 rounds from TeamA)
         └─ For round 1-5:
            ├─ Fresh deck
            ├─ Deal cards
            ├─ Player turn: Hit/Stand loop
            ├─ Dealer turn: auto-play until >=17
            ├─ Determine winner
            └─ Send result
         └─ Print "TeamA: 3W 2L 0T"
         └─ Close connection

3. Repeat: more clients can connect while others play

4. Ctrl+C
   └─ Main thread: stop accepting
   └─ Wait for active games to finish
   └─ Broadcaster thread dies (daemon)
   └─ Exit
```

---

## Key Architectural Decisions Documented

1. **Port 0 binding**: OS chooses port, avoids conflicts
2. **Daemon broadcaster**: Independent from game logic, never blocks
3. **Thread-per-client**: Allows concurrent games
4. **Fresh deck per round**: Simpler than reuse + reshuffle
5. **Incremental card sending**: Each card sent immediately, client stays in sync
6. **Automatic dealer**: No decisions, deterministic logic
7. **Result codes**: Fixed binary codes (0x1/0x2/0x3), not strings

---

## What Happens When You Run It

```
$ python src/server/server.py
Server started, listening on IP address 192.168.1.10
TCP port: 54321

[broadcaster thread sends offers every 1s in background]
[waiting for client to connect...]

[Client connects from 192.168.1.20]
Client TeamAlpha from ('192.168.1.20', 55555) wants 3 rounds

[Client plays 3 rounds...]
[cards flow back and forth via TCP]

Client TeamAlpha: 2W 1L 0T (rate: 66.7%)

[waiting for next client...]
```

---

## Ready to Test

The server is now **independently testable**:
```bash
python src/server/server.py
```

It will:
- Print its IP and port
- Broadcast offers every second
- Wait for clients to connect (none connected yet, so it just waits)
- Handle each client perfectly once they connect

**Next**: Build client (game_client.py, offer_listener.py, client.py) to test against this server.

---

## Files Modified

- `src/server/server.py` - ✅ IMPLEMENTED
- `src/server/offer_broadcaster.py` - ✅ IMPLEMENTED
- `src/server/game_handler.py` - ✅ IMPLEMENTED
- `DECISIONS.md` - ✅ UPDATED with implementation details
