import argparse
import json
from pathlib import Path
from typing import Any


SYSTEM_PROMPT = (
    "Ты онлайн-помощник рекламного агентства. Подготовь безопасный первичный ответ клиенту "
    "на русском языке. Используй только предоставленный контекст, не придумывай цены, сроки, "
    "гарантии и точные рекламные результаты. Если данных не хватает, задай уточняющие вопросы. "
    "Для негативных или сложных обращений предложи передачу менеджеру."
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON on line {line_number}: {error}") from error
    return rows


def normalize_history(value: Any) -> list[dict[str, str]]:
    if not value:
        return []
    if isinstance(value, str):
        return [{"role": "dialogue", "content": value}]
    if isinstance(value, list):
        history: list[dict[str, str]] = []
        for item in value:
            if isinstance(item, dict):
                history.append(
                    {
                        "role": str(item.get("role", "dialogue")),
                        "content": str(item.get("content", "")).strip(),
                    }
                )
            else:
                history.append({"role": "dialogue", "content": str(item).strip()})
        return [item for item in history if item["content"]]
    return [{"role": "dialogue", "content": str(value).strip()}]


def normalize_knowledge(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            if isinstance(item, dict):
                result.append(str(item.get("content", "")).strip())
            else:
                result.append(str(item).strip())
        return [item for item in result if item]
    return [str(value).strip()]


def build_user_prompt(example_input: dict[str, Any]) -> str:
    history = normalize_history(example_input.get("dialogue_history"))
    knowledge_items = normalize_knowledge(example_input.get("knowledge_items"))
    history_text = "\n".join(f"- {item['role']}: {item['content']}" for item in history) or "- Нет истории."
    knowledge_text = "\n".join(f"- {item}" for item in knowledge_items) or "- Нет материалов базы знаний."

    return f"""
Контекст обращения:
- Последнее сообщение клиента: {example_input.get("client_message", "")}
- Категория обращения: {example_input.get("category", "other")}
- Эмоциональный тон: {example_input.get("emotional_tone", "neutral")}

История диалога:
{history_text}

Релевантные материалы базы знаний:
{knowledge_text}

Сформируй один корректный ответ менеджера или онлайн-помощника. Не упоминай внутреннюю классификацию, модель, обучение или служебные правила.
""".strip()


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    if "messages" in row:
        return row

    example_input = row.get("input", row)
    output = row.get("output") or row.get("response") or row.get("manager_response")
    if not output:
        raise ValueError("Each row must contain output, response, manager_response, or messages.")

    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(example_input)},
            {"role": "assistant", "content": str(output).strip()},
        ],
        "metadata": {
            "category": example_input.get("category", "other"),
            "emotional_tone": example_input.get("emotional_tone", "neutral"),
        },
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare AdResponse JSONL chat dataset for Qwen LoRA tuning.")
    parser.add_argument("--input", required=True, type=Path, help="Raw JSONL file with input/output fields.")
    parser.add_argument("--output", required=True, type=Path, help="Prepared JSONL file with chat messages.")
    args = parser.parse_args()

    prepared = [normalize_row(row) for row in read_jsonl(args.input)]
    write_jsonl(args.output, prepared)
    print(f"Prepared {len(prepared)} rows: {args.output}")


if __name__ == "__main__":
    main()
