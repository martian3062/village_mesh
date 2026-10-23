"""Export a bounded point trace from The Well HDF5 velocity field to Unreal CSV.

The resulting signal is normalized and retimed for visual wind, not a local
Navier-Stokes solver. No model training or full dataset download is performed.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import h5py
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HF_REVISION = "1bca59aef4f2167f1d07d875ace6ea8c646d7cce"
DEMO_URL = ("https://huggingface.co/datasets/polymathic-ai/shear_flow/resolve/" + HF_REVISION
            + "/data/test/shear_flow_Reynolds_1e4_Schmidt_1e-1.hdf5")


def point_trace(handle, trajectory=0, point=(128, 170), frames=48):
    if not 2 <= frames <= 512:
        raise ValueError("frames must be in [2, 512]")
    ds = handle["t1_fields/velocity"]
    if (ds.ndim != 5 or ds.shape[-1] != 2 or not ds.attrs.get("sample_varying", False)
            or not ds.attrs.get("time_varying", False)
            or not np.array_equal(ds.attrs.get("dim_varying"), [True, True])):
        raise ValueError("Expected The Well 2D sample/time-varying Cartesian velocity [B,T,X,Y,2]")
    grid = handle.attrs.get("grid_type", "cartesian")
    if isinstance(grid, bytes):
        grid = grid.decode()
    if grid != "cartesian":
        raise ValueError("Only Cartesian velocity data is supported")
    if not (0 <= trajectory < ds.shape[0] and 0 <= point[0] < ds.shape[2] and 0 <= point[1] < ds.shape[3]):
        raise ValueError("Trajectory or sample point is outside the dataset")
    indices = np.unique(np.linspace(0, ds.shape[1] - 1, min(frames, ds.shape[1])).astype(int))
    # Read individual points, never materialize the entire GB-scale tensor.
    vectors = np.array([ds[trajectory, int(i), point[0], point[1], :] for i in indices], dtype=float)
    times_ds = handle["dimensions/time"]
    times = np.array(times_ds[trajectory] if times_ds.attrs.get("sample_varying", False) else times_ds[:])[indices]
    if not np.isfinite(vectors).all() or not np.isfinite(times).all() or not np.all(np.diff(times) > 0):
        raise ValueError("Velocity and time must be finite; time must strictly increase")
    return times, vectors


def normalize_trace(times, vectors, duration=120.0):
    if duration <= 0 or len(times) < 2:
        raise ValueError("A positive duration and at least two frames are required")
    peak = float(np.max(np.linalg.norm(vectors, axis=1)))
    if peak < 1e-9:
        raise ValueError("Cannot normalize a zero velocity field")
    normalized = vectors / peak
    # Duplicate the first sample at the loop end for continuous playback.
    t = (times - times[0]) / (times[-1] - times[0]) * (duration * 0.95)
    return np.append(t, duration), np.vstack((normalized, normalized[0])), peak


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", help="Local The Well 2D HDF5 file")
    parser.add_argument("--demo", action="store_true", help="Range-read a small trace from the pinned public shear-flow file")
    parser.add_argument("--point", type=int, nargs=2, default=[128, 170])
    parser.add_argument("--trajectory", type=int, default=0)
    parser.add_argument("--frames", type=int, default=48)
    parser.add_argument("--duration", type=float, default=120.0)
    parser.add_argument("--output", type=Path, default=ROOT / "Content/Well/wind.csv")
    args = parser.parse_args()
    if bool(args.source) == args.demo:
        parser.error("Choose exactly one of --source or --demo")
    if args.demo:
        import fsspec
        remote = fsspec.open(DEMO_URL, block_size=65536, cache_type="blockcache")
        with remote as stream, h5py.File(stream, "r") as handle:
            times, vectors = point_trace(handle, args.trajectory, args.point, args.frames)
        source = DEMO_URL
    else:
        with h5py.File(args.source, "r") as handle:
            times, vectors = point_trace(handle, args.trajectory, args.point, args.frames)
        source = Path(args.source).name
    t, v, peak = normalize_trace(times, vectors, args.duration)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("time", "x", "y", "z"))
        for time, vec in zip(t, v):
            writer.writerow((f"{time:.6f}", f"{vec[0]:.8f}", f"{vec[1]:.8f}", "0"))
    metadata = dict(source=source, repository="https://github.com/PolymathicAI/the_well",
                    repository_commit="aac88c0b5eb9cbe4b7b2797eaaa550a43706fb44",
                    license="CC-BY-4.0" if args.demo else "See source dataset license",
                    attribution="The Well / Polymathic AI; shear flow simulations by Rudy Morel, CCM, Flatiron Institute",
                    changes="Point trace, peak-normalized, retimed, XY mapped to horizontal wind; looping endpoint added",
                    disclaimer="Art-directed playback; not a validated atmospheric simulation or benchmark",
                    trajectory=args.trajectory, point=args.point, sample_count=len(t),
                    source_time_range=[float(times[0]), float(times[-1])], source_velocity_peak=peak,
                    csv_sha256=hashlib.sha256(args.output.read_bytes()).hexdigest())
    args.output.with_suffix(".source.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print("WELL_WIND_EXPORT_OK", len(t), "samples", args.output)


if __name__ == "__main__":
    main()
