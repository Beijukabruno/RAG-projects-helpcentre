#!/usr/bin/env python3

from pathlib import Path


def load_dotenv_file(path: Path):
    env = {}

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()

    return env


def main():
    env = load_dotenv_file(Path(".env.sample"))

    api_key = env.get("GEMMA_API_KEY")

    if not api_key:
        raise ValueError(
            "GEMMA_API_KEY not found in .env.sample"
        )

    try:
        from google import genai
    except ImportError:
        print(
            "Install dependency:\n"
            "pip install google-genai"
        )
        return

    client = genai.Client(api_key=api_key)

    print("\n" + "=" * 80)
    print("AVAILABLE MODELS")
    print("=" * 80)

    models = list(client.models.list())

    embedding_models = []
    generation_models = []

    for model in models:
        name = getattr(model, "name", "unknown")

        print(name)

        lower = name.lower()

        if "embed" in lower:
            embedding_models.append(name)

        if any(
            x in lower
            for x in [
                "gemini",
                "gemma",
                "flash",
                "pro",
            ]
        ):
            generation_models.append(name)

    print("\n")
    print("=" * 80)
    print("EMBEDDING MODELS")
    print("=" * 80)

    for m in embedding_models:
        print(m)

    print("\n")
    print("=" * 80)
    print("GENERATION MODELS")
    print("=" * 80)

    for m in generation_models:
        print(m)

    #
    # Test embedding
    #
    if embedding_models:
        print("\n")
        print("=" * 80)
        print("EMBEDDING TEST")
        print("=" * 80)

        try:
            response = client.models.embed_content(
                model=embedding_models[0],
                contents="Hello world"
            )

            vector = response.embeddings[0].values

            print(
                f"Model: {embedding_models[0]}"
            )
            print(
                f"Embedding dimensions: {len(vector)}"
            )

        except Exception as e:
            print(
                f"Embedding test failed: {e}"
            )

    #
    # Test generation
    #
    if generation_models:
        print("\n")
        print("=" * 80)
        print("GENERATION TEST")
        print("=" * 80)

        try:
            response = client.models.generate_content(
                model=generation_models[0],
                contents="Say hello in one sentence."
            )

            print(
                f"Model: {generation_models[0]}"
            )
            print(response.text)

        except Exception as e:
            print(
                f"Generation test failed: {e}"
            )


if __name__ == "__main__":
    main()