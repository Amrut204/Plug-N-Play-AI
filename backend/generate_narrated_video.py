import os
import asyncio
import subprocess
import edge_tts
import numpy as np
from PIL import Image, ImageSequence
import imageio.v3 as iio
import imageio_ffmpeg

artifact_dir = r"C:\Users\dongr\.gemini\antigravity-ide\brain\0cbbf9b9-7086-4f3a-9193-adc74d8984cd"
work_dir = r"C:\vscode\Plug-N-Play-RAG"
temp_audio_dir = os.path.join(work_dir, "temp_narration")
os.makedirs(temp_audio_dir, exist_ok=True)

ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
target_w, target_h = 1920, 1080
fps = 10

# Natural Azure Voice (Same as Microsoft Clipchamp's Andrew)
VOICE = "en-US-AndrewMultilingualNeural"

scenes = [
    {
        "id": "scene1",
        "title": "Landing Page & Security Metrics",
        "text": (
            "Hello everyone, and welcome to Plug-N-Play AI, an enterprise-grade AI data layer and autonomous agent orchestration platform built for the Razorpay AI Builder 2026 challenge. "
            "Today, modern enterprises face a massive problem: business intelligence is scattered across static documents, PDF guidelines, and live transactional databases. Typical chatbots only search through documents and cannot interact with live databases. At the same time, companies are terrified of AI executing unauthorized writes or corrupting production data. "
            "Plug-N-Play AI solves this challenge with a unified Dual-Engine Architecture and a non-negotiable Zero-Write Guarantee. Notice our three core pillars right here on the landing page: Zero Write Access Required, 100% Abstract Syntax Tree SQL Syntax Safety, and Cryptographic Multi-Tenant Isolation. Organizations can bridge their live data to intelligent agents in under five minutes without migrating records or writing complex backend code."
        ),
        "visual_type": "crossfade_series",
        "images": [
            "scene1_landing_top_1788581405103.png",
            "scene1_security_metrics_1788581417471.png",
            "scene1_dual_engine_1788581428635.png"
        ]
    },
    {
        "id": "scene2",
        "title": "Authentication & Workspace Dashboard",
        "text": (
            "Onboarding is completely frictionless. Clicking into the authentication modal reveals 1-Click Google Authentication alongside email OTP verification, immediately provisioning an isolated tenant workspace. "
            "Inside the workspace dashboard, clients get complete visibility over their usage telemetry, tracking token consumption, active agent quotas, response latencies, and security shield events. Every client workspace is isolated with cryptographic tenant UUIDs, ensuring zero cross-tenant visibility."
        ),
        "visual_type": "animation_series",
        "animations": [
            "verify_google_auth_1788542705923.webp",
            "verify_account_center_1788449535883.webp"
        ]
    },
    {
        "id": "scene3",
        "title": "Agent Studio & Multi-DB Federation",
        "text": (
            "Now, let us explore the heart of our platform: The Agent Studio. Building a custom autonomous agent takes four simple steps. "
            "In Step 1, we define the agent's identity, brand voice, and custom system prompt. "
            "In Step 2, we configure Knowledge Ingestion. Clients can upload unstructured documentation, PDFs, or policies for 384-dimensional vector embedding search. But more importantly, look at our live database connectivity. Clients can connect PostgreSQL, MySQL, SQLite, or MongoDB. "
            "Notice this key architectural innovation: our '+ Add Another Database' option. In modern architectures, customer orders live in PostgreSQL while warehouse inventory lives in MySQL. Our Multi-Database Federation enables the agent to cross-query both databases simultaneously in a single conversation. For organizations with high compliance mandates, our Zero-Knowledge Schema-Only Mode allows clients to paste their SQL DDL schema without ever sharing database connection strings, executing generated queries safely behind their private firewall. "
            "In Step 3, Audience Guardrails enforce strict row-level isolation so users only access their authorized records. And in Step 4, we configure live human support escalation alerts via SMTP email and webhooks."
        ),
        "visual_type": "crossfade_series",
        "images": [
            "scene3_step1_identity_1788581531392.png",
            "scene3_multidb_federation_card_1788581572162.png",
            "scene3_db_connections_1788581555093.png",
            "scene3_step4_deploy_1788581593217.png"
        ]
    },
    {
        "id": "scene4",
        "title": "Ambient Browser Action Relays",
        "text": (
            "Plug-N-Play AI agents do not just produce passive text; they take action. Through our Ambient Browser Relay framework, when an agent detects an intent like canceling an order or updating a preference, it generates a verified action proposal card. "
            "Once confirmed by the user, the widget dispatches a secure DOM event that the parent application executes directly within the active session, displaying immediate feedback toasts without exposing backend private keys."
        ),
        "visual_type": "animation_series",
        "animations": [
            "verify_action_flow_1788434111788.webp"
        ]
    },
    {
        "id": "scene5",
        "title": "Dedicated Zero-SQL Platform Copilot",
        "text": (
            "Next, we engineered a dedicated website guide: the Plug-N-Play Copilot, floating in the bottom-right corner. Built with a Zero-SQL Architecture, this copilot has no access to internal database tables, preventing data leaks. "
            "When a logged-in user asks, 'What is my workspace name?', the copilot resolves the tenant identity strictly from the authenticated server JWT token. "
            "When visitors ask architectural questions, such as 'Why is there an option to add another Database URL?', the copilot retrieves the exact documentation section and streams an authoritative answer with sub-second latency powered by Groq's high-speed inference."
        ),
        "visual_type": "crossfade_series",
        "images": [
            "scene4_copilot_open_1788581616517.png",
            "scene4_copilot_response1_1788581647262.png",
            "scene4_copilot_response2_1788581668816.png"
        ]
    },
    {
        "id": "scene6",
        "title": "Universal Embed Script & Conclusion",
        "text": (
            "Deploying the finished agent into production takes just one line of code. Clients simply copy our universal script tag and paste it into WordPress, Shopify, Webflow, React, Next.js, or standard HTML. "
            "In summary, Plug-N-Play AI delivers Zero-Write AST SQL Safety, Multi-Database Federation, Dual-Engine Document RAG and live Text-to-SQL, Ambient Browser Action Relays, and true Multi-Tenant Isolation. "
            "Thank you for reviewing Plug-N-Play AI for the Razorpay AI Builder 2026 Internship. We are excited to make enterprise AI autonomous, safe, and truly plug-and-play!"
        ),
        "visual_type": "crossfade_series",
        "images": [
            "scene5_embed_snippet_1788581697948.png",
            "scene5_conclusion_1788581708364.png"
        ]
    }
]

