from pathlib import Path
from urllib.parse import urlparse
import requests


def is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def download_pdf(url: str, destination_dir: Path) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    filename = Path(urlparse(url).path).name or "fifa_squad_list.pdf"
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    destination = destination_dir / filename

    headers = {"User-Agent": "WorldCup-Player-Analytics/0.2.0 SportsLabResearch"}
    with requests.get(url, headers=headers, timeout=60, stream=True) as response:
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        if "pdf" not in content_type and not url.lower().endswith(".pdf"):
            raise ValueError("La URL no parece corresponder a un archivo PDF.")
        with destination.open("wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 128):
                if chunk:
                    file.write(chunk)

    if destination.stat().st_size < 1000:
        destination.unlink(missing_ok=True)
        raise ValueError("El PDF descargado está vacío o incompleto.")
    return destination
