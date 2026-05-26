import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.dem_import import import_dem, update_dem_registry, write_sidecar


def main() -> None:
    parser = argparse.ArgumentParser(description="Import/register a GeoTIFF DEM into the local data directory.")
    parser.add_argument("--source", required=True, type=Path, help="Source DEM GeoTIFF path.")
    parser.add_argument(
        "--out",
        type=Path,
        help="Output DEM path. Defaults to data/dem/<source-name>.tif",
    )
    parser.add_argument("--target-crs", help="Optional target CRS (example: EPSG:5179).")
    parser.add_argument(
        "--reproject",
        action="store_true",
        help="Allow reprojection when source CRS and --target-crs differ.",
    )
    parser.add_argument("--source-date", help="Optional source acquisition/publication date string.")
    parser.add_argument("--license", dest="license_name", help="Optional data license string.")
    parser.add_argument("--source-url", help="Optional source URL.")
    parser.add_argument("--name", help="Registry name. Defaults to output stem.")
    parser.add_argument("--registry", type=Path, help="Optional registry JSON path for dem_datasets entry updates.")
    args = parser.parse_args()

    source = args.source.resolve()
    if not source.exists():
        raise SystemExit(f"Source DEM does not exist: {source}")

    output = args.out.resolve() if args.out else (Path("data") / "dem" / source.name).resolve()
    metadata = import_dem(
        source_path=source,
        output_path=output,
        target_crs=args.target_crs,
        reproject_if_needed=args.reproject,
    )
    metadata["source_date"] = args.source_date
    metadata["license"] = args.license_name
    metadata["source_url"] = args.source_url

    sidecar_path = output.with_suffix(output.suffix + ".json")
    write_sidecar(sidecar_path, metadata)

    if args.registry:
        update_dem_registry(
            registry_path=args.registry,
            name=args.name or output.stem,
            metadata=metadata,
            source_date=args.source_date,
            license_name=args.license_name,
            source_url=args.source_url,
        )

    print(f"Imported DEM: {output}")
    print(f"Metadata sidecar: {sidecar_path}")
    if args.registry:
        print(f"Registry updated: {args.registry.resolve()}")


if __name__ == "__main__":
    main()
