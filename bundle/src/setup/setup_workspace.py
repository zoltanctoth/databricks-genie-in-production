# Databricks notebook source
# Copies the Inside Airbnb San Francisco snapshot (three CSVs) and the 32 Genie
# PDFs from the public S3 mirror into this target's volumes. Parameters come
# from the job's base_parameters in resources/setup_workspace.job.yml.

dbutils.widgets.text("cloud_source", "s3a://dbx-data-public/airbnb-sf")
dbutils.widgets.text("files_path", "")
dbutils.widgets.text("documents_path", "")

cloud_source = dbutils.widgets.get("cloud_source").rstrip("/")
files_path = dbutils.widgets.get("files_path").rstrip("/")
documents_path = dbutils.widgets.get("documents_path").rstrip("/")
assert files_path and documents_path, "files_path and documents_path are required"

# COMMAND ----------

# The bronze tables read ${source_path}/<name>*.csv, so the CSVs land flat
# under airbnb-sf/.
for name in ["listings.csv", "calendar.csv", "reviews.csv", "LICENSE.md"]:
    dbutils.fs.cp(f"{cloud_source}/{name}", f"{files_path}/{name}")
    print(f"Copied {name} to {files_path}")

# COMMAND ----------

dbutils.fs.cp(f"{cloud_source}/documents/", f"{documents_path}/", recurse=True)
pdfs = [f for f in dbutils.fs.ls(documents_path) if f.name.endswith(".pdf")]
print(f"{len(pdfs)} PDFs in {documents_path}")
assert len(pdfs) == 32, f"expected 32 PDFs, found {len(pdfs)}"

# COMMAND ----------

display(dbutils.fs.ls(files_path))
