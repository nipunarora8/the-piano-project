/*
  LUMINO — ESP32 Serial LED Controller
  Receives Adalight protocol over USB serial, drives the LED strip.
  Use this instead of WLED when WiFi is unreliable.

  Setup:
    1. Install Arduino IDE + ESP32 board package
       (https://docs.espressif.com/projects/arduino-esp32/en/latest/installing.html)
    2. Install FastLED library (Sketch > Include Library > Manage Libraries > FastLED)
    3. Set DATA_PIN to match your WLED config (check WLED > LED Preferences > GPIO)
    4. Flash to your ESP32
    5. pip install pyserial   (in the piano project)
    6. python3 piano_backend.py  (auto-detects the serial port)

  Adalight protocol (sent by piano_backend.py):
    Byte 0-2:  'A' 'd' 'a'
    Byte 3:    (n-1) high byte
    Byte 4:    (n-1) low byte
    Byte 5:    checksum = hi ^ lo ^ 0x55
    Byte 6+:   R, G, B  per LED
*/

#include <FastLED.h>

#define DATA_PIN    4       // ← GPIO pin — check your WLED config
#define NUM_LEDS    74
#define LED_TYPE    WS2812B
#define COLOR_ORDER GRB
#define BAUD_RATE   1000000  // 1 Mbaud → ~1.9ms per packet (vs 16ms at 115200)

CRGB leds[NUM_LEDS];

// Parser state
enum State { WAIT_A, WAIT_D, WAIT_A2, HEADER, DATA };
State   state     = WAIT_A;
int     ledCount  = 0;   // number of LEDs in this packet
int     ledIdx    = 0;   // current LED being written
int     channel   = 0;   // 0=R 1=G 2=B
uint8_t r, g;

void setup() {
  Serial.begin(BAUD_RATE);
  FastLED.addLeds<LED_TYPE, DATA_PIN, COLOR_ORDER>(leds, NUM_LEDS);
  FastLED.setBrightness(255);
  FastLED.clear();
  FastLED.show();

  // Brief startup flash so you can see the strip is working
  for (int i = 0; i < NUM_LEDS; i++) {
    leds[i] = CRGB(20, 10, 0);
  }
  FastLED.show();
  delay(300);
  FastLED.clear();
  FastLED.show();
}

void loop() {
  while (Serial.available()) {
    uint8_t b = Serial.read();

    switch (state) {
      case WAIT_A:
        if (b == 'A') state = WAIT_D;
        break;

      case WAIT_D:
        state = (b == 'd') ? WAIT_A2 : WAIT_A;
        break;

      case WAIT_A2:
        state = (b == 'a') ? HEADER : WAIT_A;
        break;

      case HEADER: {
        // Collect 3 header bytes: hi, lo, checksum
        static uint8_t hdr[3];
        static int     hdrIdx = 0;
        hdr[hdrIdx++] = b;
        if (hdrIdx == 3) {
          hdrIdx = 0;
          uint8_t hi = hdr[0], lo = hdr[1], chk = hdr[2];
          if ((hi ^ lo ^ 0x55) == chk) {
            ledCount = ((hi << 8) | lo) + 1;
            ledIdx   = 0;
            channel  = 0;
            state    = DATA;
          } else {
            state = WAIT_A;  // bad checksum
          }
        }
        break;
      }

      case DATA:
        if (channel == 0)      r = b;
        else if (channel == 1) g = b;
        else {
          if (ledIdx < NUM_LEDS) {
            leds[ledIdx] = CRGB(r, g, b);
          }
          ledIdx++;
          if (ledIdx >= ledCount) {
            FastLED.show();
            state = WAIT_A;
          }
        }
        channel = (channel + 1) % 3;
        break;
    }
  }
}
