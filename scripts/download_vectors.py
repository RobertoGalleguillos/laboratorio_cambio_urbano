import os
import sys
from urllib.parse import urlparse


def _filename_from_url(url: str, fallback: str) -> str:
    path = urlparse(url).path
    name = os.path.basename(path)
    return name or fallback


def _download(url: str, dst_path: str) -> None:
    import requests

    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with open(dst_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def main() -> int:
    ide_url = os.getenv("IDE_COMUNA_URL", "").strip()
    ine_url = os.getenv("INE_MANZANAS_URL", "").strip()
    osm_url = os.getenv("OSM_ROADS_URL", "").strip()

    if not (ide_url and ine_url and osm_url):
        print("Faltan URLs. Define estas variables de entorno:")
        print("  IDE_COMUNA_URL  (limite comunal)")
        print("  INE_MANZANAS_URL (manzanas censales)")
        print("  OSM_ROADS_URL    (red vial)")
        return 1

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(repo_root, "data", "vector")
    os.makedirs(out_dir, exist_ok=True)

    downloads = [
        (ide_url, _filename_from_url(ide_url, "limite_comuna.zip")),
        (ine_url, _filename_from_url(ine_url, "manzanas_censales.zip")),
        (osm_url, _filename_from_url(osm_url, "red_vial.geojson")),
    ]

    for url, name in downloads:
        dst = os.path.join(out_dir, name)
        print(f"Descargando {url} -> {dst}")
        _download(url, dst)

    print("Descargas completas. Si los archivos vienen en .zip, descomprime en data\\vector.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
