from pathlib import Path
from urllib.request import Request, urlopen
import sys


def download_image(url: str, output_path: str) -> None:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    output = Path(output_path)

    with urlopen(request, timeout=30) as response, output.open("wb") as file:
        while chunk := response.read(8192):
            file.write(chunk)

    print(f"Downloaded image to {output}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python download_image.py IMAGE_URL OUTPUT_PATH")

    download_image(sys.argv[1], sys.argv[2])