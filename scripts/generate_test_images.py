"""Generate a placeholder test-image set for local pipeline testing.

These are simple synthetic illustrations, not real site photos -- they exist so
the Capture -> Gemini -> Firestore pipeline can be exercised end-to-end before
real construction-site photos are available. Swap assets/test-images/ with real
photos before recording the demo video.
"""

import pathlib
import random

from PIL import Image, ImageDraw

OUT_DIR = pathlib.Path(__file__).resolve().parent.parent / "assets" / "test-images"
OUT_DIR.mkdir(parents=True, exist_ok=True)

W, H = 800, 600
SKY = (176, 207, 231)
GROUND = (158, 145, 125)
CONCRETE = (190, 190, 185)


def _base(rng: random.Random) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), SKY)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, H * 0.45, W, H], fill=GROUND)
    draw.rectangle([0, H * 0.45, W, H * 0.55], fill=CONCRETE)
    return img, draw


def unprotected_edge(path: pathlib.Path, ambiguous: bool, rng: random.Random) -> None:
    img, draw = _base(rng)
    edge_y = H * 0.55
    draw.rectangle([0, H * 0.55, W, H * 0.62], fill=(120, 115, 110))
    if not ambiguous:
        draw.text((40, 30), "No guardrail at floor edge", fill=(40, 40, 40))
    else:
        for x in range(0, W, 14):
            draw.ellipse([x, edge_y - 40, x + 6, edge_y + 60], fill=(200, 200, 200, 120))
        draw.text((40, 30), "Partial view, scaffold in foreground", fill=(40, 40, 40))
    img.save(path)


def obstructed_walkway(path: pathlib.Path, ambiguous: bool, rng: random.Random) -> None:
    img, draw = _base(rng)
    draw.rectangle([W * 0.3, H * 0.55, W * 0.7, H], fill=(210, 200, 170))
    draw.text((40, 30), "Designated walkway", fill=(40, 40, 40))
    if not ambiguous:
        for i in range(4):
            x = W * 0.35 + i * 40
            draw.rectangle([x, H * 0.7, x + 60, H * 0.95], fill=(150, 100, 60))
        draw.text((40, 60), "Materials stacked across path", fill=(120, 20, 20))
    else:
        draw.rectangle([W * 0.45, H * 0.8, W * 0.55, H * 0.9], fill=(150, 100, 60))
        draw.text((40, 60), "Distant, partially occluded view", fill=(40, 40, 40))
    img.save(path)


def _stick_worker(draw: ImageDraw.ImageDraw, x: int, y: int, hard_hat: bool, hi_vis: bool) -> None:
    draw.line([x, y, x, y + 80], fill=(30, 30, 30), width=4)
    head_color = (255, 210, 0) if hard_hat else (210, 180, 140)
    draw.ellipse([x - 12, y - 24, x + 12, y], fill=head_color)
    body_color = (255, 140, 0) if hi_vis else (90, 90, 150)
    draw.line([x - 20, y + 20, x + 20, y + 20], fill=body_color, width=10)


def ppe_concern(path: pathlib.Path, ambiguous: bool, rng: random.Random) -> None:
    img, draw = _base(rng)
    if not ambiguous:
        _stick_worker(draw, int(W * 0.5), int(H * 0.35), hard_hat=False, hi_vis=False)
        draw.text((40, 30), "Worker without hard hat or hi-vis", fill=(120, 20, 20))
    else:
        _stick_worker(draw, int(W * 0.5), int(H * 0.35), hard_hat=True, hi_vis=False)
        draw.rectangle([W * 0.42, H * 0.25, W * 0.58, H * 0.5], outline=(80, 80, 80), width=3)
        draw.text((40, 30), "Partial occlusion by equipment", fill=(40, 40, 40))
    img.save(path)


def main() -> None:
    rng = random.Random(7)
    specs = [
        ("unprotected_edge", unprotected_edge, 4),
        ("obstructed_walkway", obstructed_walkway, 4),
        ("ppe_concern", ppe_concern, 4),
    ]
    count = 0
    for scenario, fn, n in specs:
        for i in range(n):
            ambiguous = i >= n - 2
            suffix = "ambiguous" if ambiguous else "clear"
            fname = OUT_DIR / f"{scenario}_{i + 1:02d}_{suffix}.jpg"
            fn(fname, ambiguous, rng)
            count += 1
    print(f"Wrote {count} placeholder test images to {OUT_DIR}")


if __name__ == "__main__":
    main()
