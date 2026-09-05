import os
import time
import numpy as np
from PIL import Image, ImageSequence
import imageio.v3 as iio

artifact_dir = r"C:\Users\dongr\.gemini\antigravity-ide\brain\0cbbf9b9-7086-4f3a-9193-adc74d8984cd"
output_mp4 = r"C:\vscode\Plug-N-Play-RAG\Plug_N_Play_AI_5Min_Pitch_Demo.mp4"
target_w, target_h = 1920, 1080
fps = 6  # 6 frames per second -> 300s = 1800 frames

def load_frames_from_file(filename, target_duration_sec):
    path = os.path.join(artifact_dir, filename)
    target_frames_count = int(target_duration_sec * fps)
    if not os.path.exists(path):
        print(f"Warning: File not found {path}")
        return []
    
    im = Image.open(path)
    raw_frames = []
    if getattr(im, "is_animated", False):
        for f in ImageSequence.Iterator(im):
            rgb = f.convert("RGB")
            if rgb.size != (target_w, target_h):
                rgb = rgb.resize((target_w, target_h), Image.Resampling.BILINEAR)
            raw_frames.append(np.array(rgb))
    else:
        rgb = im.convert("RGB")
        if rgb.size != (target_w, target_h):
            rgb = rgb.resize((target_w, target_h), Image.Resampling.BILINEAR)
        raw_frames = [np.array(rgb)]

    # Interpolate / stretch or loop to match exact target duration
    if len(raw_frames) == 1:
        return [raw_frames[0]] * target_frames_count
    elif len(raw_frames) < target_frames_count:
        # Repeat or step-duplicate
        indices = np.linspace(0, len(raw_frames) - 1, target_frames_count).astype(int)
        return [raw_frames[i] for i in indices]
    else:
        indices = np.linspace(0, len(raw_frames) - 1, target_frames_count).astype(int)
        return [raw_frames[i] for i in indices]

# Timeline specification: Total 300 seconds (5:00 minutes)
timeline = [
    # Scene 1: Landing Page & Security Metrics (0:00 - 0:45 = 45s)
    ("scene1_landing_top_1788581405103.png", 12),
    ("scene1_security_metrics_1788581417471.png", 15),
    ("scene1_dual_engine_1788581428635.png", 18),

    # Scene 2: Authentication & Workspace Modal (0:45 - 1:20 = 35s)
    ("verify_google_auth_1788542705923.webp", 18),
    ("verify_account_center_1788449535883.webp", 17),

    # Scene 3: Agent Studio & Multi-DB Federation (1:20 - 2:35 = 75s)
    ("scene3_step1_identity_1788581531392.png", 15),
    ("scene3_multidb_federation_card_1788581572162.png", 25),
    ("verify_agent_studio_1788434253125.webp", 20),
    ("scene3_step4_deploy_1788581593217.png", 15),

    # Scene 4: Action Execution & Ambient Browser Relays (2:35 - 3:20 = 45s)
    ("verify_action_flow_1788434111788.webp", 45),

    # Scene 5: Dedicated Zero-SQL Platform Copilot (3:20 - 4:20 = 60s)
    ("scene4_copilot_open_1788581616517.png", 10),
    ("verify_copilot_1788575471617.webp", 25),
    ("verify_copilot_tech_1788575506925.webp", 25),

    # Scene 6: Universal 1-Line Embed Script & Conclusion (4:20 - 5:00 = 40s)
    ("scene5_embed_snippet_1788581697948.png", 20),
    ("scene5_conclusion_1788581708364.png", 20),
]

print("Starting 5-Minute Master Pitch Video Assembly...")
total_time = sum(t[1] for t in timeline)
print(f"Target duration: {total_time}s ({total_time // 60}:{total_time % 60:02d}) at {fps} fps")

all_video_frames = []
for filename, duration in timeline:
    print(f"Loading {filename} for {duration}s ({int(duration * fps)} frames)...")
    frames = load_frames_from_file(filename, duration)
    all_video_frames.extend(frames)

print(f"Total compiled frames: {len(all_video_frames)}. Rendering to {output_mp4}...")
t0 = time.time()
iio.imwrite(output_mp4, all_video_frames, fps=fps, codec="libx264")
elapsed = time.time() - t0
print(f"SUCCESS! Rendered in {elapsed:.1f}s. Output size: {os.path.getsize(output_mp4)} bytes")
