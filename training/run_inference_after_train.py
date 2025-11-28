#!/usr/bin/env python3
"""
Quick inference tester for a saved adapter/model directory (PEFT).
Usage:
python training/run_inference_after_train.py --model_dir outputs/slm_combined --prompt "Explain photosynthesis"
"""
import argparse
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import torch

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_dir", required=True)
    parser.add_argument("--base_model", required=True)
    parser.add_argument("--prompt", required=True)
    args = parser.parse_args()

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, use_fast=True)
    base = AutoModelForCausalLM.from_pretrained(args.base_model, device_map="auto" if torch.cuda.is_available() else None)
    model = PeftModel.from_pretrained(base, args.model_dir)
    model.eval()
    inputs = tokenizer(args.prompt, return_tensors="pt").to(model.device)
    out = model.generate(**inputs, max_new_tokens=200, do_sample=False)
    print(tokenizer.decode(out[0], skip_special_tokens=True))

if __name__ == "__main__":
    main()