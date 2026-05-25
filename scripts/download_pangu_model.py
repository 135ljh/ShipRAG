from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import snapshot_download


def main() -> None:
    parser = argparse.ArgumentParser(description="Download openPangu model from Hugging Face.")
    parser.add_argument("--repo-id", default="openpangu/openPangu-Embedded-7B-model")
    parser.add_argument("--local-dir", default="models/openPangu-Embedded-7B-model")
    args = parser.parse_args()

    local_dir = Path(args.local_dir)
    local_dir.parent.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=args.repo_id,
        local_dir=str(local_dir),
        local_dir_use_symlinks=False,
        resume_download=True,
    )
    print(f"Downloaded {args.repo_id} to {local_dir}")


if __name__ == "__main__":
    main()
