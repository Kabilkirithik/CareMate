#!/usr/bin/env python3
"""
sender.py — TCP server that streams a pre-encoded 24kHz .opus file to ESP32.
The ESP32 is the TCP CLIENT — it connects outward to this script.
This script is the TCP SERVER — it binds, listens, and streams.
Start this BEFORE the ESP32 boots. The ESP32 retries every 2 s so
order only matters for the first connection attempt.
Protocol (matches ESP32 firmware exactly):
  [uint16 big-endian packet length] [raw Opus packet bytes]
Audio quality on the sender side:
  - Zero re-encode: OGG pages are demuxed and raw Opus packets sent as-is.
    Re-encoding would introduce generation loss; passthrough avoids that.
  - Real-time pacing: packets are sent at exactly 20 ms intervals so the
    ESP32 ring buffer stays evenly filled — no bursts, no starvation.
  - Pre-buffering: we send PREBUFFER_FRAMES frames before starting the
    real-time clock, giving the ESP32 ring a head start and eliminating
    the initial underrun click.
  - Fallback re-encode path: if OGG demux fails (unusual container,
    truncated file) the file is decoded to PCM and re-encoded cleanly
    via opuslib with VOIP mode + FEC enabled.
Requirements:
  pip install pyogg opuslib   (opuslib only needed for re-encode fallback)
Usage:
  python sender.py --file audio.opus --port 5005
  python sender.py --file audio.opus --port 5005 --loop
  python sender.py --file audio.opus --port 5005 --loop --gap 800
"""
import argparse
import socket
import struct
import sys
import time
# ---------------------------------------------------------------------------
# Constants — must match ESP32 firmware
# ---------------------------------------------------------------------------
SAMPLE_RATE   = 24000
CHANNELS      = 1
FRAME_SAMPLES = 480          # 20 ms @ 24 kHz
FRAME_DUR_S   = 0.020        # seconds per frame
# How many frames to pre-buffer before real-time pacing begins.
# 10 frames = 200 ms head start — fills the ESP32 ring before audio task
# starts draining, eliminating the initial underrun click.
PREBUFFER_FRAMES = 10

# ---------------------------------------------------------------------------
# OGG / Opus demux  (zero re-encode path)
# ---------------------------------------------------------------------------
def iter_opus_packets(filepath: str):
    """
    Yield raw Opus packets from an OGG-encapsulated .opus file.
    Tries the native OGG page parser first (no quality loss).
    Falls back to pyogg decode + opuslib re-encode if parsing fails
    (e.g. file is truncated or uses unusual page sizes).
    """
    try:
        packets = list(_ogg_demux(filepath))
        if packets:
            print(f"  [demux] OGG passthrough — {len(packets)} packets, zero re-encode")
            yield from packets
            return
    except Exception as e:
        print(f"  [demux] OGG parser error: {e} — falling back to re-encode")
    yield from _reencode_fallback(filepath)

def _ogg_demux(filepath: str):
    """
    Parse OGG pages (RFC 3533) and yield raw Opus audio packets.
    Skips the two mandatory Opus header pages (OpusHead + OpusTags).
    OGG page layout:
      4B  "OggS" capture pattern
      1B  stream_structure_version  (always 0)
      1B  header_type_flag
      8B  absolute_granule_position
      4B  stream_serial_number
      4B  page_sequence_no
      4B  CRC checksum
      1B  number_page_segments
      NB  lacing_values             (N = number_page_segments bytes)
      …   segment data
    """
    header_pages_seen = 0
    with open(filepath, 'rb') as f:
        while True:
            # ---- sync on "OggS" ----
            sync = f.read(4)
            if len(sync) < 4:
                break
            if sync != b'OggS':
                # lost sync — scan forward byte by byte
                buf = sync
                while True:
                    b = f.read(1)
                    if not b:
                        return
                    buf = buf[1:] + b
                    if buf == b'OggS':
                        break
            # ---- fixed page header (23 bytes after capture pattern) ----
            hdr = f.read(23)
            if len(hdr) < 23:
                break
            n_segs = hdr[22]           # number_page_segments
            lace   = f.read(n_segs)   # lacing_values
            if len(lace) < n_segs:
                break
            # ---- read all segment data for this page ----
            page_data = bytearray()
            for seg_len in lace:
                chunk = f.read(seg_len)
                if len(chunk) < seg_len:
                    return
                page_data += chunk
            # Skip OpusHead (page 0) and OpusTags (page 1)
            if header_pages_seen < 2:
                header_pages_seen += 1
                continue
            # ---- reassemble packets from lacing ----
            # A packet ends when a segment is < 255 bytes.
            # A segment of exactly 255 bytes means the packet continues
            # into the next segment (or next page).
            packets = []
            pkt    = bytearray()
            offset = 0
            for seg_len in lace:
                pkt   += page_data[offset: offset + seg_len]
                offset += seg_len
                if seg_len < 255:
                    if pkt:
                        packets.append(bytes(pkt))
                    pkt = bytearray()
            if pkt:
                # Packet spans into next page — yield as-is (rare for TTS)
                packets.append(bytes(pkt))
            yield from packets

