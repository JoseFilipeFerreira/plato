#!/bin/bash
set -e

# Launch Plato
python3 /usr/local/bin/plato.py &

# Launch Homer
exec lighttpd -D -f /lighttpd.conf
