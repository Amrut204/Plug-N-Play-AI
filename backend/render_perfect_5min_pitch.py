import os
import time
import numpy as np
from PIL import Image, ImageSequence
import imageio.v3 as iio

artifact_dir = r"C:\Users\dongr\.gemini\antigravity-ide\brain\0cbbf9b9-7086-4f3a-9193-adc74d8984cd"
output_mp4 = r"C:\vscode\Plug-N-Play-RAG\Plug_N_Play_AI_5Min_Pitch_Demo.mp4"
target_w, target_h = 1920, 1080
fps = 10  # Standard 10 FPS -> 300s = 3000 frames

def get_image(filename):
    p = os.path.join(artifact_dir, filename)
    if not os.path.exists(p):
        print(f"Warning: {filename} not found")
        return Image.new("RGB", (target_w, target_h), (13, 17, 23))
    im = Image.open(p).convert("RGB")
    if im.size != (target_w, target_h):
        im = im.resize((target_w, target_h), Image.Resampling.BILINEAR)
    return im

def get_animated_frames(filename):
    p = os.path.join(artifact_dir, filename)
    if not os.path.exists(p):
        return [get_image(filename)]
    im = Image.open(p)
    frames = []
    if getattr(im, "is_animated", False):
        for f in ImageSequence.Iterator(im):
            rgb = f.convert("RGB")
            if rgb.size != (target_w, target_h):
                rgb = rgb.resize((target_w, target_h), Image.Resampling.BILINEAR)
            frames.append(rgb)
    else:
        frames.append(get_image(filename))
    return frames

def generate_smooth_crossfade(img_from, img_to, count):
    arr1 = np.array(img_from, dtype=np.float32)
    arr2 = np.array(img_to, dtype=np.float32)
    frames = []
    for i in range(count):
        alpha = i / float(count)
        blended = (1.0 - alpha) * arr1 + alpha * arr2
        frames.append(np.clip(blended, 0, 255).astype(np.uint8))
    return frames

def generate_still_sequence(img, count):
    arr = np.array(img, dtype=np.uint8)
    return [arr] * count

def generate_animated_sequence_with_hold(filename, target_count):
    raw_frames = get_animated_frames(filename)
    if not raw_frames:
        return [np.zeros((target_h, target_w, 3), dtype=np.uint8)] * target_count
    
    result = []
    # Play raw frames at 1x speed
    for f in raw_frames:
        if len(result) < target_count:
            result.append(np.array(f, dtype=np.uint8))
    
    # If target_count > raw_frames, naturally hold the final completed state!
    last_frame = result[-1] if result else np.array(raw_frames[-1], dtype=np.uint8)
    while len(result) < target_count:
        result.append(last_frame)
    
    return result[:target_count]

print("=== Assembling Natural 1x Paced 5-Minute Pitch Video ===")
print("Total Target Duration: 300.0s (5:00 minutes) at 10.0 FPS = 3,000 frames")

all_frames = []

# -------------------------------------------------------------
# SCENE 1: Landing Page & Security Metrics (0:00 - 0:45 | 450 frames)
# -------------------------------------------------------------
print("Rendering Scene 1: Landing Page & Security Metrics (45s)...")
img_top = get_image("scene1_landing_top_1788581405103.png")
img_metrics = get_image("scene1_security_metrics_1788581417471.png")
img_dual = get_image("scene1_dual_engine_1788581428635.png")

# 0:00 - 0:15 (150 frames): Hero view + transition
all_frames.extend(generate_still_sequence(img_top, 120))
all_frames.extend(generate_smooth_crossfade(img_top, img_metrics, 30))

# 0:15 - 0:30 (150 frames): Security metrics + transition
all_frames.extend(generate_still_sequence(img_metrics, 120))
all_frames.extend(generate_smooth_crossfade(img_metrics, img_dual, 30))

# 0:30 - 0:45 (150 frames): Dual-engine architecture + transition to auth
img_auth = get_image("scene2_auth_modal_1788581469931.png")
all_frames.extend(generate_still_sequence(img_dual, 130))
all_frames.extend(generate_smooth_crossfade(img_dual, img_auth, 20))

# -------------------------------------------------------------
# SCENE 2: Authentication & Workspace Dashboard (0:45 - 1:20 | 350 frames)
# -------------------------------------------------------------
print("Rendering Scene 2: Authentication & Workspace Dashboard (35s)...")
# 0:45 - 1:02 (170 frames): Google Auth live walkthrough
all_frames.extend(generate_animated_sequence_with_hold("verify_google_auth_1788542705923.webp", 170))

