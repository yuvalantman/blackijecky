#!/usr/bin/env python3
"""
MULTI-PLAYER TESTING GUIDE
===========================

How to test the Blackjack game with multiple simultaneous players.

ARCHITECTURE:
- 1 Server (handles multiple clients concurrently)
- Multiple Clients (each is independent)
- Each client plays N rounds independently
- Server logs show which client is playing and their results


STEP-BY-STEP:

1. START THE SERVER (in Terminal 1)
   =========================================
   cd C:\Users\yuval\OneDrive\מסמכים\BGU\5th_semester\Data_communication\blackijecky
   python -m src.server.server
   
   Expected output:
   ✓ Server started, listening on IP address 192.168.1.234
   ✓ TCP port: 60000 (some random port)
   
   The server will now:
   - Broadcast "offer" announcements via UDP every 1 second
   - Wait for clients to connect
   - Handle each client in a separate thread


2. START FIRST CLIENT (in Terminal 2)
   =========================================
   cd C:\Users\yuval\OneDrive\מסמכים\BGU\5th_semester\Data_communication\blackijecky
   python -m src.client.client
   
   Then:
   - Enter team name: "horse" (or any name)
   - Enter rounds: 3
   - Select server from list
   
   The client will:
   - Discover server via UDP broadcast
   - Connect and play 3 rounds
   - Show final statistics


3. START SECOND CLIENT (in Terminal 3, while first client is playing!)
   =========================================
   cd C:\Users\yuval\OneDrive\מסמכים\BGU\5th_semester\Data_communication\blackijecky
   python -m src.client.client
   
   Then:
   - Enter team name: "team2" (different name)
   - Enter rounds: 3
   - Select server from list
   
   NOW BOTH CLIENTS ARE PLAYING SIMULTANEOUSLY!
   - Server handles both in separate threads
   - They don't interfere with each other
   - Each plays their own rounds independently


4. OPTIONAL: START MORE CLIENTS
   =========================================
   Repeat step 3 with different team names: "team3", "team4", etc.
   
   You can have as many clients as you want!
   Each will play independently without blocking the others.


5. OBSERVE THE OUTPUT
   =========================================
   
   Server Terminal (Terminal 1):
   ✓ Shows which client connects: "Client horse from (192.168.1.234, 12345) wants 3 rounds"
   ✓ Shows dealer values and card draws for each client
   ✓ Shows round results: "Player: 11♦ 10♣ (value=21) vs Dealer: 12♥ 5♠ 10♣ (value=17) -> WIN"
   ✓ Shows final stats when each client finishes
   
   Client Terminals (2, 3, etc.):
   ✓ Shows their game progress
   ✓ Shows their round results
   ✓ Shows their final statistics
   
   
WHAT YOU'LL SEE:

Server Terminal Output Example:
------
Server started, listening on IP address 192.168.1.234
TCP port: 60000

Client horse from ('192.168.1.234', 63357) wants 3 rounds
[SERVER] Sending card: rank=11, suit=1, bytes=abcddcba040b0100
[SERVER] Sending card: rank=13, suit=3, bytes=abcddcba040d0300
[SERVER] Sending card: rank=10, suit=2, bytes=abcddcba040a0200
[SERVER] Received decision: 5374616e64 = b'Stand'
[SERVER] Sending card: rank=13, suit=0, bytes=abcddcba040d0000
[SERVER-DEALER] Initial value: 20, hand: ['102', '130']
[SERVER-DEALER] Final value: 20, stopping
[SERVER] Sending result: code=1, bytes=abcddcba05010000
[ROUND END] Player: 11♦ 13♠ 10♣ (value=20) vs Dealer: 10♣ 13♥ (value=20) -> TIE

Client horse: 0W 2L 1T (rate: 0.0%)

Client team2 from ('192.168.1.234', 58004) wants 3 rounds
[SERVER] Sending card: rank=9, suit=3, bytes=abcddcba04090300
...
Client team2: 2W 1L 0T (rate: 66.7%)
------


IMPORTANT DETAILS:

✓ Multiple clients DO NOT block each other
  - Server creates a new thread for each client
  - All clients play simultaneously
  
✓ Deck is fresh for each round
  - Each round, both server and client use a new deck
  - So you can see different card distributions
  
✓ Server graceful shutdown
  - Press Ctrl+C in server terminal
  - Server waits for all games to complete
  - Then shuts down
  
✓ Client reconnection
  - Clients ask "Play again?" after each session
  - You can reconnect to same or different server


TESTING CHECKLIST:

□ 1 server + 1 client works
□ 1 server + 2 clients simultaneously work
□ 1 server + 3+ clients work
□ Server shows all clients' games in output
□ Each client plays independently without interference
□ Results are correct for all clients
□ Server can shutdown with Ctrl+C
□ Multiple clients can reconnect after first game


DEBUGGING TIPS:

If a client hangs or times out:
  - Check server terminal for errors
  - Make sure server port is not blocked
  - Try different port (change in code or restart with different port)
  
If server crashes:
  - Check Python error messages
  - Verify no other server is running on same port
  - Try: Get-Process python | Stop-Process -Force
  
If UDP broadcast discovery fails:
  - Check firewall settings
  - Make sure UDP port 13122 is not blocked
  - Try connecting directly with IP:port instead


EXAMPLE SESSION:

Terminal 1 (Server):
$ python -m src.server.server
Server started, listening on IP address 192.168.1.234
TCP port: 60000
Client horse from ('192.168.1.234', 11111) wants 3 rounds
[Start playing...]
Client horse: 1W 2L 0T

Client team2 from ('192.168.1.234', 22222) wants 2 rounds
[Start playing...]
Client team2: 2W 0L 0T

Terminal 2 (Client 1):
$ python -m src.client.client
Enter team name: horse
Enter rounds: 3
[Plays 3 rounds...]
FINAL STATISTICS
Wins: 1, Losses: 2, Ties: 0

Terminal 3 (Client 2):
$ python -m src.client.client
Enter team name: team2
Enter rounds: 2
[Plays 2 rounds while Client 1 is playing...]
FINAL STATISTICS
Wins: 2, Losses: 0, Ties: 0
"""

print(__doc__)
