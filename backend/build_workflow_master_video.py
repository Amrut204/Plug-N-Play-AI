import os
import asyncio
import subprocess
import edge_tts
import numpy as np
from PIL import Image
import imageio.v3 as iio
import imageio_ffmpeg

artifact_dir = r"C:\Users\dongr\.gemini\antigravity-ide\brain\0cbbf9b9-7086-4f3a-9193-adc74d8984cd"
work_dir = r"C:\vscode\Plug-N-Play-RAG"
temp_dir = os.path.join(work_dir, "temp_workflow_video")
os.makedirs(temp_dir, exist_ok=True)

ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
target_w, target_h = 1920, 1080
fps = 10
VOICE = "en-US-AndrewMultilingualNeural"

# Sequential Scenes strictly adhering to the user's instructions:
# 1. Fast Google login in 5-7s
# 2. Landing page intro & platform architecture
# 3-7. Step-by-step Agent Studio workflow (Step 1-4, Multi-DB federation, Zero-Knowledge Schema, AST SQL, Guardrails, Escalation)
# 8. Interactive Sandbox testing
# 9. Minimal codebase embed (1-line universal script)
# 10. Fleet dashboard & telemetry
scenes = [
    {
        "id": "scene1_fast_auth",
        "title": "Fast 5-Second Authentication",
        "text": (
            "Starting with onboarding, access is instantaneous. With single-click Google Authentication, "
            "developers enter their cryptographically isolated workspace in under five seconds with zero setup friction."
        ),
        "images": [
            "flow2_fast_login_1788586740150.png"
        ]
    },
    {
        "id": "scene2_landing_intro",
        "title": "Platform Intro & Dual-Engine Architecture",
        "text": (
            "Welcome to Plug-N-Play AI, an enterprise-grade autonomous agent platform built for the Razorpay AI Builder 2026 challenge. "
            "Modern enterprises face a fundamental data challenge: their business intelligence is split between static unstructured documentation and live transactional databases. "
            "Standard chatbots only search static documents and fail when asked for live order details, while enterprises rightfully fear AI corrupting production databases. "
            "Plug-N-Play AI bridges this divide with our Dual-Engine Retrieval architecture, combining semantic vector RAG with real-time, read-only SQL generation, "
            "enforced by our strict Zero-Write Mandate and Abstract Syntax Tree security."
        ),
        "images": [
            "flow1_landing_hero_1788586685211.png",
            "flow1_security_pillars_1788586716089.png"
        ]
    },
    {
        "id": "scene3_step1_identity",
        "title": "Agent Studio Step 1: Agent Identity & Persona",
        "text": (
            "Now, let us walk through the core workflow of creating an enterprise agent from scratch. "
            "In Step 1, we establish the agent's identity and behavioral persona. Here, developers name their agent, designate the workspace project, "
            "and select from curated brand tones, ranging from empathetic and professional to technical. "
            "The custom system prompt editor provides complete flexibility: whether you are creating an e-commerce shopping concierge, a student academic advisor, "
            "or an internal IT support assistant, you have full prompt-level control over the agent's tone, scope, and operational boundaries."
        ),
        "images": [
            "flow3_step1_identity_1788587212892.png"
        ]
    },
    {
        "id": "scene4_step2_rag_docs",
        "title": "Agent Studio Step 2: Knowledge Ingestion & Unstructured RAG",
        "text": (
            "In Step 2, we configure the agent's knowledge sources. For unstructured domain knowledge, developers can upload PDFs, Word documents, Markdown guides, "
            "and company policy handbooks. Plug-N-Play AI automatically parses and chunks these files, computing 384-dimensional dense vector embeddings. "
            "During live user interactions, the semantic retrieval engine performs cosine similarity search in milliseconds, grounding every response in verified documentation "
            "and citing source pages directly to eliminate hallucinations."
        ),
        "images": [
            "flow3_step2_rag_docs_1788587499080.png"
        ]
    },
    {
        "id": "scene5_step2_multidb",
        "title": "Agent Studio Step 2: Multi-Database Federation & Zero-Knowledge Schema Mode",
        "text": (
            "Next, we configure our structured data engine, supporting live enterprise databases including PostgreSQL, MySQL, SQLite, and MongoDB. "
            "Here we introduce two major architectural innovations. First is Multi-Database Federation: by simply clicking '+ Add Another Database', "
            "our orchestrator connects multiple disparate databases to a single agent. For example, customer orders can reside in PostgreSQL while product catalog records live in MySQL, "
            "and the agent executes federated cross-database lookups in a single conversational turn! "
            "Second is our Zero-Knowledge Schema-Only Mode: enterprises with stringent compliance requirements can simply paste their SQL DDL schema. "
            "The agent synthesizes verified queries without our platform ever needing live database credentials or firewall access."
        ),
        "images": [
            "flow3_step2_multidb_federation_1788587635822.png"
        ]
    },
    {
        "id": "scene6_step3_guardrails",
        "title": "Agent Studio Step 3: Audience Guardrails & AST Security",
        "text": (
            "In Step 3, we establish Audience Guardrails and row-level access control. Different user tiers require different data visibility. "
            "In End-User Mode, strict row isolation automatically appends 'WHERE user_id equals current user' to all SQL queries, mathematically preventing users from viewing anyone else's private orders or account data. "
            "Staff and Executive presets allow broader aggregate lookups while masking personally identifiable information. "
            "Furthermore, every generated query passes through our Abstract Syntax Tree Security Gate, which inspects query syntax and instantly blocks any destructive commands "
            "such as DROP, DELETE, UPDATE, or INSERT before execution."
        ),
        "images": [
            "flow3_step3_guardrails_1788587719729.png"
        ]
    },
    {
        "id": "scene7_step4_actions",
        "title": "Agent Studio Step 4: Actions & Live Human Escalation",
        "text": (
            "In Step 4, we configure proactive Actions and Live Human Escalation. When an inquiry requires human intervention or encounters complex edge cases, "
            "the agent instantly triggers automated escalation alerts through SMTP email notifications or webhook alerts. "
            "In addition, through our Ambient Browser Relay framework, agents can propose verified client-side actions, such as applying promotional vouchers or navigating to checkout, "
            "returning control smoothly to the user."
        ),
        "images": [
            "flow3_step4_actions_escalation_1788587783341.png"
        ]
    },
    {
        "id": "scene8_sandbox_testing",
        "title": "Step 4 Sandbox: Live Dual-Engine Testing & Validation",
        "text": (
            "Before deploying to production, developers can thoroughly test their agent in the live interactive Sandbox Console. "
            "Here, we can observe dual-engine retrieval in real time. When asking policy questions, the agent retrieves grounded vector snippets. "
            "When querying transactional data, such as checking order status or inventory levels, it translates natural language into read-only SQL, "
            "executing queries securely and displaying formatted data cards with sub-second streaming inference powered by Groq's high-speed Llama-3."
        ),
        "images": [
            "flow4_sandbox_testing_1788587962539.png"
        ]
    },
    {
        "id": "scene9_embed_script",
        "title": "Codebase Integration with Minimal Changes (Universal 1-Line Embed)",
        "text": (
            "Once validated, deploying the agent into any codebase requires zero complex refactoring or backend rewrites. "
            "Developers simply copy our universal one-line script snippet and paste it right before the closing body tag of their web application. "
            "That is all it takes! The widget initializes automatically, establishes secure session tokens, and is fully compatible with React, Next.js, "
            "WordPress, Shopify, Angular, Vue, or pure HTML with zero npm dependencies."
        ),
        "images": [
            "flow5_embed_script_1788588244897.png"
        ]
    },
    {
        "id": "scene10_dashboard_fleet",
        "title": "Workspace Telemetry & Fleet Management",
        "text": (
            "Finally, our Workspace Dashboard provides full operational telemetry for your agent fleet. "
            "Engineering teams can monitor query latencies, token consumption, and security shield events across all active deployments, backed by strict cryptographic multi-tenant isolation. "
            "Plug-N-Play AI bridges the gap between static documents and live transactional databases with zero friction and enterprise-grade security. "
            "Thank you for considering our project for the Razorpay AI Builder 2026 Internship!"
        ),
        "images": [
            "flow6_dashboard_complete_1788588302860.png"
        ]
    }
]

