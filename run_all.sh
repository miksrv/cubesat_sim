#!/bin/bash

source venv/bin/activate

echo "Starting all CubeSat services in background..."

python3 obc_service/obc.py &
python3 payload_service/payload.py &
python3 comm_service/comm.py &

echo "All services started."
echo "Use 'jobs' to see running processes."