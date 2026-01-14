"""
Listens for server offers on UDP port 13122.

Runs in a background thread so it doesn't block user input.
Collects all server offers and stores them in a thread-safe list.

Design principle: Separate network listening from user interaction.
The main thread waits for user input, this thread listens for broadcasts.
"""

import socket
import threading
from src.common.protocol import decode_offer
from config import OFFER_UDP_PORT, SOCKET_TIMEOUT


class OfferListener:
    def __init__(self):
        """Initialize the offer listener."""
        self.running = True
        self.socket = None
        self.offers = []  # List of {ip, port, name} dicts
        self.lock = threading.Lock()  # Thread-safe access to offers list
    
    def run(self):
        """
        Main listen loop: receive offers and collect them.
        Runs in background thread.
        """
        try:
            # Create UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Allow multiple processes to bind to same port (for testing on same machine)
            # Without this, two clients on same machine can't both listen on 13122
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Try SO_REUSEPORT if available (better for multiple clients)
            try:
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except (AttributeError, OSError):
                pass  # Not available on all systems
            
            # Bind to listen for broadcasts
            self.socket.bind(('0.0.0.0', OFFER_UDP_PORT))
            self.socket.settimeout(SOCKET_TIMEOUT)
            
            print(f"[Listener] Listening for server offers on port {OFFER_UDP_PORT}...")
            
            while self.running:
                try:
                    # Wait for UDP packet
                    data, (sender_ip, sender_port) = self.socket.recvfrom(1024)
                    
                    try:
                        # Try to decode as offer
                        tcp_port, server_name = decode_offer(data)
                        
                        # Store offer (check if already exists)
                        with self.lock:
                            # Check if we already have this server
                            duplicate = False
                            for offer in self.offers:
                                if offer['ip'] == sender_ip and offer['port'] == tcp_port:
                                    duplicate = True
                                    break
                            
                            if not duplicate:
                                self.offers.append({
                                    'ip': sender_ip,
                                    'port': tcp_port,
                                    'name': server_name
                                })
                                print(f"[Listener] Received offer from {server_name} @ {sender_ip}:{tcp_port}")
                    
                    except ValueError as e:
                        # Ignore invalid offers (not our protocol)
                        pass
                
                except socket.timeout:
                    # Timeout is fine, just retry
                    pass
                except Exception as e:
                    if self.running:
                        print(f"[Listener] Error receiving offer: {e}")
        
        except Exception as e:
            print(f"[Listener] Fatal error: {e}")
        
        finally:
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
    
    def get_offers(self):
        """
        Get current list of discovered servers.
        
        Returns:
            list[dict]: List of server info dicts with keys: ip, port, name
        """
        with self.lock:
            return list(self.offers)  # Return a copy
    
    def stop(self):
        """Stop the listener."""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
