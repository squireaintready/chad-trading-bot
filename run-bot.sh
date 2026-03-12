#!/bin/bash
# Launch Chad bot with SSL certs configured
export SSL_CERT_FILE=$(python3 -c "import certifi; print(certifi.where())")
exec python3 /Users/samjo/Desktop/autotrade/bot.py