def get_image(filename):
    p = os.path.join(artifact_dir, filename)
    if not os.path.exists(p):
        print(f"Warning: Image {filename} not found")
        return Image.new("RGB", (target_w, target_h), (10, 14, 23))
    
    src = Image.open(p).convert("RGB")
    # Letterbox pad to exact 1920x1080 maintaining 100% crisp unscaled fidelity
    canvas = Image.new("RGB", (target_w, target_h), (10, 14, 23))
    
    if src.width == 1920 and src.height <= 1080:
        y_offset = (target_h - src.height) // 2
        canvas.paste(src, (0, y_offset))
    else:
        src_ratio = src.width / src.height
        target_ratio = target_w / target_h
        if src_ratio > target_ratio:
            new_w = target_w
            new_h = int(target_w / src_ratio)
        else:
            new_h = target_h
            new_w = int(target_h * src_ratio)
        scaled = src.resize((new_w, new_h), Image.Resampling.LANCZOS)
        x_offset = (target_w - new_w) // 2
        y_offset = (target_h - new_h) // 2
        canvas.paste(scaled, (x_offset, y_offset))
        
    return canvas

def get_audio_duration(audio_path):
    cmd = [ffmpeg_exe, "-i", audio_path]
    res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    for line in res.stderr.split("\n"):
        if "Duration:" in line:
            parts = line.split("Duration:")[1].split(",")[0].strip().split(":")
            dur = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            return dur
    return 10.0

