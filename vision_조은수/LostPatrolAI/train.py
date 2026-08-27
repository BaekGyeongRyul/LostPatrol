from ultralytics import YOLO

model = YOLO("yolo26n.pt")
model.train(
    data="data.yaml",
    epochs=30,
    imgsz=640,
    batch=8,
    device="cpu",
)
