# Databricks notebook source
# Databricks notebook source
# Input data and working folders locations
CLOUD_SOURCE = 's3a://dbx-data-public/airbnb-sf/'
SOURCE_LOCATION = "/Volumes/genie_reference/source/files/airbnb-sf/"
TARGET_LOCATION = workdir = "/Volumes/genie_reference/airbnb/files/"

from types import SimpleNamespace
CONFIG = SimpleNamespace(
    paths = SimpleNamespace(
        datasets_root=SOURCE_LOCATION,
        workdir=workdir,
        listings=SOURCE_LOCATION + '/listings/',
        calendar=SOURCE_LOCATION + '/calendar/',
        reviews=SOURCE_LOCATION + '/reviews/'
    )
)

dbutils.widgets.text("paths_listings", CONFIG.paths.listings)
dbutils.widgets.text("paths_calendar", CONFIG.paths.calendar)
dbutils.widgets.text("paths_reviews", CONFIG.paths.reviews)
