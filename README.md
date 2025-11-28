# devForge
🎬 Text-to-Animated-Video Generator

Convert natural language into fully animated Manim videos using LLM-driven JSON planning & procedural animation.

This project transforms any text description—such as:

“Show a ball launched in a parabolic trajectory.”

into a complete Manim animation, rendered as an MP4 video.
It uses a multi-stage pipeline combining LLM planning, JSON validation, motion logic, and video rendering.

🚀 Features
1. Text → Structured JSON Scene Plan

Your input text is enhanced by an LLM (Gemini API) to generate a structured JSON describing:

Scene titles

Objects (Dot, Text, Axes, Circle, Square, Paths, Parametric curves, etc.)

Actions (FadeIn, Create, MoveAlongPath, FadeOut, Animate motion)

Scene hints (e.g., “projectile motion”, “parabolic trajectory”)

Optional physics parameters

2. JSON → Manim Python Code

The JSON plan is validated and transformed into executable Manim CE code, producing:

Multi-object animations

Parametric motion (projectile arcs, curves, custom paths)

Camera-ready Manim scenes

Automatic class naming

Clean & safe Python code generation

3. Automatic Video Rendering

The generated Manim code is executed automatically to produce:

project_root/media/videos/<scene>/<resolution>/<video>.mp4


Your pipeline even locates the final video file automatically.

4. Fallback Mode

If no LLM API key is available, or the enhancement fails, the system uses a deterministic fallback plan so the pipeline still works.


🧠 Pipeline Overview
User Text
   ↓
Gemini Enhancer (Text → JSON)     ← requires your API key
   ↓
Plan Validator (safety checks)
   ↓
Training Pipeline (JSON → Manim code)
   ↓
Render Pipeline (Manim → MP4)
   ↓
Final Animated Video


🔑 Environment Setup (IMPORTANT)

Create a file named .env in the project root:

GEMINI_API_KEY=YOUR_OWN_KEY_HERE
GEMINI_API_ENDPOINT=YOUR_OWN_ENDPOINT_HERE

❗ You MUST attach your own API key & endpoint

The enhancer uses Gemini LLM to convert text → JSON.
Without your key, the system falls back to deterministic mode.

▶️ Running the Generator

Use:

python render_pipeline.py "a ball launched in a parabolic trajectory"


The script will:

Generate a JSON scene plan

Produce Manim CE code

Render MP4 video

Print the final video path

Example output:

Rendered video: C:\Users\You\Project\media\videos\Projectile\1080p60\Projectile.mp4



📁 Project Structure
viva/
│
├── render_pipeline.py        # Main entrypoint (text → video)
├── genai_enhancer.py         # LLM-based JSON generator
├── training_pipeline.py      # JSON → Manim code
├── plan_validator.py         # Schema validation + autofill
├── train_slm.py              # Fine-tuning script for custom SLM
│
├── outputs/
│   ├── plans/                # Generated JSON plans
│   ├── manim_code/           # Generated Manim Python files
│   └── videos/               # Optional saved videos
│
├── training/
│   └── generated_data/       # Dataset for training SLM
│
├── media/                    # Manim auto-generated output
│
├── requirements.txt
└── .gitignore



❤️ Contributing

Fork

Create a new branch

Submit a PR

Wait for review

Pull requests are welcome!


