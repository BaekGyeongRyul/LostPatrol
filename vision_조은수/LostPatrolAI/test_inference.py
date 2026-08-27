from pathlib import Path

from ultralytics import YOLO

SOURCE = "test/images"

weight_candidates = list(Path("runs").rglob("best.pt")) + list(Path("weights").rglob("*.pt"))
if not weight_candidates:
    raise FileNotFoundError("No .pt weights found - run train.py first")
WEIGHTS = max(weight_candidates, key=lambda p: p.stat().st_mtime)
print("using weights:", WEIGHTS)

model = YOLO(str(WEIGHTS))
results = model.predict(source=SOURCE, save=True, conf=0.25)

for r in results:
    print(r.path, "->", len(r.boxes), "detections")
    for box in r.boxes:
        cls_name = model.names[int(box.cls)]
        print(f"  {cls_name}: conf={float(box.conf):.2f}")

print("annotated images saved under:", Path(results[0].save_dir) if results else "N/A")
