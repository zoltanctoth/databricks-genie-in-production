> Research appendix. Compiled 2026-10-01 from the official Databricks docs and cited sources by a research agent; every fact carries its source URL and the page "Last updated" date. Re-verify anything dated before you build on it.
>
> Platform note (2026-10-02): the build moved from Databricks Free Edition to a standard workspace (decision D1 in `docs/01-requirements-and-risks.md`). Free Edition limits quoted below are kept as research and no longer constrain the design.

# Dataset research: Inside Airbnb on Databricks (Genie Agents / metric views / bundles course)

Researched 2026-10-01 via live scrapes and HTTP HEAD requests. Sizes are `Content-Length` bytes from `data.insideairbnb.com`; listing counts are from Inside Airbnb "Explore" pages (June 2026 snapshot).

## 1. Inside Airbnb: license, files, dictionary, sizes, snapshots

**License.** Get-the-data page: data is licensed **CC BY 4.0**. The Data Policies page adds non-binding *community guidelines*: take only what you need, do not scrape the site, "do not republish the data", download once (not per run), attribute and cite, and "Instructors, please take note… consider contributing to the project if your course relies on the data." Free data = last ~12 months (quarterly); older data is archived and must be requested (may be refused or charged for uses outside the housing-activism mission).

**Files per city/snapshot.**
- `data/` (gzipped): `listings.csv.gz` (~75 columns), `calendar.csv.gz` (365 rows/listing: date, available, price, adjusted_price, min/max nights), `reviews.csv.gz` (listing_id, id, date, reviewer_id, reviewer_name, comments).
- `visualisations/`: `listings.csv` (18-column summary), `reviews.csv` (listing_id, date), `neighbourhoods.csv`, `neighbourhoods.geojson`.
Some small cities expose only listings (and sometimes reviews); Budapest, Amsterdam, London, NYC have the full set. New country-level "regional archive files" exist for NL and UK (not Hungary).

**Data dictionary.** Google Sheet `1iWCNJcSutYqpULSQHlNyGInUvHg2BoUGoNRIGa6Szc4`, tab "listings.csv detail v4.7" (March 2026). Key fields: `id`, `scrape_id`, `last_scraped`, `source`, `host_id/host_since/host_is_superhost/host_response_rate`, `neighbourhood_cleansed`, `neighbourhood_group_cleansed`, lat/long, `property_type`, `room_type`, `accommodates`, `bathrooms_text`, `bedrooms`, `beds`, `amenities` (JSON array), `price` (local currency; leading `$` is an export artifact), `minimum_nights`, `availability_30/60/90/365`, `number_of_reviews(_ltm/_l30d)`, `first/last_review`, `review_scores_*`, `license`, `instant_bookable`, `calculated_host_listings_count*`, `reviews_per_month`. Natural star schema: listing, host, neighbourhood, date dims; calendar and review facts; metric views for occupancy proxy, ADR, review velocity.

**Sizes and counts (June 2026).**

| City (snapshot) | Listings | listings.csv.gz | calendar.csv.gz (~rows) | reviews.csv.gz | summary listings.csv |
|---|---|---|---|---|---|
| Budapest (2026-06-28) | 11,459 | 6.5 MB | 10.1 MB (~4.2 M) | 136 MB | 2.2 MB |
| Amsterdam (2026-06-15) | 10,465 | 5.8 MB | 9.0 MB (~3.8 M) | 66.6 MB | 2.1 MB |
| New York City (2026-06-14) | 30,555 | 15.7 MB | 25.9 MB (~11 M) | 119 MB | 5.5 MB |
| London (2026-06-19) | 92,799 | 50.4 MB | 82.4 MB (~34 M) | 277 MB | 16.0 MB |

Budapest extras: summary `reviews.csv` 26 MB, `neighbourhoods.csv` 374 B (23 districts), `neighbourhoods.geojson` 154 KB. Reviews row counts were not downloaded; Budapest reviews are in the low millions by compressed size. Budapest profile: 91% entire homes, 72.8% multi-listing hosts, prices in **HUF** (`Ft50,809`/night).

