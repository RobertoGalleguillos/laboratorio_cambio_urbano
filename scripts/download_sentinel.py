import argparse
import os
import shutil

import ee
import geemap


PROJECT_ID = "geoinformatica-lab"
DRIVE_FOLDER_ID = "1fgVm3omjUBq0Fm0xAxqVudoD1J2M0MeK"


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _classify_dest(filename: str, repo_root: str) -> str:
    name = filename.lower()
    raw_exts = {".tif", ".tiff"}
    vector_exts = {
        ".gpkg",
        ".shp",
        ".shx",
        ".dbf",
        ".prj",
        ".cpg",
        ".qpj",
        ".qmd",
        ".geojson",
    }

    ext = os.path.splitext(name)[1]
    if ext in raw_exts:
        return os.path.join(repo_root, "data", "raw")
    if ext in vector_exts:
        return os.path.join(repo_root, "data", "vector")
    return os.path.join(repo_root, "data", "raw")


def _move_downloaded_files(download_root: str, repo_root: str) -> None:
    for root, _dirs, files in os.walk(download_root):
        for filename in files:
            src = os.path.join(root, filename)
            dest_dir = _classify_dest(filename, repo_root)
            _ensure_dir(dest_dir)
            dst = os.path.join(dest_dir, filename)
            if os.path.abspath(src) == os.path.abspath(dst):
                continue
            if os.path.exists(dst):
                os.remove(dst)
            shutil.move(src, dst)


def download_from_drive() -> None:
    try:
        import gdown
    except ImportError:
        print("Falta gdown. Instala con: python -m pip install gdown")
        return

    repo_root = _repo_root()
    temp_dir = os.path.join(repo_root, "data", "_drive_tmp")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    _ensure_dir(temp_dir)

    url = f"https://drive.google.com/drive/folders/{DRIVE_FOLDER_ID}"
    gdown.download_folder(url=url, output=temp_dir, quiet=False, use_cookies=False)
    _move_downloaded_files(temp_dir, repo_root)
    shutil.rmtree(temp_dir, ignore_errors=True)


def export_sentinel_gee() -> None:
    # Inicializar Earth Engine (asegurate de autenticarte primero con: earthengine authenticate)
    ee.Initialize(project=PROJECT_ID)

    # Area de estudio: Comuna Estacion Central (aprox. bounding box)
    # Si cuentas con el limite oficial, reemplaza este rectangulo por la geometria exacta.
    area = ee.Geometry.Rectangle([-70.74, -33.52, -70.62, -33.40])

    # Funcion para enmascarar nubes en Sentinel-2
    def mask_clouds_s2(image):
        qa = image.select("QA60")
        cloud_mask = qa.bitwiseAnd(1 << 10).eq(0).And(qa.bitwiseAnd(1 << 11).eq(0))
        return image.updateMask(cloud_mask)

    # Coleccion Sentinel-2 para multiples anos (al menos 5 anos y 4 fechas)
    years = [2018, 2020, 2022, 2024]

    for year in years:
        # Filtrar por fecha (verano austral: dic-feb)
        start = f"{year}-12-01"
        end = f"{year + 1}-02-28"

        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(area)
            .filterDate(start, end)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 10))
            .map(mask_clouds_s2)
        )

        # Crear compuesto mediana
        composite = collection.median().clip(area)

        # Exportar
        task = ee.batch.Export.image.toDrive(
            image=composite.select(["B2", "B3", "B4", "B8", "B11", "B12"]),
            description=f"sentinel2_{year}",
            folder="cambio_urbano",
            region=area,
            scale=10,
            maxPixels=1e9,
        )
        task.start()
        print(f"Exportando {year}...")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Descarga/exporta datos para el laboratorio de cambio urbano."
    )
    parser.add_argument(
        "--gee",
        action="store_true",
        help="Exporta Sentinel-2 a Google Drive via Earth Engine.",
    )
    parser.add_argument(
        "--drive",
        action="store_true",
        help="Descarga datos desde Google Drive y los ordena en data/raw y data/vector.",
    )

    args = parser.parse_args()
    if not (args.gee or args.drive):
        parser.print_help()
        return 1

    if args.gee:
        export_sentinel_gee()
    if args.drive:
        download_from_drive()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
