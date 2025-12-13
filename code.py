import os
import time
import wifi
import socketpool
import binascii
import board
import digitalio
import microcontroller
import supervisor
import neopixel

# --- CONFIGURATION ---

# 1. WIFI SSID & Password
CIRCUITPY_WIFI_SSID = os.getenv("CIRCUITPY_WIFI_SSID")
CIRCUITPY_WIFI_PASSWORD = os.getenv("CIRCUITPY_WIFI_PASSWORD")

# 2. The MAC address of the PC you want to wake
TARGET_MAC_ADDRESS = "AA:BB:CC:DD:EE:FF"

# 3. The IP Address to send the packet to.
# Use the broadcast address (ends in .255 for standard /24 networks).
TARGET_IP_ADDRESS = "192.168.1.255"

# 4. The Port (Standard WoL is 9 or 7)
PORT = 9

# 5. USB DETECTION SETTING
STOP_ON_USB_CONNECTION = True

# 6. NEOPIXEL BRIGHTNESS AND COLORS
NEOPIXEL_BRIGHTNESS = 0.01

RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 150, 0)
PURPLE = (180, 0, 255)
WHITE = (255, 255, 255)
OFF = (0, 0, 0)

# --- HARDWARE SETUP ---
led = None

try:
    led = neopixel.NeoPixel(board.NEOPIXEL, 1)
    led.brightness = NEOPIXEL_BRIGHTNESS
    led.fill(OFF)
except Exception as e:
    print(f"Hardware Warning: NeoPixel setup failed ({e})")

# --- HELPER FUNCTIONS ---

def create_magic_packet(mac_address):
    mac_cleaned = mac_address.replace(":", "").replace("-", "")
    if len(mac_cleaned) != 12:
        raise ValueError(f"Invalid MAC Address format: {mac_address}")
    mac_bytes = binascii.unhexlify(mac_cleaned)
    return b'\xff' * 6 + mac_bytes * 16

def blink_led_safe(times, color=WHITE, speed=0.1):
    if led is None: return
    try:
        for _ in range(times):
            led.fill(color)
            time.sleep(speed)
            led.fill(OFF)
            time.sleep(speed)
    except Exception:
        pass

# --- USB/SERIAL CHECK ---

if STOP_ON_USB_CONNECTION and (supervisor.runtime.usb_connected or supervisor.runtime.serial_connected):
    print("------------------------------------------------")
    print("USB/SERIAL CONNECTION DETECTED")
    print("WoL Relay is PAUSED to allow coding/editing.")
    print("Unplug from PC and use a wall charger to run.")
    print("------------------------------------------------")
    
    while True:
        blink_led_safe(10, YELLOW, 0.5)

# --- NETWORK SETUP ---

print("Init: Connecting to WiFi...")
try:
    wifi.radio.enabled = False
    time.sleep(0.5)
    wifi.radio.enabled = True
    
    wifi.radio.connect(CIRCUITPY_WIFI_SSID, CIRCUITPY_WIFI_PASSWORD)
    print(f"Connected! ESP32 IP: {wifi.radio.ipv4_address}")
    print(f"Targeting: {TARGET_IP_ADDRESS} for device {TARGET_MAC_ADDRESS}")
except Exception as e:
    print(f"WiFi Connection failed: {e}")
    time.sleep(10)
    blink_led_safe(2, RED, speed=0.2)
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
    blink_led_safe(3, RED, speed=0.2)
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
            blink_led_safe(1, GREEN, speed=0.05)
        else:
            print(f"Ignored non-magic packet from {sender_address[0]}")

    except OSError as e:
        print(f"Network Error: {e}")
        time.sleep(10)
        blink_led_safe(4, RED, speed=0.2)
        if e.errno == 104 or e.errno == 113 or e.errno == 12: # ECONNRESET, EHOSTUNREACH, ENOMEM
            microcontroller.reset()

    except Exception as e:
        print(f"Unexpected Error: {e}")
        time.sleep(10)
        blink_led_safe(5, RED, speed=0.2)
        microcontroller.reset()