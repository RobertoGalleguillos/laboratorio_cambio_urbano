import os
import sys


FOLDER_ID = "1fgVm3omjUBq0Fm0xAxqVudoD1J2M0MeK"


def main() -> int:
    try:
        import gdown
    except ImportError:
        print("Falta gdown. Instala con: python -m pip install gdown")
        return 1

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(repo_root, "data", "raw")
    os.makedirs(out_dir, exist_ok=True)

    url = f"https://drive.google.com/drive/folders/{FOLDER_ID}"
    gdown.download_folder(url=url, output=out_dir, quiet=False, use_cookies=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