**Snapshots.** The site's Gatsby data (`page-data/sq/d/3176684073.json`) lists 561 datasets / 121 regions. Free quarterly snapshots:
- Budapest: 2025-09-25, 2025-12-28, 2026-03-29, 2026-06-28
- Amsterdam: 2025-09-11, 2025-12-12, 2026-03-19, 2026-06-15
- London: 2025-09-14, 2025-12-13, 2026-03-21, 2026-06-19
- NYC: 2025-12-04, 2026-03-16, 2026-06-14
HEAD-verified: the three archived Budapest `listings.csv.gz` return 200 (6.9 / 5.0 / 4.4 MB); a 2025-06 URL returns 403 (rolled off). Four snapshots support an SCD Type 2 demo and a `snapshot_date` dimension.

## 2. Paid Udemy course and redistribution

- **CC BY 4.0 allows commercial use and adaptation** ("for any purpose, even commercially"), requiring appropriate credit, a license link, and a note that changes were made, without implying endorsement. Teaching on Udemy and distributing derived tables/PDFs is licensed.
- **Tension:** Inside Airbnb's guidelines say "do not republish" and ask instructors to download once and consider donating. Respectful approach: students download the specific snapshot URLs themselves; redistribute only small derived artifacts (Budapest Parquet subset, generated PDFs); include a donation link.
- No official citation string. Suggested text:
  > "Data: Inside Airbnb (insideairbnb.com), Budapest snapshot 2026-06-28, licensed under CC BY 4.0 (creativecommons.org/licenses/by/4.0). Modified: filtered, cleansed and aggregated for teaching."
- Databricks' Marketplace listing redistributes the same data with a disclaimer ("not associated with or endorsed by Airbnb…"), a useful precedent to copy.
- Free Edition "may not be used for commercial purposes"; students learning on their own accounts is normal use, the instructor recording a paid course on one is a grey area (open question).

## 3. Marketplace / sample-dataset substitutes

- **Marketplace "Airbnb Sample Data" by Databricks** (listing id `5f183624-…`): type **Files** (shared volume), Free, Instantly available, category Education. Sourced from insideairbnb.com, "in an unmodified form, as well as in a form subjected to additional cleansing". Its license link says CC0 (inconsistent; treat CC BY as governing). Cities/dates not disclosed on the listing page.
- **Free Edition as Marketplace consumer:** docs require a UC workspace on "Premium plan or above" plus `USE MARKETPLACE ASSETS` (default-granted). Free Edition limits only say it "cannot become Databricks Marketplace providers". Docs also mention "Free sample data from Databricks Marketplace" on the Add data page. Unverified on Free Edition.
- **`samples` catalog** (default in UC): `samples.nyctaxi.trips`, `samples.tpch`, `samples.tpcds_sf1`, volume `/Volumes/samples/databricks/datasets/`. No Airbnb data; fallback only. Legacy `/databricks-datasets/` is DBFS, which is limited on serverless.

## 4. Free Edition loading paths

- **Compute:** serverless only; one SQL warehouse capped at 2X-Small; "limited" notebook compute; max 5 concurrent job tasks; one active pipeline per type; one workspace/metastore; no account console; quota overrun shuts compute for the rest of the day/month.
- **Egress:** "outbound internet access is restricted to a limited set of trusted domains" (list unpublished). A July 2026 thread on similarly restricted serverless found `pypi.org`, `github.com`, `docker.com`, `databricks.com` reachable and other hosts failing DNS; Free Edition users report `requests.get("https://www.google.com")` failing. No account console means network policies cannot be changed. **Assume `data.insideairbnb.com` is NOT reachable** from a Free Edition notebook; `%pip install` and GitHub Git folders should work. Not empirically tested, verify with one `requests.head()` cell.
- **Catalog Explorer volume upload:** 5 GB per file (larger via SDK/CLI). All Budapest files fit easily.
- **Create or modify a table using file upload:** up to 10 files, total under 2 GB, CSV/TSV/JSON/Avro/Parquet/text, lands as Delta. Gzip acceptance not documented.
- **CLI:** `databricks fs cp <local> dbfs:/Volumes/<cat>/<schema>/<vol>/ [-r] [--overwrite]` is documented for volumes; good scripted step for the bundles module. Python SDK `w.files.upload` is the equivalent.
- **Serverless caveats:** volumes have no random writes (unzip in `/tmp`, then `dbutils.fs.mv`); Spark reads gzipped CSV natively via `read_files(..., format => 'csv', header => true, multiLine => true)` — `description`/`comments` contain embedded newlines and quotes, so `multiLine` and escape options matter.

