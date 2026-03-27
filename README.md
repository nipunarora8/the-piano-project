# Lumino — The Piano Project

A gorgeous, retro-styled piano web application that syncs in real-time with a physical LED strip. Built with a stunning dark-mode "Marshall Amp" aesthetic, the interface provides beautiful glowing visual feedback, waveform spectrum analysis, and subtle responsive particle effects while flawlessly mirroring your keystrokes to hardware LEDs.

Designed around an **M-Audio Keystation 61 MK3** and an **ESP32** driving a WS2812B LED strip via custom high-speed Serial or UDP (WLED).

---

## 🌟 Features

- **Web MIDI API Integration**: Instantly reads MIDI input directly from your piano keyboard (Chrome only).
- **Premium Retro UI**: Features a detailed amp-style interface with a massive dynamic center display that glows with the velocity and color of the last played key.
- **Real-Time Spectrum Analyzer**: Visualizes the audio output via a continuous glowing waveform.
- **Hardware-Synchronized LEDs**: Drives a physical LED strip where colors and brightness map precisely to what you play. Included custom key-mapping (E5 split) to seamlessly align uniform LED strips with piano string gaps.
- **Acoustic Sustain Simulation**: Holding the sustain pedal (MIDI CC 64) keeps notes ringing. When you release a sustained key, the physical LEDs will gracefully fade out over 4 seconds, perfectly mimicking the natural decay of a piano string. 
- **Live Customization Settings**: Tweak the aesthetic on the fly using the minimalist header controls. Instantly switch between custom-curated LED colormaps, or use the global LED brightness slider to dim the lights for night-time playing without losing relative velocity dynamics.
- **High-Performance Python Backend**: A robust `asyncio` Python server handles WebSocket traffic from the browser, decoupling it into a strictly capped 40 FPS render loop to prevent hardware UART buffer overflows when mashing chords.

---

## 🎹 Hardware Requirements

| Component | Details |
|-----------|---------|
| Keyboard | M-Audio Keystation 61 MK3 (MIDI range C3 to C8 / 48–108) |
| Microcontroller | ESP32-D0WD-V3 (or similar), driving the LEDs |
| LED strip | 62× WS2812B pixels physically mapped to 61 keys (E5 spans two LEDs) |
| Connection | WiFi UDP (WLED) or USB serial (~1 Mbaud Adalight) |

---

## 🚀 Running the Project

### 1. Start the Hardware Backend

```bash
# Install dependencies
pip install websockets pyserial

# Run the backend server
python3 piano_backend.py
```

The backend dynamically auto-detects an ESP32 connected via USB on macOS and automatically engages the high-speed Adalight serial protocol. If not found, it seamlessly falls back to WLED UDP.

### 2. Launch the Interface

Open `index.html` in **Google Chrome** (required for Web MIDI access).

Click **Connect MIDI + Audio** to initialize Tone.js and sync with your MIDI keyboard. The Salamander Grand Piano samples will be dynamically fetched on your first keystroke.

---

## 🔧 Architecture & Data Flow

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
- **Browser Compatibility**: Safari and Firefox do not natively support the Web MIDI API. You must use Chromium-based browsers.
- **ESP32 WiFi**: If you experience extreme UDP packet loss with WLED, standard ESP32 boards often suffer from antenna noise. The included USB Adalight serial mode skips WiFi entirely and provides flawless 1ms response times.
