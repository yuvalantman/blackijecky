"""
Broadcasts server availability via UDP every 1 second.

Runs in a separate daemon thread so it doesn't block client game loops.
The offer message tells clients: "Hey, I'm a blackjack server on this IP at this TCP port".

Every team running a server broadcasts simultaneously on the same port (13122).
Clients hear all of them and pick which one to connect to.
"""

import socket
import time
import threading
from src.common.protocol import encode_offer
from config import OFFER_UDP_PORT, BROADCAST_ADDRESS, OFFER_BROADCAST_INTERVAL


class OfferBroadcaster:
    def __init__(self, tcp_port, server_name):
        """
        Initialize broadcaster.
        
        Args:
            tcp_port (int): Server's TCP port to advertise
            server_name (str): Server/team name to broadcast
        """
        self.tcp_port = tcp_port
        self.server_name = server_name
        self.running = True
        self.socket = None
    
    def run(self):
        """
        Main broadcast loop: send offer every 1 second forever.
        
        This runs in a daemon thread, so if it crashes, the server doesn't crash.
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Enable broadcast permission on this socket
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            while self.running:
                try:
                    # Encode the offer message
                    offer_msg = encode_offer(self.tcp_port, self.server_name)
                    
                    # Send to broadcast address on port 13122
                    # 255.255.255.255 reaches all devices on the local network
                    self.socket.sendto(offer_msg, (BROADCAST_ADDRESS, OFFER_UDP_PORT))
                    
                    # Wait 1 second before next broadcast
                    time.sleep(OFFER_BROADCAST_INTERVAL)
                    
                except Exception as e:
                    print(f"Broadcast error: {e}")
                    # Don't crash, just keep trying
                    time.sleep(1)
        
        except Exception as e:
            print(f"Broadcaster startup error: {e}")
        
        finally:
            if self.socket:
                self.socket.close()
    
    def stop(self):
        """Signal the broadcaster to stop."""
        self.running = False
