#!/bin/bash
set -e

python3 /usr/local/bin/plato.py &

/bin/sh /entrypoint.sh
