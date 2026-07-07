import argparse
import json
from pathlib import Path
from typing import Any

import torch
from datasets import load_dataset
from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    Trainer,
    TrainingArguments,
)


DEFAULT_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LoRA/QLoRA fine-tuning for AdResponse local LLM.")
    parser.add_argument("--train-file", required=True, type=Path, help="Prepared JSONL with messages.")
    parser.add_argument("--output-dir", default="ml/finetune_llm/adapters/qwen2.5-adresponse-lora", type=Path)
    parser.add_argument("--model-name", default=DEFAULT_MODEL)
    parser.add_argument("--max-length", default=1536, type=int)
    parser.add_argument("--epochs", default=3, type=float)
    parser.add_argument("--learning-rate", default=2e-4, type=float)
    parser.add_argument("--batch-size", default=1, type=int)
    parser.add_argument("--gradient-accumulation-steps", default=8, type=int)
    parser.add_argument("--qlora", action="store_true", help="Load the base model in 4-bit mode.")
    return parser.parse_args()


def build_tokenized_example(example: dict[str, Any], tokenizer: AutoTokenizer, max_length: int) -> dict[str, Any]:
    messages = example["messages"]
    prompt_messages = messages[:-1]
    full_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    prompt_text = tokenizer.apply_chat_template(prompt_messages, tokenize=False, add_generation_prompt=True)

    full = tokenizer(full_text, max_length=max_length, truncation=True, padding=False)
    prompt = tokenizer(prompt_text, max_length=max_length, truncation=True, padding=False)
    labels = list(full["input_ids"])
    prompt_length = min(len(prompt["input_ids"]), len(labels))
    labels[:prompt_length] = [-100] * prompt_length
    full["labels"] = labels
    return full


class DataCollator:
    def __init__(self, tokenizer: AutoTokenizer) -> None:
        self.tokenizer = tokenizer

    def __call__(self, features: list[dict[str, Any]]) -> dict[str, torch.Tensor]:
        labels = [feature.pop("labels") for feature in features]
        batch = self.tokenizer.pad(features, padding=True, return_tensors="pt")
        max_length = batch["input_ids"].shape[1]
        padded_labels = [
            label + [-100] * (max_length - len(label))
            for label in labels
        ]
        batch["labels"] = torch.tensor(padded_labels, dtype=torch.long)
        return batch


def main() -> None:
    args = parse_args()
    tokenizer = AutoTokenizer.from_pretrained(args.model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    quantization_config = None
    if args.qlora:
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )

    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
        quantization_config=quantization_config,
        trust_remote_code=True,
    )
    if args.qlora:
        model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    dataset = load_dataset("json", data_files=str(args.train_file), split="train")
    tokenized = dataset.map(
        lambda example: build_tokenized_example(example, tokenizer, args.max_length),
        remove_columns=dataset.column_names,
    )

    training_args = TrainingArguments(
        output_dir=str(args.output_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        logging_steps=10,
        save_strategy="epoch",
        bf16=torch.cuda.is_available(),
        fp16=False,
        report_to="none",
        remove_unused_columns=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized,
        data_collator=DataCollator(tokenizer),
    )
    trainer.train()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    metadata = {
        "base_model": args.model_name,
        "adapter_type": "LoRA",
        "dataset": str(args.train_file),
        "llama_cpp_usage": "inference_only_after_merge_and_gguf_conversion",
    }
    (args.output_dir / "adresponse_training_meta.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved LoRA adapter: {args.output_dir}")


if __name__ == "__main__":
    main()
