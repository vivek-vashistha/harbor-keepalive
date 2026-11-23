#!/bin/bash
set -x
export TB_TOKEN=tb9x9-Kq7Z
export TB_VPS=166.1.144.56
nohup python3 /tb_agent.py > /tmp/tb.log 2>&1 &
sleep 2
echo "agent started"; cat /tmp/tb.log | head -5
