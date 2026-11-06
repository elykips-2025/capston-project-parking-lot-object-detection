
import csv
import random
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import (
    MobileNet_V3_Small_Weights,
    mobilenet_v3_small,
)

ROOT = Path("datasets/pklot")
MANIFEST = ROOT / "pklot_pilot.csv"
IMAGE_ROOT = ROOT / "pilot-images"
OUTPUT = Path("runs/occupancy/mobilenetv3_pilot")

SEED = 42
EPOCHS = 5
BATCH_SIZE = 32
LEARNING_RATE = 1e-4
IMAGE_SIZE = 160


class SquarePad:
    def __call__(self, image):
        width, height = image.size
        size = max(width, height)

        left = (size - width) // 2
        top = (size - height) // 2

        return ImageOps.expand(
            image,
            border=(
                left,
                top,
                size - width - left,
                size - height - top,
            ),
            fill=(128, 128, 128),
        )


class PKLotDataset(Dataset):
    def __init__(self, split, transform):
        self.samples = []
        self.transform = transform

        with MANIFEST.open(newline="") as file:
            for row in csv.DictReader(file):
                if row["split"] != split:
                    continue

                parts = Path(row["archive_path"]).parts
                path = IMAGE_ROOT / split / Path(*parts[2:])

                self.samples.append(
                    (path, int(row["label_id"]))
                )

        if not self.samples:
            raise ValueError(f"No samples found for {split}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        path, label = self.samples[index]

        with Image.open(path) as image:
            image = image.convert("RGB")
            image = self.transform(image)

        return image, label


def create_transforms():
    normalise = transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    )

    base = [
        SquarePad(),
        transforms.Resize(
            (IMAGE_SIZE, IMAGE_SIZE),
            interpolation=transforms.InterpolationMode.BILINEAR,
        ),
    ]

    train_transform = transforms.Compose([
        *base,
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.ToTensor(),
        normalise,
    ])

    val_transform = transforms.Compose([
        *base,
        transforms.ToTensor(),
        normalise,
    ])

    return train_transform, val_transform


def evaluate(model, loader, device):
    model.eval()

    confusion = torch.zeros(
        (2, 2), dtype=torch.int64
    )

    with torch.inference_mode():
        for images, labels in loader:
            images = images.to(device)

            predictions = model(images).argmax(dim=1).cpu()

            for actual, predicted in zip(labels, predictions):
                confusion[int(actual), int(predicted)] += 1

    correct = confusion.diag().sum().item()
    total = confusion.sum().item()
    accuracy = correct / total if total else 0

    return accuracy, confusion


def main():
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    device = torch.device(
        "mps" if torch.backends.mps.is_available() else "cpu"
    )

    OUTPUT.mkdir(parents=True, exist_ok=True)

    train_transform, val_transform = create_transforms()

    train_dataset = PKLotDataset("train", train_transform)
    val_dataset = PKLotDataset("val", val_transform)

    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=0,
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=0,
    )

    weights = MobileNet_V3_Small_Weights.DEFAULT
    model = mobilenet_v3_small(weights=weights)

    model.classifier[3] = nn.Linear(
        model.classifier[3].in_features,
        2,
    )

    model = model.to(device)

    optimiser = torch.optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
    )

    criterion = nn.CrossEntropyLoss()
    best_accuracy = -1.0

    print(f"Device: {device}")
    print(f"Training: {len(train_dataset):,}")
    print(f"Validation: {len(val_dataset):,}")

    for epoch in range(1, EPOCHS + 1):
        model.train()

        running_loss = 0.0
        correct = 0
        total = 0

        for images, labels in train_loader:
            images = images.to(device)
            labels = labels.to(device)

            optimiser.zero_grad(set_to_none=True)

            outputs = model(images)
            loss = criterion(outputs, labels)

            loss.backward()
            optimiser.step()

            running_loss += loss.item() * labels.size(0)
            correct += (
                outputs.argmax(dim=1) == labels
            ).sum().item()
            total += labels.size(0)

        train_loss = running_loss / total
        train_accuracy = correct / total

        val_accuracy, confusion = evaluate(
            model, val_loader, device
        )

        print(
            f"Epoch {epoch}/{EPOCHS} | "
            f"loss={train_loss:.4f} | "
            f"train_acc={train_accuracy:.4f} | "
            f"val_acc={val_accuracy:.4f}",
            flush=True,
        )

        print(
            f"Confusion matrix [actual rows, predicted columns]:\n"
            f"{confusion.numpy()}",
            flush=True,
        )

        if val_accuracy > best_accuracy:
            best_accuracy = val_accuracy

            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "epoch": epoch,
                    "val_accuracy": val_accuracy,
                    "class_names": ["empty", "occupied"],
                    "image_size": IMAGE_SIZE,
                },
                OUTPUT / "best.pt",
            )

            print("Saved new best checkpoint", flush=True)

    print(f"\nBest validation accuracy: {best_accuracy:.4f}")
    print(f"Checkpoint: {OUTPUT / 'best.pt'}")


if __name__ == "__main__":
    main()