async def prepare_audio_tracks():
    print("Preparing Studio Neural AI Audio Tracks...")
    final_padded_audios = []
    
    for s in scenes:
        raw_audio = os.path.join(temp_dir, f"{s['id']}_raw.mp3")
        padded_audio = os.path.join(temp_dir, f"{s['id']}_padded.mp3")
        
        # 1. Synthesize if raw does not exist or is empty
        if not os.path.exists(raw_audio) or os.path.getsize(raw_audio) < 1000:
            print(f"  Synthesizing {s['id']}...")
            comm = edge_tts.Communicate(s["text"], VOICE, rate="-2%")
            await comm.save(raw_audio)
        
        # 2. Pad exactly 0.6s silence at the end with FFmpeg apad
        pad_cmd = [
            ffmpeg_exe, "-y",
            "-i", raw_audio,
            "-af", "apad=pad_dur=0.6",
            "-c:a", "libmp3lame",
            "-q:a", "2",
            padded_audio
        ]
        subprocess.run(pad_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        
        # 3. Measure EXACT duration of padded audio
        dur = get_audio_duration(padded_audio)
        s["duration"] = dur
        s["audio_file"] = padded_audio
        final_padded_audios.append(padded_audio)
        print(f"  [{s['id']}] Padded Audio: {dur:.2f}s ({s['title']})")
        
    return final_padded_audios

def render_scene_frames(scene):
    target_count = int(scene["duration"] * fps)
    imgs = [get_image(fn) for fn in scene["images"]]
    n_imgs = len(imgs)
    
    if n_imgs == 1:
        arr = np.array(imgs[0], dtype=np.uint8)
        return [arr] * target_count
    
    frames_per_img = target_count // n_imgs
    fade_frames = min(15, frames_per_img // 4)
    hold_frames = frames_per_img - fade_frames
    
    frames = []
    for i in range(n_imgs):
        curr_img = np.array(imgs[i], dtype=np.float32)
        next_img = np.array(imgs[(i + 1) % n_imgs] if i < n_imgs - 1 else imgs[i], dtype=np.float32)
        
        for _ in range(hold_frames):
            frames.append(np.clip(curr_img, 0, 255).astype(np.uint8))
        
        if i < n_imgs - 1:
            for f in range(fade_frames):
                alpha = f / float(fade_frames)
                blended = (1.0 - alpha) * curr_img + alpha * next_img
                frames.append(np.clip(blended, 0, 255).astype(np.uint8))
        else:
            while len(frames) < target_count:
                frames.append(np.clip(curr_img, 0, 255).astype(np.uint8))
                
    return frames[:target_count]

async def main():
    print("=" * 65)
    print("PLUG-N-PLAY AI — MASTER PITCH VIDEO COMPILER (PERFECT SYNC)")
    print("=" * 65)
    
    # 1. Prepare Audio
    audio_files = await prepare_audio_tracks()
    
    # 2. Concat Master Audio
    concat_list_file = os.path.join(temp_dir, "concat_list.txt")
    master_audio = os.path.join(temp_dir, "master_narration.mp3")
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for a in audio_files:
            f.write(f"file '{os.path.basename(a)}'\n")
            
    subprocess.run([
        ffmpeg_exe, "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list_file,
        "-c", "copy", master_audio
    ], cwd=temp_dir, check=True)
    
    master_dur = get_audio_duration(master_audio)
    print(f"\nMaster Audio Assembled: {master_dur:.2f}s ({master_dur/60:.2f} minutes)")
    
    # 3. Assemble Perfectly Synchronized Video Frames
    print("\nBuilding video frames matched to exact audio timestamps...")
    all_frames = []
    for s in scenes:
        scene_frames = render_scene_frames(s)
        all_frames.extend(scene_frames)
        print(f"  [{s['id']}] {len(scene_frames)} frames ({len(scene_frames)/fps:.2f}s)")
        
    temp_raw_video = os.path.join(temp_dir, "temp_raw_video.mp4")
    print(f"\nEncoding raw video frames ({len(all_frames)} frames at {fps} fps)...")
    iio.imwrite(temp_raw_video, all_frames, fps=fps, codec="libx264")
    
    # 4. Mux Audio & Video with FFmpeg
    final_output = os.path.join(work_dir, "Plug_N_Play_AI_Master_Pitch_Demo.mp4")
    print(f"\nMuxing into Final Master Video: {final_output}...")
    subprocess.run([
        ffmpeg_exe, "-y",
        "-i", temp_raw_video,
        "-i", master_audio,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        final_output
    ], check=True)
    
    final_size = os.path.getsize(final_output)
    final_dur = get_audio_duration(final_output)
    print("\n" + "=" * 65)
    print("SUCCESS! Fresh Master Agent Pitch Video Created!")
    print(f"File: {final_output}")
    print(f"Duration: {final_dur:.1f}s ({final_dur/60:.2f} minutes)")
    print(f"Size: {final_size / (1024*1024):.2f} MB")
    print("=" * 65)

if __name__ == "__main__":
    asyncio.run(main())
