# Lumino — The Piano Project

A gorgeous, retro-styled piano web application that syncs in real-time with a physical LED strip. Built with a stunning dark-mode "Marshall Amp" aesthetic, the interface provides beautiful glowing visual feedback, waveform spectrum analysis, and subtle responsive particle effects while flawlessly mirroring your keystrokes to hardware LEDs.

Designed around an **M-Audio Keystation 61 MK3** and an **ESP32** driving a WS2812B LED strip via custom high-speed USB serial (Adalight).

---

## 🌟 Features

- **Web MIDI API Integration**: Instantly reads MIDI input directly from your piano keyboard (Chrome only).
- **Premium Retro UI**: Features a detailed amp-style interface with a massive dynamic center display that glows with the velocity and color of the last played key.
- **Real-Time Spectrum Analyzer**: Visualizes the audio output via a continuous glowing waveform.
- **Hardware-Synchronized LEDs**: Drives a physical LED strip where colors and brightness map precisely to what you play. Included custom key-mapping (E5 split) to seamlessly align uniform LED strips with piano key gaps.
- **Acoustic Sustain Simulation**: Holding the sustain pedal (MIDI CC 64) keeps notes ringing. When you release a sustained key, the physical LEDs gracefully fade out over 4 seconds, perfectly mimicking the natural decay of a piano string.
- **Live Customization Settings**: Tweak the aesthetic on the fly using the minimalist header controls. Instantly switch between custom-curated LED colormaps, or use the global LED brightness slider to dim the lights for night-time playing without losing relative velocity dynamics.
- **No backend required**: The browser talks directly to the ESP32 over USB serial via the **Web Serial API** — no Python server, no WebSocket, nothing to install.

---

## 🎹 Hardware Requirements

| Component | Details |
|-----------|---------|
| Keyboard | M-Audio Keystation 61 MK3 (MIDI range C3 to C8 / 48–108) |
| Microcontroller | ESP32-D0WD-V3 (or similar), flashed with the Adalight sketch |
| LED strip | 62× WS2812B pixels physically mapped to 61 keys (E5 spans two LEDs) |
| Connection | USB serial at 1 Mbaud (Adalight protocol) |

---

## 🚀 Running the Project

There are two versions:

### `docs/index.html` — GitHub Pages / standalone (recommended)

Everything runs entirely in the browser using **Web MIDI API**, **Web Serial API**, and **Tone.js**. No server, no Python, nothing to install.

1. Open `docs/index.html` in **Google Chrome** (or any Chromium browser).
2. Click **Connect MIDI + Audio** to initialize audio and sync your MIDI keyboard.
3. Click **Connect LED Strip** in the header, select your ESP32's serial port, and the browser will talk directly to it at 1 Mbaud via Adalight.

> Also deployable to GitHub Pages — just point Pages at the `docs/` directory and open the URL.

### `index.html` — Local version with Python backend

The original local-only version. Requires a Python WebSocket server as a bridge between the browser and the ESP32.

```bash
# Install dependencies
pip install websockets pyserial

# Run the backend server (auto-detects ESP32 on USB, falls back to WLED UDP)
python3 piano_backend.py

# Open index.html in Chrome
```

---

## 🔧 Architecture & Data Flow

### Standalone (`docs/index.html`)

```text
[ MIDI Keyboard ]
       │ (USB)
       ▼
[ Google Chrome ]  <-- Web MIDI API + Web Serial API + Tone.js + Canvas UI
       │ (USB @ 1 Mbaud, Adalight protocol)
       ▼
    [ ESP32 ]      <-- Adalight firmware (FastLED)
       │ (GPIO)
       ▼
[ WS2812B Strip ]
```

### Local with Python backend (`index.html`)

```text
[ MIDI Keyboard ]
       │ (USB)
       ▼
[ Google Chrome ]  <-- Web MIDI API + Tone.js + Canvas UI
       │ (WebSocket @ ws://localhost:8765)
       ▼
[ Python Backend]  <-- Asyncio Server + 40 FPS Cap Rate
       │ (UDP or 1-Mbaud USB Serial)
       ▼
    [ ESP32 ]      <-- Adalight / WLED Firmware
       │ (GPIO)
       ▼
[ WS2812B Strip ]
```

### Advanced LED Mapping
Because uniform LED strips do not perfectly align with the physical spacing of black and white piano keys, Lumino includes manual array shifting. By default, **E5 (Index 28)** spans two physical LEDs (29 and 30) on the strip, and all subsequent notes are shifted by +1 to guarantee that your physical strip perfectly tracks your fingers all the way up the board.

---

## 🎨 Dynamic Color & Velocity Profile

Every key is permanently assigned a distinct vibrant hue from a 62-step color wheel. By default, the interface uses a full **Rainbow** spectrum, but you can select from several curated colormaps (Ocean, Fire, Synthwave, Cyberpunk, Forest, Crimson, or Pure Gold) instantly using the header dropdown. The chosen colormap is dynamically repainted on the browser's UI keys in real-time, matching exactly what is pushed to the physical LEDs.

**Precision Velocity Mapping**: How hard you strike the piano directly controls the exact final brightness of both the UI glow and the physical LED strip!
- The MIDI velocity (0–127) scales the brightness dynamically on a curve from a **12% base idle glow** up to a **piercing 100% full strike**. (This total output curve can be clamped globally using the LED Brightness slider).
- Smashing a key creates a larger, higher-velocity burst of digital dust particles that drift upwards more violently than gently pressing a key.

---

## ⚠️ Notes
- **Browser Compatibility**: Safari and Firefox do not support Web MIDI or Web Serial APIs. You must use Chrome or a Chromium-based browser.
- **Web Serial prompt**: The first time you click **Connect LED Strip**, Chrome will show a port-picker dialog. Select your ESP32's USB serial port. This permission persists for the session.
- **ESP32 firmware**: Flash `esp32_serial/esp32_serial.ino` (FastLED Adalight sketch) onto your ESP32. Set `DATA_PIN` to match your LED data GPIO before flashing.
