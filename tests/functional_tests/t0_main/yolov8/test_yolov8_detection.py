from ultralytics.yolo.engine.model import YOLO
from wandb.yolov8 import add_callbacks


def main():
    model = YOLO("yolov8n.pt")
    model = add_callbacks(model)
    model.train(
        data="coco128.yaml",
        epochs=2,
        imgsz=160,
    )


if __name__ == "__main__":
    main()