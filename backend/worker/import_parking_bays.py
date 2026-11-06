
import json
import uuid
from pathlib import Path

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import Camera, ParkingBay, ParkingSite


MAPPING_PATH = Path(
    "datasets/video-mapping/parksight-bay-mapping.json"
)

SITE_ID = uuid.UUID("88ba90de-72bc-463a-baa6-d14992dbf1f9")
CAMERA_ID = uuid.UUID("98116c54-fc85-46a9-a97b-c507891afda2")

ACCESSIBLE_BAYS = {
    f"A{i:02d}" for i in range(22, 28)
}


def main():
    with MAPPING_PATH.open() as f:
        mapping = json.load(f)

    bays = mapping["bays"]

    if len(bays) != 27:
        raise ValueError(f"Expected 27 bays, found {len(bays)}")

    codes = [bay["id"] for bay in bays]

    if len(set(codes)) != len(codes):
        raise ValueError("Duplicate bay identifiers in mapping")

    with SessionLocal.begin() as db:
        site = db.get(ParkingSite, SITE_ID)
        camera = db.get(Camera, CAMERA_ID)

        if site is None:
            raise ValueError("Parking site not found")

        if camera is None or camera.site_id != SITE_ID:
            raise ValueError("Camera does not belong to parking site")

        created = 0
        updated = 0

        for bay in bays:
            code = bay["id"]
            points = bay["points"]

            if len(points) < 3 or any(
                not isinstance(point, dict)
                or not isinstance(point.get("x"), (int, float))
                or not isinstance(point.get("y"), (int, float))
                for point in points
            ):
                raise ValueError(f"Invalid polygon for {code}")

            bay_type = (
                "accessible"
                if code in ACCESSIBLE_BAYS
                else "standard"
            )

            existing = db.scalar(
                select(ParkingBay).where(
                    ParkingBay.site_id == SITE_ID,
                    ParkingBay.bay_code == code,
                )
            )

            if existing:
                existing.camera_id = CAMERA_ID
                existing.bay_type = bay_type
                existing.polygon = points
                updated += 1
            else:
                db.add(
                    ParkingBay(
                        site_id=SITE_ID,
                        camera_id=CAMERA_ID,
                        bay_code=code,
                        bay_type=bay_type,
                        polygon=points,
                    )
                )
                created += 1

    print(f"Imported {len(bays)} bays")
    print(f"Created: {created}")
    print(f"Updated: {updated}")
    print(f"Standard: {len(bays) - len(ACCESSIBLE_BAYS)}")
    print(f"Accessible: {len(ACCESSIBLE_BAYS)}")


if __name__ == "__main__":
    main()
