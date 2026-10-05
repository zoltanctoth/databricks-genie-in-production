# Databricks notebook source
# MAGIC %run "../import_config"

# COMMAND ----------

print(f"Copying data from {CLOUD_SOURCE}...")
dbutils.fs.cp(CLOUD_SOURCE + '/listings.csv', SOURCE_LOCATION + '/listings/', recurse=True)
dbutils.fs.cp(CLOUD_SOURCE + '/calendar.csv', SOURCE_LOCATION + '/calendar/', recurse=True)
dbutils.fs.cp(CLOUD_SOURCE + '/reviews.csv', SOURCE_LOCATION + '/reviews/', recurse=True)
print(f"Done! files are copied into {SOURCE_LOCATION}")
display(dbutils.fs.ls(SOURCE_LOCATION))
