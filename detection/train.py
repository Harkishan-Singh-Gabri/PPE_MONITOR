from ultralytics import YOLO
from utils.logger import log
from utils.config_loader import load_config

config=load_config()

def train():
    model=YOLO("yolov8n.pt")
    log.info("Starting PPE model training...")

    results=model.train(
        data=config["detection"]["data_yaml"],
        epochs=50,
        imgsz=640,
        batch=16,
        device=config["detection"]["device"],
        project="models",
        name="ppe_training",
        save=True,
        plots=True
    )

    log.info("Training complete")

if __name__=='__main__':
    train()