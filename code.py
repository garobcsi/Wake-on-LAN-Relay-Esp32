import time
import wifi
import socketpool
import binascii
import board
import digitalio
import microcontroller
import supervisor

# --- CONFIGURATION ---

# 1. WIFI SSID & Password 
CIRCUITPY_WIFI_SSID = "Your_WiFi_Name"
CIRCUITPY_WIFI_PASSWORD = "Your_WiFi_Password"

# 2. The MAC address of the PC you want to wake
TARGET_MAC_ADDRESS = "AA:BB:CC:DD:EE:FF" 

# 3. The IP Address to send the packet to.
# BEST OPTION: Use your network's "Broadcast Address" (e.g. 192.168.1.255).
# This ensures the packet reaches the PC even if the router has forgotten its IP while it sleeps.
# ALTERNATIVE: You can try the specific IP (e.g. 192.168.1.105), but it might fail if the ARP cache clears.
TARGET_IP_ADDRESS = "192.168.1.255"

# 4. The Port (Standard WoL is 9 or 7)
PORT = 9 

# 5. USB DETECTION SETTING
# If True: The code will NOT run network logic when plugged into a computer.
# If False: The code will run even if plugged into a computer (useful for debugging).
STOP_ON_USB_CONNECTION = True

# --- HARDWARE SETUP ---
try:
    led = digitalio.DigitalInOut(board.LED)
    led.direction = digitalio.Direction.OUTPUT
except Exception as e:
    print(f"Hardware Warning: LED setup failed ({e})")
    led = None

# --- HELPER FUNCTIONS ---

def create_magic_packet(mac_address):
    mac_cleaned = mac_address.replace(":", "").replace("-", "")
    if len(mac_cleaned) != 12:
        raise ValueError(f"Invalid MAC Address format: {mac_address}")
    mac_bytes = binascii.unhexlify(mac_cleaned)
    return b'\xff' * 6 + mac_bytes * 16

def blink_led_safe(times, speed=0.1):
    if led is None: return
    try:
        for _ in range(times):
            led.value = True
            time.sleep(speed)
            led.value = False
            time.sleep(speed)
    except Exception:
        pass 

# --- USB CHECK ---

if STOP_ON_USB_CONNECTION and (supervisor.runtime.usb_connected or supervisor.runtime.serial_connected):
    print("------------------------------------------------")
    print("USB DATA CONNECTION DETECTED")
    print("WoL Relay is PAUSED to allow coding/editing.")
    print("Unplug from PC and use a wall charger to run.")
    print("------------------------------------------------")
    
    while True:
        blink_led_safe(10, speed=0.5) 
        time.sleep(1)

# --- NETWORK SETUP ---

print("Init: Connecting to WiFi...")
try:
    wifi.radio.connect(CIRCUITPY_WIFI_SSID, CIRCUITPY_WIFI_PASSWORD)
    print(f"Connected! Pico IP: {wifi.radio.ipv4_address}")
    print(f"Targeting: {TARGET_IP_ADDRESS} for device {TARGET_MAC_ADDRESS}")
except Exception as e:
    print(f"WiFi Connection failed: {e}")
    time.sleep(10)
    blink_led_safe(2)
    microcontroller.reset()

try:
    pool = socketpool.SocketPool(wifi.radio)
    sock = pool.socket(pool.AF_INET, pool.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PORT))
    sock.setblocking(True)
    
    target_packet = create_magic_packet(TARGET_MAC_ADDRESS)
    print(f"Ready: Listening on UDP Port {PORT}")
except Exception as e:
    print(f"Socket setup failed: {e}")
    time.sleep(10)
    blink_led_safe(3)
    microcontroller.reset()

# --- MAIN LOOP ---

while True:
    try:
        buffer = bytearray(1024)
        
        size, sender_address = sock.recvfrom_into(buffer)
        
        if size >= 102 and buffer[0:6] == b'\xff' * 6:
            print(f"[{time.monotonic()}] Magic Packet received from {sender_address[0]}")
            
            sock.sendto(target_packet, (TARGET_IP_ADDRESS, PORT))
            
            print(f"--> Relayed packet to {TARGET_IP_ADDRESS}")
            blink_led_safe(1)
        else:
            print(f"Ignored non-magic packet from {sender_address[0]}")

    except OSError as e:
        print(f"Network Error: {e}")
        time.sleep(10)
        blink_led_safe(4)
        if e.errno == 104 or e.errno == 113: # ECONNRESET or EHOSTUNREACH
            microcontroller.reset()

    except Exception as e:
        print(f"Unexpected Error: {e}")
        time.sleep(10)
        blink_led_safe(5)
        microcontroller.reset()