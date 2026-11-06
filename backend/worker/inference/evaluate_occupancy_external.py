
import csv
from pathlib import Path

import torch
from PIL import Image
from torch import nn
from torchvision import transforms
from torchvision.models import mobilenet_v3_small

from worker.inference.train_occupancy_classifier import SquarePad

IMAGE_DIR = Path("datasets/rectified-bays")
CHECKPOINT = Path("runs/occupancy/mobilenetv3_pilot/best.pt")
OUTPUT = Path("runs/occupancy/mobilenetv3_pilot/external_results.csv")

CLASS_NAMES = ["empty", "occupied"]


def main():
    device = torch.device(
        "mps" if torch.backends.mps.is_available() else "cpu"
    )

    checkpoint = torch.load(
        CHECKPOINT,
        map_location="cpu",
        weights_only=True,
    )

    model = mobilenet_v3_small(weights=None)
    model.classifier[3] = nn.Linear(
        model.classifier[3].in_features, 2
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device).eval()

    image_size = checkpoint["image_size"]

    transform = transforms.Compose([
        SquarePad(),
        transforms.Resize(
            (image_size, image_size),
            interpolation=transforms.InterpolationMode.BILINEAR,
        ),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        ),
    ])

    images = sorted(IMAGE_DIR.glob("*.jpg"))
    results = []
    confusion = [[0, 0], [0, 0]]

    for path in images:
        if path.name.startswith("mapping-tests_"):
            actual = 0
        elif path.name.startswith("occupied-tests_"):
            actual = 1
        else:
            continue

        with Image.open(path) as image:
            tensor = transform(image.convert("RGB")).unsqueeze(0)
            tensor = tensor.to(device)

        with torch.inference_mode():
            logits = model(tensor)
            probabilities = torch.softmax(logits, dim=1)[0].cpu()

        predicted = int(probabilities.argmax())
        confidence = float(probabilities[predicted])
        occupied_probability = float(probabilities[1])

        confusion[actual][predicted] += 1

        results.append({
            "bay": path.stem,
            "actual": CLASS_NAMES[actual],
            "predicted": CLASS_NAMES[predicted],
            "confidence": round(confidence, 6),
            "occupied_probability": round(occupied_probability, 6),
            "correct": actual == predicted,
        })

    if len(results) != 24:
        raise RuntimeError(
            f"Expected 24 bay crops, found {len(results)}"
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(results[0].keys()),
        )
        writer.writeheader()
        writer.writerows(results)

    print(f"Device: {device}")
    print(f"Checkpoint epoch: {checkpoint['epoch']}")
    print()
    print(
        f"{'Bay':<23} {'Actual':<10} "
        f"{'Predicted':<10} {'Confidence':>10} {'Result':>8}"
    )

    for row in results:
        status = "PASS" if row["correct"] else "FAIL"
        print(
            f"{row['bay']:<23} "
            f"{row['actual']:<10} "
            f"{row['predicted']:<10} "
            f"{row['confidence']:>10.4f} "
            f"{status:>8}"
        )

    correct = sum(row["correct"] for row in results)
    accuracy = correct / len(results)

    # Actual occupied, predicted empty: unsafe false vacancy.
    false_vacant = confusion[1][0]

    occupied_recall = (
        confusion[1][1] / sum(confusion[1])
        if sum(confusion[1]) else 0
    )
    empty_recall = (
        confusion[0][0] / sum(confusion[0])
        if sum(confusion[0]) else 0
    )

    print("\nExternal evaluation")
    print(f"Accuracy: {correct}/{len(results)} ({accuracy:.2%})")
    print(f"Occupied recall: {occupied_recall:.2%}")
    print(f"Empty recall: {empty_recall:.2%}")
    print(f"False-vacant predictions: {false_vacant}")

    print("\nConfusion matrix")
    print("                  Pred empty  Pred occupied")
    print(f"Actual empty      {confusion[0][0]:>10} {confusion[0][1]:>14}")
    print(f"Actual occupied   {confusion[1][0]:>10} {confusion[1][1]:>14}")

    print(f"\nResults saved: {OUTPUT}")


if __name__ == "__main__":
    main()
