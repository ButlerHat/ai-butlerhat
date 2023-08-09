#!/bin/bash

# Init Anaconda
conda init bash

# Assert ~/.cloudflared directory exists
if [ ! -d ~/.cloudflared ]; then
    echo No ~/.cloudflared directory found. The tunnel will not work.
    exit 1
fi
# Assert ~/.cloudflared/cert.pem exists
if [ ! -f ~/.cloudflared/cert.pem ]; then
    echo No ~/.cloudflared/cert.pem file found. The tunnel will not work.
    exit 1
fi

# Start the tunnel
cloudflared tunnel --config $HOME/.cloudflared/config_ai.yml run ai &

# Start interpreter server. The port is fixed to 8000 due to cloudflare tunnel
PYTHONPATH="." name_or_path=model/ /opt/conda/bin/python api/app.py
