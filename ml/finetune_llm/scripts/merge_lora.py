import argparse
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


DEFAULT_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge AdResponse LoRA adapter into Qwen base model.")
    parser.add_argument("--base-model", default=DEFAULT_MODEL)
    parser.add_argument("--adapter-dir", required=True, type=Path)
    parser.add_argument("--output-dir", default="ml/finetune_llm/merged_models/qwen2.5-adresponse", type=Path)
    args = parser.parse_args()

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
        trust_remote_code=True,
    )
    model = PeftModel.from_pretrained(model, args.adapter_dir)
    merged_model = model.merge_and_unload()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    merged_model.save_pretrained(args.output_dir, safe_serialization=True)
    tokenizer.save_pretrained(args.output_dir)
    print(f"Saved merged model: {args.output_dir}")


if __name__ == "__main__":
    main()
