"""
Main server entry point for the Blackjack game.

Responsibilities:
- Bind TCP socket to any available port
- Start UDP broadcaster thread (announces to clients)
- Accept client connections and spawn game handlers
- Graceful shutdown

Threading model:
- Main thread: TCP accept loop (waits for clients)
- Broadcaster thread: UDP loop (sends offers every 1s, daemon)
- Game handler threads: One per connected client (handles their game)
"""

import socket
import threading
import sys
from src.server.offer_broadcaster import OfferBroadcaster
from src.server.game_handler import GameHandler
from config import SOCKET_TIMEOUT


class BlackjackServer:
    def __init__(self, server_name="Blackijecky"):
        """
        Initialize server.
        
        Args:
            server_name (str): Team name to broadcast
        """
        self.server_name = server_name
        self.tcp_socket = None
        self.tcp_port = None
        self.broadcaster = None
        self.broadcaster_thread = None
        self.running = True
        self.handlers = []  # Track active game handler threads
    
    def start(self):
        """
        Start the server and begin accepting clients.
        """
        try:
            # Bind TCP socket to any available port
            # Binding to 0 means: "OS, pick any available port"
            # We get the actual port via getsockname()
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_socket.bind(('0.0.0.0', 0))  # 0 = any available port
            self.tcp_socket.listen(5)  # Queue up to 5 pending connections
            self.tcp_socket.settimeout(1.0)  # 1 second timeout on accept() so Ctrl+C works
            
            # Get the actual port we bound to
            self.tcp_port = self.tcp_socket.getsockname()[1]
            print(f"Server started, listening on IP address {self._get_local_ip()}")
            print(f"TCP port: {self.tcp_port}")
            
            # Start broadcaster thread (daemon so it dies with main thread)
            self.broadcaster = OfferBroadcaster(self.tcp_port, self.server_name)
            self.broadcaster_thread = threading.Thread(target=self.broadcaster.run, daemon=True)
            self.broadcaster_thread.start()
            
            # Main loop: accept clients and spawn handlers
            self._accept_clients()
            
        except KeyboardInterrupt:
            print("\nShutting down...")
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            self.shutdown()
    
    def _get_local_ip(self):
        """
        Get the local IP address that will reach other machines on the network.
        
        This is a bit hacky but standard: create a socket, connect to an external address
        (doesn't actually send data), and read what address the OS assigned locally.
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # This doesn't actually connect, just binds for address discovery
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    def _accept_clients(self):
        """
        Main server loop: accept TCP connections and spawn game handlers.
        
        Each client connection gets its own thread so multiple games run concurrently.
        Socket timeout allows Ctrl+C to interrupt accept() quickly.
        """
        while self.running:
            try:
                # Accept one client connection
                # Socket timeout (1s) means we check self.running frequently
                client_socket, client_address = self.tcp_socket.accept()
                
                # Spawn a new thread to handle this client's game
                # Don't pass daemon=True - we want to wait for games to finish
                handler = GameHandler(client_socket, client_address)
                handler_thread = threading.Thread(target=handler.handle_game)
                handler_thread.start()
                
                self.handlers.append(handler_thread)
                
            except socket.timeout:
                # Timeout is normal - just loop again and check self.running
                continue
            except KeyboardInterrupt:
                break
            except Exception as e:
                if self.running:
                    print(f"Error accepting client: {e}")
    
    def shutdown(self):
        """
        Graceful shutdown: close sockets and wait for game threads.
        """
        self.running = False
        
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except:
                pass
        
        if self.broadcaster:
            self.broadcaster.stop()
        
        # Wait for active game handlers to finish
        print("Waiting for active games to complete...")
        for thread in self.handlers:
            if thread.is_alive():
                thread.join(timeout=1)


def main():
    server = BlackjackServer()
    server.start()


if __name__ == "__main__":
    main()
