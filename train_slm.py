#!/usr/bin/env python3
"""
train_slm.py (updated prompt)

Fine-tunes a causal LM (HF) to convert scene JSON -> Manim code using PEFT/LoRA.
Expect training JSONL where each entry has keys: instruction, input, output
"""
import argparse
import os
import json
import random
from typing import Dict, Any

from datasets import load_dataset
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

def build_prompt(example: Dict[str, str]) -> str:
    instruction = example.get("instruction", "")
    inp = example.get("input", "")
    # input is a JSON string for the plan
    prompt = (
        "You are an SLM that converts scene-plan JSON into Manim CE Python code.\n"
        "Rules:\n"
        "- Output ONLY valid Python code (no commentary, no markdown, no backticks).\n"
        "- The code must import manim and define at least one Scene class with construct().\n"
        "- Use object ids to name variables (prefix 'obj_').\n\n"
        f"{instruction}\n\n"
        "Scene JSON (input):\n"
        f"{inp}\n\n"
        "### Response (Python Manim code):\n"
    )
    return prompt

def tokenize_and_mask(batch, tokenizer, max_length=1024):
    input_ids_batch = []
    labels_batch = []
    attention_mask_batch = []
    for inst, inp, out in zip(batch['instruction'], batch.get('input', []), batch['output']):
        ex = {"instruction": inst, "input": inp if inp is not None else "", "output": out}
        prompt = build_prompt(ex)
        full = prompt + out
        tokenized_full = tokenizer(full, truncation=True, max_length=max_length, padding=False)
        tokenized_prompt = tokenizer(prompt, truncation=True, max_length=max_length, padding=False)
        input_ids = tokenized_full["input_ids"]
        prompt_ids = tokenized_prompt["input_ids"]
        labels = [-100] * len(prompt_ids) + input_ids[len(prompt_ids):]
        labels = labels[: len(input_ids)]
        attention_mask = [1] * len(input_ids)
        input_ids_batch.append(input_ids)
        labels_batch.append(labels)
        attention_mask_batch.append(attention_mask)
    return {"input_ids": input_ids_batch, "labels": labels_batch, "attention_mask": attention_mask_batch}

def data_collator(batch, tokenizer):
    import torch
    input_ids = [torch.tensor(x) for x in batch["input_ids"]]
    labels = [torch.tensor(x) for x in batch["labels"]]
    attention_mask = [torch.tensor(x) for x in batch["attention_mask"]]
    input_ids = torch.nn.utils.rnn.pad_sequence(input_ids, batch_first=True, padding_value=tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id)
    labels = torch.nn.utils.rnn.pad_sequence(labels, batch_first=True, padding_value=-100)
    attention_mask = torch.nn.utils.rnn.pad_sequence(attention_mask, batch_first=True, padding_value=0)
    return {"input_ids": input_ids, "labels": labels, "attention_mask": attention_mask}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name_or_path", type=str, required=True)
    parser.add_argument("--train_file", type=str, required=True)
    parser.add_argument("--output_dir", type=str, default="outputs/slm-lora")
    parser.add_argument("--per_device_train_batch_size", type=int, default=4)
    parser.add_argument("--num_train_epochs", type=int, default=3)
    parser.add_argument("--learning_rate", type=float, default=2e-4)
    parser.add_argument("--max_length", type=int, default=1024)
    parser.add_argument("--lora_r", type=int, default=8)
    parser.add_argument("--lora_alpha", type=int, default=16)
    parser.add_argument("--lora_dropout", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)

    os.makedirs(args.output_dir, exist_ok=True)

    print("Loading dataset...")
    dataset = load_dataset("json", data_files=args.train_file)["train"]
    print(f"Dataset size: {len(dataset)} examples")

    tokenizer = AutoTokenizer.from_pretrained(args.model_name_or_path, use_fast=True)
    if tokenizer.pad_token_id is None:
        tokenizer.add_special_tokens({"pad_token": "<|pad|>"})

    model = AutoModelForCausalLM.from_pretrained(args.model_name_or_path, torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32, device_map="auto" if torch.cuda.is_available() else None)
    model.resize_token_embeddings(len(tokenizer))

    lora_config = LoraConfig(r=args.lora_r, lora_alpha=args.lora_alpha, target_modules=None, lora_dropout=args.lora_dropout, bias="none", task_type="CAUSAL_LM")
    try:
        model = prepare_model_for_kbit_training(model)
    except Exception:
        pass
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    tokenized = dataset.map(lambda examples: tokenize_and_mask(examples, tokenizer, max_length=args.max_length), batched=True, remove_columns=dataset.column_names)
    tokenized = tokenized.with_format(type="torch")

    training_args = TrainingArguments(output_dir=args.output_dir, per_device_train_batch_size=args.per_device_train_batch_size, num_train_epochs=args.num_train_epochs, learning_rate=args.learning_rate, logging_steps=50, save_strategy="epoch", fp16=torch.cuda.is_available(), remove_unused_columns=False, report_to="none")

    trainer = Trainer(model=model, args=training_args, train_dataset=tokenized, data_collator=lambda b: data_collator(b, tokenizer))
    trainer.train()
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print("Training complete. Model saved to:", args.output_dir)
