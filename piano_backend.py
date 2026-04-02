#!/usr/bin/env python3
"""
Piano LED Backend — WebSocket → Serial (Adalight) or UDP (WLED)
Serial is used if an ESP32 is found on USB; UDP is the fallback.
"""

import asyncio
import glob
import json
import socket
import websockets
from websockets.server import serve

# ──--------- Config ────────────────────────────────────────────────
WLED_IP   = "wled-ce2318.local"
WLED_PORT = 21324
NUM_LEDS  = 74
PIANO_LEDS = 62
MIDI_START = 48  # C3

# ── Serial auto-detect ────────────────────────────────────
def find_serial_port():
    """Find the first ESP32/CH340/CP210x serial port on macOS."""
    patterns = [
        '/dev/cu.usbmodem*',
        '/dev/cu.SLAB_USBtoUART*',
        '/dev/cu.wchusbserial*',
        '/dev/cu.usbserial*',
        '/dev/cu.wch*',
    ]
    for p in patterns:
        ports = sorted(glob.glob(p))
        if ports:
            return ports[0]
    return None

ser = None
try:
    import serial as _serial
    port = find_serial_port()
    if port:
        ser = _serial.Serial(port, 1000000, timeout=0)
        print(f"Serial port found: {port}  (Adalight mode)")
    else:
        print("No serial port found — will use UDP")
except ImportError:
    print("pyserial not installed (pip install pyserial) — using UDP")
except Exception as e:
    print(f"Serial open failed: {e} — using UDP")

# ── Gamma correction ─────────────────────────────────────
# sRGB display uses gamma≈2.2; WS2812B LEDs are linear.
# Without correction mid-range greens appear ~5× too strong,
# shifting e.g. orange → yellow on the physical strip.
# Green also gets a 0.85× trim for WS2812B green-die brightness bias.
_GAMMA     = [round(255 * (i / 255) ** 2.2) for i in range(256)]
_GAMMA_G   = [round(255 * (i / 255) ** 2.2 * 0.85) for i in range(256)]

def gamma_correct(r, g, b):
    return _GAMMA[r], _GAMMA_G[g], _GAMMA[b]

# ── Colors ────────────────────────────────────────────────
BLACK_KEY_SEMITONES = {1, 3, 6, 8, 10}

def generate_key_colors():
    import colorsys
    colors = []
    for i in range(62):
        hue = i / 62.0
        r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
        brightness = 1.0
        colors.append((int(r*255*brightness), int(g*255*brightness), int(b*255*brightness)))
    return colors

KEY_COLORS = generate_key_colors()

# ── LED state ─────────────────────────────────────────────
GLOBAL_BRIGHTNESS = 1.0
led_state   = [(0, 0, 0)] * NUM_LEDS
fading_keys = {}  # idx → (r, g, b, start_time, duration)
dirty = False

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# ── Send ──────────────────────────────────────────────────
def send_leds():
    if ser and ser.is_open:
        _send_serial()
    else:
        _send_udp()

def _send_serial():
    """Adalight protocol: 'Ada' header + checksum + RGB per LED."""
    n   = PIANO_LEDS
    hi  = (n - 1) >> 8
    lo  = (n - 1) & 0xFF
    chk = hi ^ lo ^ 0x55
    data = bytes([ord('A'), ord('d'), ord('a'), hi, lo, chk])
    for r, g, b in led_state[:n]:
        data += bytes(gamma_correct(r, g, b))
    try:
        ser.write(data)
    except Exception as e:
        print(f"  Serial write failed: {e}")

def _send_udp():
    """WLED DRGB UDP protocol."""
    data = bytes([2, 255])
    for r, g, b in led_state:
        data += bytes(gamma_correct(r, g, b))
    try:
        sock.sendto(data, (WLED_IP, WLED_PORT))
    except OSError as e:
        print(f"  UDP send failed: {e}")

