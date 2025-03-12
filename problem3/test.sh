#!/bin/bash
CONFIGS=(
    "enabled enabled"
    "enabled disabled"
    "disabled enabled"
    "disabled disabled"
)

PORT=12345
HOST="172.21.124.53"

for config in "${CONFIGS[@]}"; do
    read NAGLE DELAYED <<< "$config"
    echo "Running configuration: Nagle = $NAGLE, Delayed-ACK = $DELAYED"
    
    sudo -E python3 tcp_conn.py --mode server --port "$PORT" --nagle "$NAGLE" --delayed_ack "$DELAYED" > "server_${NAGLE}_${DELAYED}.log" 2>&1 &
    SERVER_PID=$!
    echo "Server started with PID $SERVER_PID"
    sleep 5

    echo "Starting client"
    python3 tcp_conn.py --mode client --host "$HOST" --port "$PORT" --nagle "$NAGLE" --delayed_ack "$DELAYED" > "client_${NAGLE}_${DELAYED}.log" 2>&1

    echo "Waiting for server (PID $SERVER_PID) to finish"
    wait $SERVER_PID
    echo "Configuration Nagle=$NAGLE, Delayed-ACK=$DELAYED completed"
    echo ""
    sleep 5
done

echo "Done"
