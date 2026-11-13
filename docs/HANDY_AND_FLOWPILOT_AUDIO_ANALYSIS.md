# Handy & FlowPilot Audio Architecture Dissection & Issue Tracking

This document records the architectural dissection of **Handy** ([cjpais/handy](https://github.com/cjpais/handy)), cross-references it with the native Windows voice pipeline in **FlowPilot** ([flowpilot](file:///D:/Software%20by%20Abi/flowpilot)), and details the concrete hardening patterns adapted into **CartMate** ([CartMate](file:///C:/Users/user/cartmate)).

---

## 1. Comparative Architecture Overview

| Dimension | Handy (`cjpais/handy`) | FlowPilot (`flowpilot`) | CartMate (`cartmate`) |
| :--- | :--- | :--- | :--- |
| **Primary Domain** | Desktop Speech-to-Text Dictation | Desktop Voice Intelligence & Text Injection | Ephemeral 10-Minute Voice Companion (WebRTC) |
| **Core Technology** | Tauri v2 + Rust (`rodio`, `cpal`, `whisper.cpp`) | PySide6 (Qt6) + Python (`faster-whisper`, `sounddevice`, `onnxruntime`) | FastAPI + React (WebRTC, WebSocket, Web Audio API) |
| **Audio Pipeline** | Ring buffer PCM -> VAD chunking -> GGUF model | Ring buffer float32 -> Silero VAD -> CTranslate2 | WebRTC MediaStream -> AudioContext Analyser -> STUN/TURN relay |
| **Device Selection** | Device name matching via `cpal` | Persistent PnP DevNode resolution via Win32 `CfgMgr32` | `navigator.mediaDevices.enumerateDevices()` + `setSinkId()` |
| **Silence Handling** | Digital silence frame counter (`MicrophoneSilent`) | RMS energy threshold + Silero VAD probability | Logarithmic frequency power tracking + live alert badge |
| **Visualizer** | 9-bar logarithmic FFT with power curve & spatial filter | Floating companion overlay with dynamic RMS pulse | 9-bar logarithmic FFT with SVG power curve in HUD |
| **Audio Feedback** | WAV earcons via `rodio` | Audio ducker + synthesized feedback chimes | Pure Web Audio API synthesized oscillators (zero external assets) |

---

## 2. Issue Tracking & Individual Technical Dissections

### Issue 1: Digital Silence & Hardware Mute Trap
- **Handy Issue (#2486):** *"fix: say so when the microphone sends only silence"*. When hardware mute switches or OS microphone permissions cut off audio, `getUserMedia()` / `cpal` streams uninterrupted streams of pure zeros (`0.0`). The system showed an active recording state with a flat visualizer, leaving users confused whether the model was frozen.
- **FlowPilot Solution:** In `engine/audio_capture.py` and `engine/vad.py`, FlowPilot monitors RMS energy over a sliding window alongside Silero VAD. If frames remain below 0.001 RMS while unmuted, the state machine flags `AudioInputSilence`.
- **CartMate Adaptation & Test:**
  - In [VoiceCallHUD.tsx](file:///C:/Users/user/cartmate/frontend/src/components/VoiceCallHUD.tsx), added `isMicSilent` tracking: if total FFT frequency power across all 9 bins is `< 10` for > 90 consecutive animation frames (~1.5 seconds) while unmuted, a live accessible alert badge (`role="alert"`) displays `vcopy.micSilentWarning`.
  - **Individual Test Verification:** Verified in Playwright E2E suite (`qa/tests/pods-and-voice.spec.ts`) that the alert badge renders programmatically across all 4 supported locales (`pl`, `en`, `uk`, `ru`).

---

### Issue 2: Bluetooth / AirPods Profile Switching & Dropouts
- **Handy Issues (#2472, #2387, #2446):**
  - #2472: *"[BUG] AirPods mic goes silent a few seconds into a recording (macOS)"*.
  - #2387: *"[BUG] Linux: Bluetooth headset mic stalls or records silence when WirePlumber switches A2DP -> HFP on stream open"*.
  - When output audio plays while an input stream opens, Bluetooth headsets negotiate bidirectional SCO/HFP profiles, causing audio stalls or complete microphone dropouts.
- **FlowPilot Solution:** Feature 28 ([0002-persistent-audio-input-identity.md](file:///D:/Software%20by%20Abi/flowpilot/docs/specs/0002-persistent-audio-input-identity.md)) uses Windows `CfgMgr32` and registry devnodes to disambiguate endpoints across host APIs (WASAPI vs DirectSound) and defers recorder switching during active speech frames to prevent device negotiation stalls.
- **CartMate Adaptation & Test:**
  - In `VoiceCallHUD.tsx`, `toggleSpeakerphone` isolates output routing via HTMLMediaElement `setSinkId()` without touching or recreating `localStreamRef.current`. By never re-requesting `getUserMedia` during an output switch, Bluetooth input audio remains locked and uninterrupted.
  - **Individual Test Verification:** Exercised in [pods-and-voice.spec.ts](file:///C:/Users/user/cartmate/qa/tests/pods-and-voice.spec.ts#L190-L200) across Desktop Chromium and Mobile Chrome emulation.

---

### Issue 3: Asynchronous Dequeue Latency vs Event Timestamps
- **Handy Issue (#2097):** *"fix(shortcut): classify tap vs hold by key event time, not dequeue time"*. When input queues experienced high load or background thread scheduling latency, tap-to-talk was frequently misclassified as long push-to-talk holds.
- **FlowPilot Solution:** Uses Win32 `GetMessageTime()` hardware timestamps rather than Python thread dequeue timestamps in `engine/hotkey_service.py`.
- **CartMate Adaptation & Test:**
  - Implemented monotonic call session guards (`callSessionRef.current = ++callSessionRef.current`). All asynchronous WebRTC callbacks (`getUserMedia`, `onicecandidate`, `ontrack`, `onconnectionstatechange`) verify that `sessionId === callSessionRef.current` before updating state, preventing delayed network or media callbacks from corrupting call transitions.
  - **Individual Test Verification:** Stress tested under rapid match, hangup, and rating sequences in `pods-and-voice.spec.ts`.

---

### Issue 4: Process Crash & Worker Poisoning Recovery
- **Handy Issue (#2485):** *"fix: replace the transcription worker after a backend error"*. When an underlying whisper worker crashed or ran out of VRAM/memory, subsequent transcription requests hung indefinitely.
- **FlowPilot Solution:** `engine/orchestrator.py` implements a watchdog monitor that catches worker crashes and automatically respawns the inference worker.
- **CartMate Adaptation & Test:**
  - Implemented WebRTC connection failure state recovery in `VoiceCallHUD.tsx`: when connection state enters `failed` or `closed`, the HUD terminates media immediately, clears timers, and returns the user to the lobby with appropriate error notices.
  - WebRTC signaling backend features a 12s disconnect grace timer and auto-sweeper in `voice_manager.py`.

---

### Issue 5: Punctuation Hallucination on Low-SNR Audio
- **Handy Issue (#2434):** *"fix: skip pasting a transcript that is only a period"*. Speech models frequently hallucinate isolated periods (`.`) or commas when fed background noise or near-silence.
- **FlowPilot Solution:** Spec 0004 FactGuard (`engine/writing_intelligence.py`) strips standalone punctuation and phantom tokens, refusing to inject zero-content edits.
- **CartMate Adaptation & Test:**
  - Chat and telemetry pipelines enforce strict string length bounds, PII scrubbing via `sanitize_analytics_properties()`, and empty-message rejection.

---

### Issue 6: Overlay Focus Stealing & Context Menu Glitches
- **Handy Issue (#2403):** *"fix(overlay): disable WebView2 context menu on the recording overlay"*. Right-clicking the floating overlay opened the Windows context menu, stealing input focus.
- **FlowPilot Solution:** Floating HUD windows explicitly set Win32 `WS_EX_NOACTIVATE (0x08000000)` and `Qt.WindowDoesNotAcceptFocus`.
- **CartMate Adaptation & Test:**
  - Accessible focus management via `useDialogFocus` hook: traps keyboard focus inside active modals, restores focus to triggering elements on dismiss, and binds the Escape key (`RT-12` test passed).

---

### Issue 7: Perceptual FFT Logarithmic Speech Visualizer
- **Handy Pattern:** `audio_toolkit/audio/visualizer.rs`:
  - 9 logarithmic frequency bands matching human speech hearing (`[1..2]`, `[2..4]`, ..., `[37..48]`).
  - Calibrated dynamic range (`-68 dB` to `-25 dB`) with `Math.pow(lvl, 0.7)` power curve shaping.
  - Dual-stage smoothing: exponential temporal smoothing (`0.7 * prev + 0.3 * target`) and 3-point spatial smoothing (`0.7 * center + 0.15 * left + 0.15 * right`).
- **CartMate Adaptation & Test:**
  - Ported directly to `VoiceCallHUD.tsx` in `startAudioAnalyser()`. The visualizer renders smoothly without jagged spikes or static deadbands.

---

### Issue 8: Tactile Audio Feedback Earcons
- **Handy Pattern:** `audio_feedback.rs` uses `rodio` to play feedback audio for recording start/stop.
- **CartMate Adaptation & Test:**
  - Built pure synthetic Web Audio earcons (`playAudioCue`) using standard `AudioContext` sine and triangle oscillators:
    - **Connect:** Rising major-third chime (`523 Hz -> 659 Hz`, 300ms soft exponential decay).
    - **Disconnect:** Gentle descending chime (`659 Hz -> 440 Hz`, 320ms soft exponential decay).
    - **Mute / Unmute:** Clean dual-frequency tactile click (`320 Hz / 640 Hz`, 80ms decay).
  - Requires zero audio asset downloads, eliminating network latency and bundle overhead.

---

## 3. Verification Matrix

| Verification Target | Test Suite | Result |
| :--- | :--- | :--- |
| **Backend & Ops Unit / Contract Tests** | `pytest -p no:cacheprovider -q` | **250 passed, 0 failed** (92.17s) |
| **Database Isolation Guard** | Root & Backend `conftest.py` + `storage.py` | **Verified: 0 byte drift on `cartmate.db`** |
| **Voice Backend Unit Suite** | `backend/test_voice_calls.py` | **12 passed, 0 failed** (6.10s) |
| **Playwright Operator-Pilot Suite** | `qa/playwright.operator-pilot.config.ts` | **16 passed, 0 failed** (1.9m) |
| **Playwright Pods & Voice Suite** | `qa/tests/pods-and-voice.spec.ts` | **6 passed, 0 failed** (22.9s) |
| **Playwright Staging No-Demo Suite** | `qa/playwright.no-demo.config.ts` | **4 passed, 0 failed** (24.3s) |
| **Diagnostic Security Probes** | 9 independent security probes | **All 9 exit 0** |
| **Frontend Code Quality** | `npx oxlint` (29 files) | **0 errors, 0 warnings** (193ms) |
| **Frontend Production Build** | `tsc -b && vite build` | **Clean build** (1.55s) |
