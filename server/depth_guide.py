#!/usr/bin/env python3
"""Build a soft relative-depth composition guide from a source image."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


MODEL_SIZE = 518
MAX_SOURCE_SIDE = 1600
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--structure", type=int, default=170)
    parser.add_argument("--detail", type=int, default=8)
    parser.add_argument("--smoothing", type=float, default=8)
    parser.add_argument("--contrast", type=float, default=0.95)
    return parser.parse_args()


def load_image(path: Path) -> Image.Image:
    with Image.open(path) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
    if max(image.size) > MAX_SOURCE_SIDE:
        image.thumbnail((MAX_SOURCE_SIDE, MAX_SOURCE_SIDE), Image.Resampling.LANCZOS)
    return image


def preprocess(image: Image.Image) -> np.ndarray:
    resized = image.resize((MODEL_SIZE, MODEL_SIZE), Image.Resampling.BICUBIC)
    array = np.asarray(resized, dtype=np.float32) / 255.0
    array = (array - IMAGENET_MEAN) / IMAGENET_STD
    return array.transpose(2, 0, 1)[None].astype(np.float32)


def normalize_depth(depth: np.ndarray) -> Image.Image:
    values = np.squeeze(depth).astype(np.float32)
    low, high = np.percentile(values, (2.0, 98.0))
    if high <= low:
        low, high = float(values.min()), float(values.max())
    normalized = np.clip((values - low) / max(high - low, 1e-6), 0.0, 1.0)
    return Image.fromarray((normalized * 255.0).astype(np.uint8))


def render_depth(
    raw_depth: Image.Image,
    output_size: tuple[int, int],
    structure: int,
    detail: int,
    smoothing: float,
    contrast: float,
) -> Image.Image:
    width, height = output_size
    longest = max(width, height)
    structure = max(64, min(MODEL_SIZE, structure))
    scale = min(1.0, structure / max(longest, 1))
    reduced_size = (
        max(1, round(width * scale)),
        max(1, round(height * scale)),
    )

    full = raw_depth.resize(output_size, Image.Resampling.BICUBIC)
    broad = full.resize(reduced_size, Image.Resampling.BILINEAR)
    broad = broad.resize(output_size, Image.Resampling.BICUBIC)
    if smoothing > 0:
        broad = broad.filter(ImageFilter.GaussianBlur(radius=smoothing))

    detail_ratio = max(0.0, min(1.0, detail / 100.0))
    merged = Image.blend(broad, full, detail_ratio)
    merged = ImageEnhance.Contrast(merged).enhance(max(0.5, min(1.8, contrast)))
    return merged.filter(ImageFilter.GaussianBlur(radius=0.6))


def build_depth_guide(args: argparse.Namespace) -> None:
    if not args.model.exists():
        raise FileNotFoundError(f"Depth Anything model not found: {args.model}")
    image = load_image(args.input)
    options = ort.SessionOptions()
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    session = ort.InferenceSession(
        str(args.model),
        sess_options=options,
        providers=["CPUExecutionProvider"],
    )
    input_name = session.get_inputs()[0].name
    output = session.run(None, {input_name: preprocess(image)})[0]
    raw_depth = normalize_depth(output)
    rendered = render_depth(
        raw_depth,
        image.size,
        args.structure,
        args.detail,
        args.smoothing,
        args.contrast,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rendered.save(args.output, format="PNG", optimize=True)


if __name__ == "__main__":
    build_depth_guide(parse_args())
