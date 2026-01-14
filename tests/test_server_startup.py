#!/usr/bin/env python3
"""Test server startup with debug output."""

import sys
import os

print("Starting imports...", flush=True, file=sys.stderr)

try:
    print("Importing server...", flush=True, file=sys.stderr)
    from src.server.server import BlackjackServer
    print("Server class imported OK", flush=True, file=sys.stderr)
    
    print("Creating server...", flush=True, file=sys.stderr)
    server = BlackjackServer()
    print("Server created OK", flush=True, file=sys.stderr)
    
    print("Starting server...", flush=True, file=sys.stderr)
    server.start()
    print("Server started OK", flush=True, file=sys.stderr)
    
except KeyboardInterrupt:
    print("\nKeyboard interrupt", flush=True, file=sys.stderr)
except Exception as e:
    import traceback
    print(f"ERROR: {e}", flush=True, file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
