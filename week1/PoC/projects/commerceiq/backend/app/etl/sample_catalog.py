"""Downloads a small, curated set of demo catalog images so users can try
Catalog Vision with one click, without needing their own product photos.

Source: marcusklasson/GroceryStoreDataset (GitHub), MIT License.
  https://github.com/marcusklasson/GroceryStoreDataset
  Paper: Klasson, M., Zhang, C., Kjellstrom, H. "A Hierarchical Grocery
         Store Image Dataset with Visual and Semantic Labels." WACV 2019.
  We pull only the repo's small `sample_images/{natural,iconic}` folders
  (10 grocery classes x 2 shots = 20 images, a few hundred KB total) via
  raw.githubusercontent.com — not the full ~5,000-image dataset — to keep
  first-run setup fast.
"""
import os

import requests

GROCERY_ITEMS = [
    "Alpro-Fresh-Soy-Milk",
    "Arla-Standard-Milk",
    "Banana",
    "Granny-Smith",
    "Green-Bell-Pepper",
    "Lemon",
    "Oatly-Natural-Oatghurt",
    "Pink-Lady",
    "Vine-Tomato",
    "Yellow-Onion",
]
BASE_URL = "https://raw.githubusercontent.com/marcusklasson/GroceryStoreDataset/master/sample_images"


def ensure_sample_images(data_dir: str) -> list[str]:
    out_dir = os.path.join(data_dir, "sample_images")
    os.makedirs(out_dir, exist_ok=True)
    paths: list[str] = []

    for item in GROCERY_ITEMS:
        for variant, remote_name in (("natural", f"{item}.jpg"), ("iconic", f"{item}_Iconic.jpg")):
            local_path = os.path.join(out_dir, f"{item}_{variant}.jpg")
            if not os.path.exists(local_path):
                url = f"{BASE_URL}/{variant}/{remote_name}"
                try:
                    resp = requests.get(url, timeout=30)
                    if resp.status_code == 200 and resp.content:
                        with open(local_path, "wb") as f:
                            f.write(resp.content)
                except requests.RequestException:
                    continue
            if os.path.exists(local_path):
                paths.append(local_path)
    return paths
