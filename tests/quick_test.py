#!/usr/bin/env python3
"""
Quick sanity test for the fixed Blackjack server/client.
This tests:
1. Server can start
2. Client can connect
3. One full round can complete
"""

import socket
import struct
import time
import threading
from src.server.server import BlackjackServer

def run_server():
    """Run server in background thread."""
    try:
        server = BlackjackServer("TestServer")
        server.start()
    except KeyboardInterrupt:
        pass

def test_client_connection():
    """Test a single client connection."""
    time.sleep(2)  # Let server start
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', 50000))  # Will need to find actual port
        print("✓ Connected to server")
        
        # Send request for 1 round
        request = struct.pack('!IBB', 0xabcddcba, 0x3, 1) + b'test'.ljust(32, b'\x00')
        s.sendall(request)
        print("✓ Sent request")
        
        # Receive 3 cards
        cards_received = 0
        for i in range(3):
            data = s.recv(8)
            if len(data) == 8:
                magic, msg_type = struct.unpack('!IB', data[:5])
                if magic == 0xabcddcba and msg_type == 0x4:
                    cards_received += 1
                    rank = data[5]
                    suit = data[6]
                    print(f"✓ Received card {i+1}: rank={rank}, suit={suit}")
        
        if cards_received != 3:
            print(f"✗ Expected 3 cards, got {cards_received}")
            return False
            
        # Send Stand decision
        s.sendall(b'Stand')
        print("✓ Sent Stand decision")
        
        # Receive cards until result
        while True:
            data = s.recv(8)
            if len(data) < 8:
                print("✗ Incomplete payload received")
                return False
                
            magic, msg_type = struct.unpack('!IB', data[:5])
            if magic != 0xabcddcba:
                print(f"✗ Invalid magic cookie: {hex(magic)}")
                return False
            
            if msg_type == 0x4:
                # Card
                rank = data[5]
                print(f"✓ Dealer card: rank={rank}")
            elif msg_type == 0x5:
                # Result
                result_code = data[5]
                print(f"✓ Received result: code=0x{result_code:02x}")
                break
            else:
                print(f"✗ Unknown message type: 0x{msg_type:02x}")
                return False
        
        s.close()
        print("✓ Test PASSED!")
        return True
        
    except Exception as e:
        print(f"✗ Client error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("Starting quick sanity test...")
    print()
    
    # Start server in background
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Test client
    test_client_connection()