def get_image(filename):
    p = os.path.join(artifact_dir, filename)
    if not os.path.exists(p):
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

def get_audio_duration(audio_path):
    cmd = [
        ffmpeg_exe, "-i", audio_path
    ]
    res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    for line in res.stderr.split("\n"):
        if "Duration:" in line:
            parts = line.split("Duration:")[1].split(",")[0].strip().split(":")
            dur = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            return dur
    return 10.0

async def generate_all_audio():
    print("Generating Neural AI Voiceover with Microsoft Azure (Andrew Multilingual)...")
    audio_files = []
    for s in scenes:
        out_audio = os.path.join(temp_audio_dir, f"{s['id']}.mp3")
        communicate = edge_tts.Communicate(s["text"], VOICE, rate="-2%")
        await communicate.save(out_audio)
        dur = get_audio_duration(out_audio)
        s["duration"] = dur + 1.2  # 1.2s padding for natural breathing pause
        s["audio_file"] = out_audio
        print(f"  [{s['id']}] Generated: {s['duration']:.2f}s audio duration")
        audio_files.append(out_audio)
    return audio_files

def build_scene_frames(scene):
    target_frames_count = int(scene["duration"] * fps)
    
    if scene["visual_type"] == "crossfade_series":
        imgs = [get_image(fn) for fn in scene["images"]]
        n_imgs = len(imgs)
        if n_imgs == 1:
            arr = np.array(imgs[0], dtype=np.uint8)
            return [arr] * target_frames_count
        
        frames_per_img = target_frames_count // n_imgs
        fade_frames = min(20, frames_per_img // 3)
        hold_frames = frames_per_img - fade_frames
        
        scene_frames = []
        for i in range(n_imgs):
            curr_img = np.array(imgs[i], dtype=np.float32)
            next_img = np.array(imgs[(i + 1) % n_imgs] if i < n_imgs - 1 else imgs[i], dtype=np.float32)
            
            # Still hold
            for _ in range(hold_frames):
                scene_frames.append(np.clip(curr_img, 0, 255).astype(np.uint8))
            
            # Crossfade if not last
            if i < n_imgs - 1:
                for f in range(fade_frames):
                    alpha = f / float(fade_frames)
                    blended = (1.0 - alpha) * curr_img + alpha * next_img
                    scene_frames.append(np.clip(blended, 0, 255).astype(np.uint8))
            else:
                # Pad remaining
                while len(scene_frames) < target_frames_count:
                    scene_frames.append(np.clip(curr_img, 0, 255).astype(np.uint8))
        return scene_frames[:target_frames_count]
        
    elif scene["visual_type"] == "animation_series":
        all_raw = []
        for fn in scene["animations"]:
            all_raw.extend(get_animated_frames(fn))
        
        scene_frames = []
        for f in all_raw:
            if len(scene_frames) < target_frames_count:
                scene_frames.append(np.array(f, dtype=np.uint8))
        
        last = scene_frames[-1] if scene_frames else np.zeros((target_h, target_w, 3), dtype=np.uint8)
        while len(scene_frames) < target_frames_count:
            scene_frames.append(last)
            
        return scene_frames[:target_frames_count]

async def main():
    # 1. Generate Voiceover
    audio_files = await generate_all_audio()
    
    # Concatenate all scene audio into master audio
    concat_list_file = os.path.join(temp_audio_dir, "concat_list.txt")
    master_audio = os.path.join(temp_audio_dir, "master_narration.mp3")
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for a in audio_files:
            # Silence padding between scenes
            f.write(f"file '{os.path.basename(a)}'\n")
    
    cmd_concat = [
        ffmpeg_exe, "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list_file,
        "-c", "copy", master_audio
    ]
    subprocess.run(cmd_concat, cwd=temp_audio_dir, check=True)
    master_dur = get_audio_duration(master_audio)
    print(f"\nMaster Audio Track Assembled: {master_dur:.2f}s ({master_dur/60:.2f} mins)")
    
    # 2. Build Perfectly Synchronized Video Frames
    print("\nBuilding video frames matched to exact audio timestamps...")
    all_video_frames = []
    for s in scenes:
        frames = build_scene_frames(s)
        all_video_frames.extend(frames)
        print(f"  [{s['id']}] {len(frames)} frames ({len(frames)/fps:.2f}s)")
        
    temp_raw_video = os.path.join(temp_audio_dir, "temp_raw_video.mp4")
    print(f"\nWriting raw video frames ({len(all_video_frames)} frames at {fps} fps)...")
    iio.imwrite(temp_raw_video, all_video_frames, fps=fps, codec="libx264")
    
    # 3. Multiplex Audio and Video with FFmpeg
    final_output = os.path.join(work_dir, "Plug_N_Play_AI_Pitch_Demo_WITH_VOICE.mp4")
    print(f"\nMuxing audio and video into final output: {final_output}...")
    cmd_mux = [
        ffmpeg_exe, "-y",
        "-i", temp_raw_video,
        "-i", master_audio,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        final_output
    ]
    subprocess.run(cmd_mux, check=True)
    
    final_size = os.path.getsize(final_output)
    final_dur = get_audio_duration(final_output)
    print(f"\n==================================================================")
    print(f"COMPLETE! Pitch Video with Neural AI Voiceover Successfully Created!")
    print(f"File: {final_output}")
    print(f"Duration: {final_dur:.1f}s ({final_dur/60:.2f} minutes)")
    print(f"Size: {final_size / (1024*1024):.2f} MB")
    print(f"==================================================================")

if __name__ == "__main__":
    asyncio.run(main())
