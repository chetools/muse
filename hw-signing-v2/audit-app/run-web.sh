#!/bin/sh
# Start the Teacher Audit web front end on this machine.
cd "$(dirname "$0")"
exec python3 web.py --port 8766
