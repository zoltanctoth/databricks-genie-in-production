# Databricks notebook source
# MAGIC %run "./Import Config"

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REFRESH STREAMING TABLE bronze_listings (
# MAGIC   CONSTRAINT listing_id_present EXPECT (id IS NOT NULL),
# MAGIC   CONSTRAINT no_rescued_data    EXPECT (_rescued_data IS NULL)
# MAGIC )
# MAGIC COMMENT 'Raw Inside Airbnb listings.csv (San Francisco). All columns as strings plus ingestion metadata. Not a Genie source; feeds dim_listing and dim_host.'
# MAGIC TBLPROPERTIES ('quality' = 'bronze')
# MAGIC AS SELECT
# MAGIC   *,
# MAGIC   _metadata.file_path              AS _source_file,
# MAGIC   _metadata.file_modification_time AS _source_modified_at,
# MAGIC   current_timestamp()              AS _ingested_at
# MAGIC FROM STREAM read_files(
# MAGIC   concat(:source_path, '/listings*.csv'),
# MAGIC   format              => 'csv',
# MAGIC   header              => true,
# MAGIC   multiLine           => true,
# MAGIC   escape              => '"',
# MAGIC   inferColumnTypes    => false,
# MAGIC   mode                => 'PERMISSIVE',
# MAGIC   rescuedDataColumn   => '_rescued_data',
# MAGIC   schemaEvolutionMode => 'addNewColumns'
# MAGIC );
# MAGIC