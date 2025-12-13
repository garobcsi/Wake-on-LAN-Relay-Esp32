# ESP32 Wake-on-LAN (WoL) Relay

This CircuitPython script turns a ESP32 into a dedicated Wake-on-LAN relay bridge. It solves the common problem where routers refuse to route Magic Packets sent from the internet (WAN) to the local network broadcast address.

## How it Works

1. Listens: The ESP32 sits on your local network and listens on a specific UDP port (e.g., Port 9).

2. Detects: When you send a packet from outside your network (via port forwarding).

3. Relays: The ESP32 generates a new Magic Packet targeting your specific PC and broadcasts it internally to the local network (LAN), waking the target machine.

## Configuration

| Variable                  | Description                                                                                                                                                 |
|---------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `CIRCUITPY_WIFI_SSID`     | Your WiFi Network Name.                                                                                                                                     |
| `CIRCUITPY_WIFI_PASSWORD` | Your WiFi Password.                                                                                                                                         |
| `TARGET_MAC_ADDRESS`      | The MAC address of the PC you want to wake (e.g., "AA:BB:CC:DD:EE:FF").                                                                                     |
| `TARGET_IP_ADDRESS`       | Highly Recommended: Use your subnet broadcast IP (e.g., 192.168.1.255). This ensures the packet reaches the PC even if it is sleeping and has no active IP. |
| `PORT`                    | The UDP port to listen on. Standard WoL ports are `7` or `9`.                                                                                               |
