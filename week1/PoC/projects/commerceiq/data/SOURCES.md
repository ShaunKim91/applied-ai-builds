# Data sources

Both datasets below are downloaded automatically — you never need to do this
by hand. `backend/app/main.py`'s startup hook calls the same functions shown
here in a background thread on first boot; `scripts/download_data.sh` is a
manual trigger if you ever want to force a re-check.

## 1. UCI "Online Retail" — demand forecasting

- **Source**: UCI Machine Learning Repository, dataset #352
  <https://archive.ics.uci.edu/dataset/352/online+retail>
- **Direct download**: <https://archive.ics.uci.edu/static/public/352/online+retail.zip> (22.6 MB, contains `Online Retail.xlsx`)
- **License**: CC BY 4.0 (Creative Commons Attribution 4.0 International)
- **Citation**: Chen, Daqing. "Online Retail." UCI Machine Learning Repository, 2015. <https://doi.org/10.24432/C5BW33>
- **Content**: 541,909 real transactions from a UK-based online retailer, 2010-12-01 to 2011-12-09 (`InvoiceNo`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `UnitPrice`, `CustomerID`, `Country`).
- **What CommerceIQ does with it**: `backend/app/etl/online_retail.py::ensure_online_retail_daily()` downloads + extracts the zip once, drops cancelled orders (`InvoiceNo` starting with "C") and non-positive quantity/price rows, computes `revenue = Quantity * UnitPrice`, and resamples to a daily revenue time series. The result is cached as `data/processed/online_retail_daily.parquet` so subsequent boots skip the ~540k-row re-parse.
- **Download it yourself** (outside the app, for inspection): `curl -L -o online_retail.zip https://archive.ics.uci.edu/static/public/352/online+retail.zip && unzip online_retail.zip`

## 2. GroceryStoreDataset (sample subset) — catalog vision demo images

- **Source**: `marcusklasson/GroceryStoreDataset` on GitHub
  <https://github.com/marcusklasson/GroceryStoreDataset>
- **Paper**: Klasson, M., Zhang, C., Kjellström, H. "A Hierarchical Grocery Store Image Dataset with Visual and Semantic Labels." *WACV 2019*.
- **License**: MIT License (repository root `LICENSE` file, Copyright (c) 2019 Marcus Klasson)
- **What CommerceIQ downloads**: only the repository's small `sample_images/{natural,iconic}/` folders — **10 grocery classes × 2 shots = 20 images** (Alpro Fresh Soy Milk, Arla Standard Milk, Banana, Granny Smith, Green Bell Pepper, Lemon, Oatly Natural Oatghurt, Pink Lady, Vine Tomato, Yellow Onion), a few hundred KB total — **not** the full ~5,000-image dataset, to keep first-run setup fast. Fetched directly via `raw.githubusercontent.com` (no `git clone` needed).
- **What CommerceIQ does with it**: `backend/app/etl/sample_catalog.py::ensure_sample_images()` downloads each file once to `data/sample_images/`, used by Catalog Vision's "try a sample" one-click classification flow so users can test the feature without their own product photos.
- **Download the full dataset yourself**: `git clone https://github.com/marcusklasson/GroceryStoreDataset.git`

## 3. Pretrained model weights (not "datasets," but also downloaded automatically)

| Model | Hub | Size (approx.) | Used for |
|---|---|---|---|
| `WinKawaks/vit-tiny-patch16-224` | HuggingFace | ~23 MB | Image classification |
| `segmind/tiny-sd` | HuggingFace | ~1 GB | Text-to-image generation |
| `intfloat/multilingual-e5-small` | HuggingFace | ~470 MB | Embeddings / semantic search |
| `Qwen/Qwen2.5-0.5B-Instruct` | HuggingFace | ~2 GB (fp32) | Local narrative LLM |

All four are cached in the `commerceiq_hf_cache` Docker named volume after first download, so restarts never re-download them.
