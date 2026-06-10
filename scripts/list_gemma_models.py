#!/usr/bin/env python3

import argparse
from pathlib import Path


def load_dotenv_file(path: Path):
    data = {}

    if not path.exists():
        print(f".env file not found at: {path}")
        return data

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if "=" in line:
                k, v = line.split("=", 1)
                data[k.strip()] = v.strip()

    return data


def try_list_models(key_name: str, api_key: str):
    output = []

    header = (
        "\n"
        + "=" * 60
        + f"\nKey: {key_name}\n"
        + "=" * 60
        + "\n"
    )

    print(header, end="")
    output.append(header)

    if not api_key:
        msg = "No key value found\n"
        print(msg, end="")
        output.append(msg)
        return output

    try:
        import google.genai as genai
    except Exception as e:
        msg = (
            f"google.genai package not installed: {e}\n"
            "Install it with: pip install google-genai\n"
        )

        print(msg, end="")
        output.append(msg)
        return output

    try:
        client = genai.Client(api_key=api_key)

        if hasattr(client.models, "list"):

            models = list(client.models.list())

            tline = f"Found {len(models)} models\n\n"
            print(tline, end="")
            output.append(tline)

            for m in models:
                line = repr(m) + "\n\n"

                print(line, end="")
                output.append(line)

        else:
            msg = (
                "client.models.list not available on this client version\n"
            )

            print(msg, end="")
            output.append(msg)

    except Exception as e:
        msg = f"Error while listing models: {e}\n"

        print(msg, end="")
        output.append(msg)

    return output


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--env",
        type=str,
        default=".env",
        help="Path to .env file",
    )

    args = parser.parse_args()

    env_path = Path(args.env)

    env = load_dotenv_file(env_path)

    gemma = env.get("GEMMA_API_KEY") or env.get("GEMMA_KEY")
    new_gemma = env.get("NEW_GEMMA_API_KEY")

    found_keys = ", ".join(sorted(env.keys()))

    intro = (
        f"Parsed .env: {env_path}\n"
        f"Found keys: {found_keys}\n\n"
    )

    print(intro)

    results = [intro]

    results.extend(
        try_list_models("GEMMA_API_KEY", gemma)
    )

    results.extend(
        try_list_models("NEW_GEMMA_API_KEY", new_gemma)
    )

    out_path = Path("scripts") / "gemma_models_list.txt"

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)

        full_text = "".join(results)

        with out_path.open("w", encoding="utf-8") as fh:
            fh.write(full_text)

        print(f"\nWrote results to: {out_path}")
        print(f"Saved {len(full_text)} characters")

    except Exception as e:
        print(f"Failed to write output file: {e}")


if __name__ == "__main__":
    main()