import logging

from transformers import pipeline


logger = logging.getLogger(__name__)
SAFE_RESPONSE = "Sorry, I can't assist with that."
_pipe = None


def _get_pipeline():
    global _pipe
    if _pipe is None:
        model_path = "Intel/toxic-prompt-roberta"
        logger.info("Loading toxicity guardrail model: %s", model_path)
        _pipe = pipeline("text-classification", model=model_path, tokenizer=model_path)
    return _pipe


def check_toxicity(text):
    pipe = _get_pipeline()
    max_length = pipe.tokenizer.model_max_length if hasattr(pipe.tokenizer, "model_max_length") else 512
    inputs = pipe.tokenizer(text, truncation=True, max_length=max_length, return_tensors="pt")
    truncated_text = pipe.tokenizer.decode(inputs["input_ids"][0], skip_special_tokens=True)
    result = pipe(truncated_text)[0]
    return result["label"], result["score"]


def guard_input(text):
    label, score = check_toxicity(text)
    if label == "TOXIC":
        return False, label, score, SAFE_RESPONSE
    return True, label, score, None


def guard_output(text):
    label, score = check_toxicity(text)
    if label == "TOXIC":
        return False, label, score, SAFE_RESPONSE
    return True, label, score, None


def initialize_guardrails() -> None:
    """Warm up the toxicity guardrail pipeline so first request doesn't pay the load cost."""
    _get_pipeline()
