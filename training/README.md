```markdown
# Train SLM (Small Language Model) — quick guide

Overview
- We fine-tune a pretrained causal model with instruction-response pairs.
- We use PEFT LoRA so you only train a small number of parameters (efficient).
- Dataset format: JSONL lines with { "instruction": "...", "input": "...", "output": "..." }.

Install (recommended)
- Create venv and activate:
  python -m venv venv
  # Windows PowerShell:
  .\venv\Scripts\Activate
  # macOS/Linux:
  source venv/bin/activate

- Install dependencies (example; adapt for GPU):
  python -m pip install --upgrade pip setuptools wheel
  pip install transformers datasets peft accelerate
  # Install torch appropriate for your CUDA; for CPU:
  pip install torch
  # Optional: bitsandbytes for 4-bit finetuning (if you have compatible GPU)
  # pip install bitsandbytes

Notes:
- For 1B+ models, prefer bitsandbytes + 4-bit quant + GPU(s) and use device_map="auto".
- For small tests use a smaller model for speed (e.g., bigscience/bloom-560m).

Prepare data
- Use dataset_prep.py to create `training/sample_data.jsonl` or replace with your own JSONL.
- Each line must have instruction/input/output fields.

Training
- Example command (small model):
  python training/train_slm.py \
    --model_name_or_path bigscience/bloom-560m \
    --train_file training/sample_data.jsonl \
    --output_dir outputs/slm-lora \
    --per_device_train_batch_size 2 \
    --num_train_epochs 1

Notes & hyperparams
- LoRA defaults: r=8, alpha=16, dropout=0.05
- LR: 1e-4 to 3e-4 for LoRA
- Increase batch size if you have more VRAM

Evaluation & Inference
- Load base model and apply PEFT adapters:
  from transformers import AutoModelForCausalLM, AutoTokenizer
  from peft import PeftModel
  base = AutoModelForCausalLM.from_pretrained("facebook/opt-1.3b")
  model = PeftModel.from_pretrained(base, "outputs/slm-lora")
  tokenizer = AutoTokenizer.from_pretrained("facebook/opt-1.3b")
  inputs = tokenizer("Explain photosynthesis", return_tensors="pt").to(model.device)
  outputs = model.generate(**inputs, max_new_tokens=200)

Hardware & costs
- 1–2 GPUs with 16–48GB VRAM recommended for 1B–7B models.
- For small experiments CPU is possible but slow.

If you want:
- I can adapt the script for bitsandbytes 4-bit training,
- add an evaluation script for automatic metrics,
- or create a setup using Hugging Face accelerate config for multi-GPU.

Reply with your preferred base model and GPU details and I’ll tailor commands/hyperparams.