## 5. PDFs for "Genie over files in a volume"

**Genie support (docs Sep 2026):** "Analyze files in volumes with a Genie Agent" is **Beta**, enabled by an admin in Previews. Up to 10 volumes per agent; the whole volume is attached; requires **Agent mode**; page-level citations. Without content search: **PDF, JPG/JPEG, PNG, TIFF, DOC/DOCX, PPT/PPTX**, max **10 MB/file**, **500 files/volume** (TXT/MD exempt), **5 files retrieved per question**. With content search (region-dependent): 10,000 files of 50 MB. Users need Workspace access + Databricks SQL access entitlements and `READ VOLUME`. Separate feature: PDF upload into a conversation (Beta; 20 MB, 100 pages, 15,000 chars, needs Partner-Powered AI). Keep the demo on the volume path.

**Generation ideas** (Python + reportlab/fpdf2 in a notebook, written into a volume):
1. **Per-district market reports** (23 Budapest districts): median price, occupancy proxy (`365 - availability_365`), review scores, room-type mix, top hosts, QoQ change across 4 snapshots, one chart. ~200 KB each; ideal for "which district's report says X" and PDF-vs-table blending.
2. **Host house-rules / guest guides** for the top ~30 multi-listing hosts, synthesized from `amenities`, `minimum_nights`, `accommodates`, `neighborhood_overview`: check-in, quiet hours, pet/smoking policy. Answers policy questions SQL cannot.
3. **City regulation summary** (one PDF, clearly labelled teaching summary): Budapest STR rules (<30 nights), the Terézváros (district VI) referendum banning STRs from 2026, registration/permit changes; cross-reference the `license` column.
4. **Quarterly change memos** (3 PDFs): narrative counterpart to the SCD2 tables.
5. **Data dictionary PDF** exported from the Google Sheet so Genie can explain columns.
Keep files under 10 MB, fewer than 500, descriptive names (`budapest_district_07_2026Q2_market_report.pdf`), no near-duplicates, precise volume description.

## Recommendation

**Primary: Budapest, all four free snapshots, detailed `listings.csv.gz` per snapshot + summary `reviews.csv` + `neighbourhoods.csv/geojson`; detailed `calendar.csv.gz` for the latest snapshot; detailed `reviews.csv.gz` optional.**
- Fits Free Edition: ~23 MB gzipped listings across four quarters, 10 MB calendar (4.2 M rows: a real fact table that a 2X-Small warehouse still handles), 26 MB summary reviews. The 136 MB detailed reviews file (free text) is the only heavy item; load once only if you want `ai_query`/sentiment demos.
- Four snapshots give the SCD2/time story; 23 districts give a tidy geography for metric views and per-district PDFs; HUF prices and heavy host concentration make for good questions.

**Secondary (optional comparison city): Amsterdam.** Same size class (10.5k listings, 67 MB reviews), EUR prices, and a `license` field with ~91% licensed listings, enabling a compliance metric and multi-city metric views with a `city` dimension. Both cities together stay under ~300 MB raw.

**Do not require London or NYC**: 92.8k listings, ~34 M-row calendar, 277 MB reviews would be slow and quota-hungry on a 2X-Small warehouse and limited serverless notebooks. Mention London as a "scale it up at work" exercise.

