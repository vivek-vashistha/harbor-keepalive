#!/bin/bash
set -x
export TB_TOKEN=tbk-859be892398a50ad635b6909
export TB_VPS=166.1.144.56
nohup python3 /tb_agent.py > /tmp/tb.log 2>&1 &
sleep 2
echo "agent started"; cat /tmp/tb.log | head -5