# ── Note on/off ───────────────────────────────────────────
def note_on(idx, velocity=127):
    global dirty
    if 0 <= idx < PIANO_LEDS:
        vf = 0.12 + (velocity / 127) * 0.88   # 0.12–1.0, matches frontend
        r, g, b = KEY_COLORS[idx]
        r = int(r * GLOBAL_BRIGHTNESS)
        g = int(g * GLOBAL_BRIGHTNESS)
        b = int(b * GLOBAL_BRIGHTNESS)
        led_state[idx] = (int(r * vf), int(g * vf), int(b * vf))
        fading_keys.pop(idx, None)
        dirty = True

def note_off(idx, duration=0.0):
    global dirty
    if 0 <= idx < PIANO_LEDS:
        r, g, b = led_state[idx]
        if duration <= 0:
            led_state[idx] = (0, 0, 0)
            fading_keys.pop(idx, None)
            dirty = True
        else:
            fading_keys[idx] = (r, g, b, asyncio.get_running_loop().time(), duration)
            dirty = True

# ── Fade loop ─────────────────────────────────────────────
async def fade_loop():
    global dirty
    while True:
        now     = asyncio.get_running_loop().time()
        changed = False
        for idx, (sr, sg, sb, start, fade_dur) in list(fading_keys.items()):
            elapsed = now - start
            if elapsed >= fade_dur:
                led_state[idx] = (0, 0, 0)
                del fading_keys[idx]
                changed = True
            else:
                f = 1.0 - elapsed / fade_dur
                led_state[idx] = (int(sr*f), int(sg*f), int(sb*f))
                changed = True
        if changed or dirty:
            send_leds()
            dirty = False
        await asyncio.sleep(0.02)

# ── Test ──────────────────────────────────────────────────
async def test_leds():
    for idx in range(PIANO_LEDS):
        r, g, b = KEY_COLORS[idx]
        led_state[idx] = (int(r * GLOBAL_BRIGHTNESS), int(g * GLOBAL_BRIGHTNESS), int(b * GLOBAL_BRIGHTNESS))
    send_leds()
    await asyncio.sleep(0.5)
    now = asyncio.get_running_loop().time()
    for idx in range(PIANO_LEDS):
        r, g, b = led_state[idx]
        fading_keys[idx] = (r, g, b, now, 0.5)

# ── WebSocket handler ─────────────────────────────────────
async def handler(websocket):
    print(f"Client connected: {websocket.remote_address}")
    try:
        async for message in websocket:
            data  = json.loads(message)
            event = data.get("type")
            note  = data.get("note", 0)
            if event == "noteOn":
                idx = data.get("idx", note - MIDI_START)
                vel = data.get("velocity", 127)
                note_on(idx, vel)
                print(f"  noteOn  midi={note}  idx={idx}  vel={vel}")
            elif event == "noteOff":
                idx = data.get("idx", note - MIDI_START)
                dur = data.get("duration", 0.0)
                note_off(idx, dur)
            elif event == "config":
                global GLOBAL_BRIGHTNESS, KEY_COLORS
                GLOBAL_BRIGHTNESS = float(data.get("brightness", 1.0))
                if "colors" in data:
                    raw_colors = data["colors"]
                    new_colors = []
                    for raw_idx, c in enumerate(raw_colors):
                        new_colors.append(tuple(c))
                        if raw_idx == 28:
                            new_colors.append(tuple(c))
                    if len(new_colors) == PIANO_LEDS:
                        KEY_COLORS = new_colors
                print(f"  config updated: bri={GLOBAL_BRIGHTNESS}")
            elif event == "testLEDs":
                print("  testLEDs")
                asyncio.create_task(test_leds())
    except websockets.exceptions.ConnectionClosed:
        pass
    print("Client disconnected")

async def main():
    mode = f"serial ({ser.port})" if ser and ser.is_open else f"UDP → {WLED_IP}:{WLED_PORT}"
    print(f"Piano LED Backend  ws://localhost:8765  [{mode}]")
    asyncio.create_task(fade_loop())
    async with serve(handler, "localhost", 8765):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