**Loading path to teach:** students download the few files from exact snapshot URLs on their laptop (one-time, matching Inside Airbnb's guidelines), upload to a UC volume via Catalog Explorer (or `databricks fs cp` in the bundles module), then `read_files`/Auto Loader into bronze Delta. Do not depend on in-notebook `curl` to `data.insideairbnb.com`. Generate PDFs into a second volume and attach only that volume to the Genie Agent.

## Facts verified (URLs)

- CC BY 4.0 statement, file lists, "quarterly data for the last year… free", regional archives: https://insideairbnb.com/get-the-data/
- Community guidelines, free vs archived policy: https://insideairbnb.com/data-policies/
- Data dictionary v4.7: https://docs.google.com/spreadsheets/d/1iWCNJcSutYqpULSQHlNyGInUvHg2BoUGoNRIGa6Szc4
- All snapshots per city: https://insideairbnb.com/page-data/sq/d/3176684073.json
- Listing counts/currency: https://insideairbnb.com/budapest/ , /amsterdam/ , /london/ , /new-york-city/
- Sizes: HTTP HEAD on `data.insideairbnb.com/hungary/k%C3%B6z%C3%A9p-magyarorsz%C3%A1g/budapest/2026-06-28/...`, `/the-netherlands/north-holland/amsterdam/2026-06-15/...`, `/united-kingdom/england/london/2026-06-19/...`, `/united-states/ny/new-york-city/2026-06-14/...`; archived Budapest 2025-09-25/12-28, 2026-03-29 return 200; 2025-06-23 returns 403.
- CC BY 4.0 deed: https://creativecommons.org/licenses/by/4.0/deed.en
- Marketplace listing: https://marketplace.databricks.com/details/5f183624-2cc9-450d-98cd-a524bb036b57/Databricks_Airbnb-Sample-Data ; consumer requirements: https://docs.databricks.com/aws/en/marketplace/get-started-consumer
- `samples` catalog: https://docs.databricks.com/aws/en/discover/databricks-datasets
- Free Edition limitations: https://docs.databricks.com/aws/en/getting-started/free-edition-limitations ; serverless limitations: https://docs.databricks.com/aws/en/compute/serverless/limitations
- Download-from-internet patterns: https://docs.databricks.com/aws/en/volumes/download-internet-files
- Volume UI 5 GB limit: https://docs.databricks.com/aws/en/volumes/volume-files ; https://docs.databricks.com/aws/en/files/files-recommendations
- Table upload UI (10 files / 2 GB): https://docs.databricks.com/aws/en/ingestion/create-or-modify-table
- CLI `fs cp` to volumes: https://docs.databricks.com/aws/en/dev-tools/cli/reference/fs-commands
- Egress reports: https://community.databricks.com/t5/data-engineering/serverless-egress-public-internet-access-issues/td-p/163165 ; https://community.databricks.com/t5/data-engineering/free-edition-outbound-internet-suddenly-blocked-error/td-p/121832
- Genie over volumes: https://docs.databricks.com/aws/en/genie-agents/volumes ; Genie file upload: https://docs.databricks.com/aws/en/genie-agents/file-upload

## Open questions

1. Is `data.insideairbnb.com` reachable from a Free Edition notebook? (Strongly implied no; untested.)
2. Can Free Edition "Get instant access" to the Marketplace Airbnb volume, and which cities/dates does it hold?
3. Is the "Analyze Files in Volumes with Genie Agents" preview (and content search) available in Free Edition's region?
4. Does the table-upload UI accept `.csv.gz`? If not, gunzip locally (Budapest listings ~90 MB uncompressed).
5. Exact Budapest `reviews.csv.gz` row count (confirm after first load).
6. Recording a paid course on a Free Edition account vs the "no commercial purposes" clause; consider a trial/paid workspace for recording.
7. Whether to donate/acknowledge Inside Airbnb and email data@insideairbnb.com as a courtesy.