def _reencode_fallback(filepath: str):
    """
    Decode the .opus file to PCM with pyogg, then re-encode frame by frame
    using opuslib in VOIP mode with FEC enabled.
    Quality note: one generation of re-encode at 32 kbps is inaudible for
    TTS. The important thing is VOIP application mode (voice-optimised
    psychoacoustic model) and inband FEC for WiFi robustness.
    """
    try:
        import pyogg
        import opuslib
    except ImportError:
        sys.exit("Install pyogg and opuslib:  pip install pyogg opuslib")
    print("  [demux] Re-encode fallback: decoding to PCM ...")
    of    = pyogg.OpusFile(filepath)
    pcm   = bytes(of.buffer)
    sr    = of.frequency
    chans = of.channels
    if sr != SAMPLE_RATE:
        sys.exit(f"File sample rate {sr} Hz does not match firmware {SAMPLE_RATE} Hz. "
                 "Re-encode your file at 24000 Hz.")
    enc = opuslib.Encoder(SAMPLE_RATE, chans, opuslib.APPLICATION_VOIP)
    # VOIP application mode: enables speech-optimised psychoacoustics,
    # comfort noise generation, and DTX (discontinuous transmission).
    enc.inband_fec       = True   # embed FEC — helps ESP32 on WiFi packet loss
    enc.packet_loss_perc = 5      # target FEC for 5% loss environment
    enc.bitrate          = 32000  # 32 kbps mono TTS — transparent quality
    frame_bytes = FRAME_SAMPLES * chans * 2  # 16-bit PCM
    offset      = 0
    count       = 0
    while offset + frame_bytes <= len(pcm):
        frame   = pcm[offset: offset + frame_bytes]
        offset += frame_bytes
        count  += 1
        yield enc.encode(frame, FRAME_SAMPLES)
    print(f"  [demux] Re-encoded {count} frames")

# ---------------------------------------------------------------------------
# Silence packet
# ---------------------------------------------------------------------------
def silence_packet() -> bytes:
    """
    Minimal valid Opus bitstream packet representing digital silence.
    TOC byte 0xF8: CELT-only, 1 frame, mono, 20 ms.
    One 0x00 payload byte satisfies the minimum packet size requirement.
    Sending this instead of disconnecting keeps the decoder state warm
    so it can apply PLC smoothly when audio resumes.
    """
    return bytes([0xF8, 0x00])

# ---------------------------------------------------------------------------
# TCP server + streaming
# ---------------------------------------------------------------------------
def send_frame(conn: socket.socket, pkt: bytes):
    """Send one framed Opus packet: [uint16 BE length] [data]."""
    conn.sendall(struct.pack('>H', len(pkt)) + pkt)

def stream_to_client(conn: socket.socket, packets: list, loop: bool, gap_ms: int):
    """
    Stream all packets to a connected ESP32 client.
    Timing strategy:
      Phase 1 — Pre-buffer: send PREBUFFER_FRAMES frames as fast as TCP
                allows. This fills the ESP32 ring buffer so the audio task
                has data immediately when it starts draining.
      Phase 2 — Real-time pacing: send each subsequent frame exactly 20 ms
                after the previous one, maintaining a steady pipeline.
    This prevents two failure modes:
      • Underrun (gap/click): caused by sending too slowly.
      • Overrun (distortion): caused by sending faster than playback,
        overflowing the ESP32 ring buffer.
    """
    silence = silence_packet()
    pass_num = 0
    while True:
        pass_num += 1
        total   = len(packets)
        # ---- Phase 1: pre-buffer ----
        pre = min(PREBUFFER_FRAMES, total)
        for i in range(pre):
            send_frame(conn, packets[i])
        # ---- Phase 2: real-time pacing for remaining frames ----
        # Anchor the clock AFTER the pre-buffer burst so pacing is
        # relative to when real-time playback begins on the ESP32.
        t0 = time.monotonic()
        for i in range(pre, total):
            send_frame(conn, packets[i])
            frame_idx = i - pre + 1
            expected  = t0 + frame_idx * FRAME_DUR_S
            sleep     = expected - time.monotonic()
            if sleep > 0.001:   # skip sub-ms sleeps (scheduling overhead)
                time.sleep(sleep)
        elapsed = time.monotonic() - t0 + pre * FRAME_DUR_S
        print(f"  Pass {pass_num} complete — {total} frames, {elapsed:.2f} s")
        if not loop:
            break
        # ---- Inter-loop silence gap ----
        # Keeps decoder state warm and lets the ESP32 ring drain before
        # the next pass starts. The noise gate on the ESP32 will mute
        # these silence packets, so no audible noise during the gap.
        gap_frames = gap_ms // int(FRAME_DUR_S * 1000)
        t_gap = time.monotonic()
        for j in range(gap_frames):
            send_frame(conn, silence)
            expected = t_gap + (j + 1) * FRAME_DUR_S
            sleep    = expected - time.monotonic()
            if sleep > 0.001:
                time.sleep(sleep)