# 1:02 - 1:20 (180 frames): Account Center & Dashboard telemetry
all_frames.extend(generate_animated_sequence_with_hold("verify_account_center_1788449535883.webp", 180))

# -------------------------------------------------------------
# SCENE 3: Agent Studio & Multi-DB Federation (1:20 - 2:35 | 750 frames)
# -------------------------------------------------------------
print("Rendering Scene 3: Agent Studio & Multi-DB Federation (75s)...")
img_step1 = get_image("scene3_step1_identity_1788581531392.png")
img_multidb = get_image("scene3_multidb_federation_card_1788581572162.png")
img_db_conn = get_image("scene3_db_connections_1788581555093.png")
img_step4 = get_image("scene3_step4_deploy_1788581593217.png")

# Step 1 Identity (15s = 150 frames)
all_frames.extend(generate_still_sequence(img_step1, 130))
all_frames.extend(generate_smooth_crossfade(img_step1, img_multidb, 20))

# Step 2 Knowledge & Multi-DB Federation (35s = 350 frames)
all_frames.extend(generate_still_sequence(img_multidb, 160))
all_frames.extend(generate_smooth_crossfade(img_multidb, img_db_conn, 20))
all_frames.extend(generate_still_sequence(img_db_conn, 150))
all_frames.extend(generate_smooth_crossfade(img_db_conn, img_step4, 20))

# Step 3 & Step 4 Guardrails and Deployment (25s = 250 frames)
all_frames.extend(generate_still_sequence(img_step4, 250))

# -------------------------------------------------------------
# SCENE 4: Ambient Browser Action Relays (2:35 - 3:20 | 450 frames)
# -------------------------------------------------------------
print("Rendering Scene 4: Ambient Browser Action Relays (45s)...")
all_frames.extend(generate_animated_sequence_with_hold("verify_action_flow_1788434111788.webp", 450))

# -------------------------------------------------------------
# SCENE 5: Dedicated Zero-SQL Platform Copilot (3:20 - 4:20 | 600 frames)
# -------------------------------------------------------------
print("Rendering Scene 5: Dedicated Zero-SQL Platform Copilot (60s)...")
img_copilot_open = get_image("scene4_copilot_open_1788581616517.png")
img_copilot_resp1 = get_image("scene4_copilot_response1_1788581647262.png")
img_copilot_resp2 = get_image("scene4_copilot_response2_1788581668816.png")

# Copilot opens (8s = 80 frames)
all_frames.extend(generate_still_sequence(img_copilot_open, 60))
all_frames.extend(generate_smooth_crossfade(img_copilot_open, img_copilot_resp1, 20))

# Copilot answers "What is my workspace name?" (22s = 220 frames)
all_frames.extend(generate_still_sequence(img_copilot_resp1, 200))
all_frames.extend(generate_smooth_crossfade(img_copilot_resp1, img_copilot_resp2, 20))

# Copilot answers "Why is there an option to add another DB URL?" streaming (30s = 300 frames)
all_frames.extend(generate_still_sequence(img_copilot_resp2, 300))

# -------------------------------------------------------------
# SCENE 6: Universal 1-Line Embed & Conclusion (4:20 - 5:00 | 400 frames)
# -------------------------------------------------------------
print("Rendering Scene 6: Universal 1-Line Embed & Conclusion (40s)...")
img_embed = get_image("scene5_embed_snippet_1788581697948.png")
img_conclusion = get_image("scene5_conclusion_1788581708364.png")

# Embed code snippet (20s = 200 frames)
all_frames.extend(generate_still_sequence(img_embed, 180))
all_frames.extend(generate_smooth_crossfade(img_embed, img_conclusion, 20))

# Final clean wrap-up view (20s = 200 frames)
all_frames.extend(generate_still_sequence(img_conclusion, 200))

# Final verification of frame count
total_frames = len(all_frames)
duration_sec = total_frames / fps
print(f"Total compiled frames: {total_frames} ({duration_sec:.1f}s / {duration_sec/60:.2f} mins)")

print(f"Encoding Full HD 1080p MP4 to {output_mp4} at {fps} FPS...")
t0 = time.time()
iio.imwrite(
    output_mp4,
    all_frames,
    fps=fps,
    codec="libx264"
)
elapsed = time.time() - t0
file_size = os.path.getsize(output_mp4)
print(f"SUCCESS! Rendered in {elapsed:.1f}s. Output size: {file_size} bytes ({file_size / (1024*1024):.2f} MB)")
