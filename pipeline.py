"""Orchestrator: run the full pipeline end-to-end.

    python pipeline.py            # ingest -> transform -> load -> dashboard
    python pipeline.py --no-fetch # skip API calls, reuse latest raw file
"""
import sys
import time

import ingest
import transform_load
import build_dashboard


def main():
    t0 = time.time()
    if "--no-fetch" not in sys.argv:
        print("[1/3] Ingesting from Open-Meteo...")
        ingest.run()
    else:
        print("[1/3] Skipping fetch (reusing latest raw file)")
    print("[2/3] Transforming + loading into DuckDB...")
    transform_load.run()
    print("[3/3] Building dashboard...")
    build_dashboard.run()
    print(f"Done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
