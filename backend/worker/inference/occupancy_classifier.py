
from pathlib import Path

import torch
from PIL import Image
from torch import nn
from torchvision import transforms
from torchvision.models import mobilenet_v3_small

from worker.inference.occupancy_policy import decide_occupancy


class SquarePad:
    def __call__(self, image):
        width, height = image.size
        size = max(width, height)

        left = (size - width) // 2
        top = (size - height) // 2

        from PIL import ImageOps

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


class OccupancyClassifier:
    def __init__(self, checkpoint_path, device=None):
        self.device = torch.device(
            device or (
                "mps"
                if torch.backends.mps.is_available()
                else "cpu"
            )
        )

        checkpoint = torch.load(
            Path(checkpoint_path),
            map_location="cpu",
            weights_only=True,
        )

        if checkpoint.get("class_names") != ["empty", "occupied"]:
            raise ValueError("Unexpected checkpoint class ordering")

        self.model = mobilenet_v3_small(weights=None)
        self.model.classifier[3] = nn.Linear(
            self.model.classifier[3].in_features,
            2,
        )
        self.model.load_state_dict(
            checkpoint["model_state_dict"]
        )
        self.model.to(self.device).eval()

        self.transform = transforms.Compose([
            SquarePad(),
            transforms.Resize(
                (checkpoint["image_size"], checkpoint["image_size"]),
                interpolation=transforms.InterpolationMode.BILINEAR,
            ),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

    @torch.inference_mode()
    def predict(self, image: Image.Image):
        tensor = self.transform(
            image.convert("RGB")
        ).unsqueeze(0).to(self.device)

        logits = self.model(tensor)
        occupied_probability = (
            torch.softmax(logits, dim=1)[0, 1].item()
        )

        return decide_occupancy(occupied_probability)

    def predict_file(self, image_path):
        with Image.open(image_path) as image:
            return self.predict(image)


if __name__ == "__main__":
    classifier = OccupancyClassifier(
        "runs/occupancy/mobilenetv3_pilot/best.pt"
    )

    for filename in (
        "mapping-tests_A01.jpg",
        "occupied-tests_A06.jpg",
        "occupied-tests_A07.jpg",
        "occupied-tests_A14.jpg",
    ):
        result = classifier.predict_file(
            Path("datasets/rectified-bays") / filename
        )

        print(
            f"{filename:<26} "
            f"state={result.state.value:<8} "
            f"p_occupied={result.occupied_probability:.4f} "
            f"available={result.available}"
        )