def serve(filepath: str, port: int, loop: bool, gap_ms: int):
    # ---- Load and demux once ----
    print(f"Loading {filepath} ...")
    packets = list(iter_opus_packets(filepath))
    if not packets:
        sys.exit("No Opus packets found — is this a valid .opus / .ogg file?")
    duration = len(packets) * FRAME_DUR_S
    print(f"Ready: {len(packets)} packets, ~{duration:.1f} s audio")
    # ---- Bind TCP server socket ----
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('0.0.0.0', port))
    srv.listen(1)
    print(f"Listening on 0.0.0.0:{port}  — waiting for ESP32 ...")
    print(f"(Set SERVER_IP to your Mac's IP in main.cpp)\n")
    # ---- Accept loop — survives ESP32 reboots ----
    while True:
        conn, addr = srv.accept()
        # TCP_NODELAY: disable Nagle algorithm — send each frame immediately
        # without waiting to coalesce. Critical for 20 ms real-time pacing.
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        print(f"ESP32 connected from {addr[0]}:{addr[1]}")
        try:
            stream_to_client(conn, packets, loop, gap_ms)
            print("Stream finished. Waiting for next connection ...")
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            print(f"ESP32 disconnected ({e.__class__.__name__}: {e})")
            print("Waiting for reconnect ...")
        finally:
            conn.close()

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="Stream a pre-encoded 24kHz .opus file to ESP32 over TCP"
    )
    ap.add_argument('--file', required=True,
                    help='Path to .opus file (must be 24000 Hz, mono)')
    ap.add_argument('--port', type=int, default=5005,
                    help='TCP port to listen on (default: 5005)')
    ap.add_argument('--loop', action='store_true',
                    help='Loop the file continuously')
    ap.add_argument('--gap', type=int, default=500,
                    help='Silence gap between loops in milliseconds (default: 500)')
    args = ap.parse_args()
    serve(args.file, args.port, args.loop, args.gap)

def stream_to_esp32(filepath: str, port: int = 5005, timeout: int = 5, retries: int = 3):
    """
    Simple wrapper for backend integration.
    Streams one audio file to ESP32 and returns.
    Retries up to `retries` times if ESP32 doesn't connect in time.

    Args:
        filepath: Path to .opus file
        port: TCP port (default: 5005)
        timeout: Seconds to wait per attempt (default: 5)
        retries: Number of connection attempts (default: 3)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"[ESP32] Loading {filepath}...")
        packets = list(iter_opus_packets(filepath))
        if not packets:
            print("[ESP32] No Opus packets found")
            return False

        duration = len(packets) * FRAME_DUR_S
        print(f"[ESP32] Ready: {len(packets)} packets, ~{duration:.1f}s")

    except Exception as e:
        print(f"[ESP32] Failed to load file: {e}")
        return False

    for attempt in range(1, retries + 1):
        print(f"[ESP32] Attempt {attempt}/{retries} — waiting for ESP32 on port {port}...")
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            srv.bind(('0.0.0.0', port))
            srv.listen(1)
            srv.settimeout(timeout)

            try:
                conn, addr = srv.accept()
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                print(f"[ESP32] ✓ Connected from {addr[0]}:{addr[1]}")

                stream_to_client(conn, packets, loop=False, gap_ms=0)
                print(f"[ESP32] ✓ Stream completed")

                conn.close()
                srv.close()
                return True

            except socket.timeout:
                print(f"[ESP32] Attempt {attempt} timed out after {timeout}s")
                srv.close()

        except OSError as e:
            print(f"[ESP32] Socket error on attempt {attempt}: {e}")
            srv.close()

        if attempt < retries:
            print(f"[ESP32] Retrying in 1s...")
            time.sleep(1)

    print(f"[ESP32] All {retries} attempts failed — audio not streamed")
    return False

if __name__ == '__main__':
    main()