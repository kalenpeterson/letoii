#!/usr/bin/env python3
"""
main.py – scrape multiple spice vendors
---------------------------------------

New features
============
* --out-type {local,s3}           # default: local file
* All args can be set with env vars:
    DELAY, LIMIT, OUT, OUT_TYPE,
    S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY,
    S3_BUCKET, S3_OBJECT_NAME, S3_SECURE (true/false)

Examples
--------
# Local file (default)
python3 main.py --limit 10 --out data.csv

# Upload to MinIO
export S3_ENDPOINT="https://minio.mydomain.local:9000"
export S3_ACCESS_KEY="minioadmin"
export S3_SECRET_KEY="minioadmin"
export S3_BUCKET="spice-data"
python3 main.py --out-type s3 --out spices.csv
"""

import argparse, os, re, pandas as pd
from scrapers import get_vendor_modules

# ───────────────────────── CLI / ENV handling ─────────────────────────
def env_or_default(name: str, default):
    return type(default)(os.getenv(name, default))

parser = argparse.ArgumentParser()
parser.add_argument("--delay",    type=float,
                    default=env_or_default("DELAY", 2.0),
                    help="seconds to wait between requests")
parser.add_argument("--limit",    type=int,
                    default=env_or_default("LIMIT", 3),
                    help="max products *per vendor*")
parser.add_argument("--out",      default=env_or_default("OUT", "all_vendors_spices.csv"),
                    help="local filename (always) & S3 object name unless overridden")
parser.add_argument("--out-type", choices=["local", "s3"],
                    default=env_or_default("OUT_TYPE", "local"),
                    help="'local' → write file only, 's3' → upload to MinIO/S3")

# S3 / MinIO specific ENV overrides
S3_ENV_DEFAULTS = {
    "S3_ENDPOINT": "",
    "S3_ACCESS_KEY": "",
    "S3_SECRET_KEY": "",
    "S3_BUCKET": "",
    "S3_OBJECT_NAME": "",   # falls back to --out if empty
    "S3_SECURE": "true",    # 'true' or 'false'
}

args = parser.parse_args()

# ───────────────────────── Run each vendor ─────────────────────────
modules = get_vendor_modules()
rows = []
for name, mod in modules.items():
    if not hasattr(mod, "scrape"):
        continue
    try:
        vendor_rows = mod.scrape(limit=args.limit, delay=args.delay)
        print(f"{name}: collected {len(vendor_rows)} variant rows")
        rows.extend(vendor_rows)
    except Exception as exc:
        print(f"{name}: error {exc}")

# ───────────────────────── DataFrame & filter ─────────────────────────
df = pd.DataFrame(rows)

# Drop blends/bundles/boxes
exclude_re = re.compile(r"blend|seasoning|mix|rub|box|bundle|gift|set|kit", re.I)
df = df[~df["name"].str.contains(exclude_re, na=False)]

df.to_csv(args.out, index=False)
print(f"Saved {len(df)} rows → {args.out}")

# ───────────────────────── Optional S3 upload ─────────────────────────
if args.out_type == "s3":
    from minio import Minio
    from minio.error import S3Error

    cfg = {k: os.getenv(k, v) for k, v in S3_ENV_DEFAULTS.items()}
    if not all([cfg["S3_ENDPOINT"], cfg["S3_ACCESS_KEY"],
                cfg["S3_SECRET_KEY"], cfg["S3_BUCKET"]]):
        raise SystemExit("Missing one or more required S3_* env vars.")

    secure = cfg["S3_SECURE"].lower() != "false"
    object_name = cfg["S3_OBJECT_NAME"] or os.path.basename(args.out)

    client = Minio(
        cfg["S3_ENDPOINT"].replace("https://", "").replace("http://", ""),
        access_key=cfg["S3_ACCESS_KEY"],
        secret_key=cfg["S3_SECRET_KEY"],
        secure=secure,
    )

    # create bucket if it doesn't exist
    if not client.bucket_exists(cfg["S3_BUCKET"]):
        client.make_bucket(cfg["S3_BUCKET"])

    try:
        client.fput_object(
            bucket_name=cfg["S3_BUCKET"],
            object_name=object_name,
            file_path=args.out,
            content_type="text/csv",
        )
        print(f"✓ Uploaded {args.out} → s3://{cfg['S3_BUCKET']}/{object_name}")
    except S3Error as err:
        print(f"S3 upload failed: {err}")
