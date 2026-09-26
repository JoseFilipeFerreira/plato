#!/bin/sh
set -e

# Launch Plato
/opt/venv/bin/python /usr/local/bin/plato.py &

# Launch Homer
exec lighttpd -D -f /lighttpd.conf
