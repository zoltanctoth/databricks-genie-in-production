-- Metric view booking_reference over gold.fact_calendar, dim_listing and dim_host.
--
-- Run by the deploy_metric_views job as a sql_task on a SQL warehouse, not by the
-- pipeline: SDP accepts only CREATE MATERIALIZED VIEW / STREAMING TABLE statements,
-- and bundles have no metric view resource (decision D5).
--
-- {{catalog}} and {{schema}} are job parameters. USE sets the target, so the view
-- name and the YAML source and join tables are written without catalog and schema.

USE CATALOG IDENTIFIER({{catalog}});
USE SCHEMA IDENTIFIER({{schema}});

CREATE OR REPLACE VIEW booking_reference
WITH METRICS
LANGUAGE YAML
AS $$
version: 1.1
source: fact_calendar
filter: listing_id IS NOT NULL AND is_available IS NOT NULL
joins:
  - name: dim_listings
    source: dim_listing
    using:
      - listing_id
    joins:
      - name: dim_host
        source: dim_host
        using:
          - host_id
dimensions:
  - name: calendar_date
    expr: source.calendar_date
    comment: Represents the specific date for each record, allowing for time-based analysis and filtering. Use this dimension to group or filter data by individual days in your queries.
    display_name: Calendar Date
    synonyms:
      - date
      - day
      - transaction date
      - event date
  - name: listing_id
    expr: source.listing_id
    comment: Unique identifier for each listing in the dataset. Use this dimension to filter or group data related to specific listings.
    display_name: Listing ID
    synonyms:
      - listing number
      - property ID
      - item ID
      - listing reference
  - name: minimum_nights
    expr: source.minimum_nights
    comment: Represents the minimum number of nights required for a booking. Use this dimension to filter or group data based on the minimum stay policy for properties.
    display_name: Minimum Nights
    synonyms:
      - minimum stay
      - required nights
      - booking nights
      - stay duration
  - name: is_available
    expr: source.is_available
    comment: "True if the night can be booked. False means blocked: booked by a guest or closed by the host."
    display_name: Is Available
    synonyms:
      - availability
      - bookable
      - reservation status
      - room status
  - name: host_type
    expr: IF(dim_listings.dim_host.is_superhost, 'Superhost', 'Not Superhost')
    comment: Indicates whether a host is classified as a Superhost based on their performance metrics. Use this dimension to filter or group listings by host type for analysis of host quality and customer experience.
    display_name: Is Superhost
    synonyms:
      - superhost status
      - host classification
      - host quality
      - superhost designation
  - name: neighborhood
    expr: dim_listings.neighbourhood
    comment: Identifies the neighborhood where each listing is located. Use this dimension to analyze listing performance, trends, or metrics by geographic area within the city.
    display_name: Neighborhood
    synonyms:
      - area
      - district
      - locality
      - neighborhood name

measures:
  - name: availability_ratio
    expr: COUNT_IF(is_available) / COUNT(*)
    comment: Proportion of records where the item is available, calculated as the percentage of rows with is_available = true. Use this measure to track overall availability rates over time or across groups.
    display_name: Availability Ratio
    format:
      type: percentage
      decimal_places:
        type: max
        places: 2
      hide_group_separator: false
    synonyms:
      - availability rate
      - percent available
      - availability percentage
      - item availability
$$;
