-- Silver: one typed row per listing, latest scrape wins.
--
-- Silver does three things and nothing else: cast the bronze strings, keep one
-- row per listing, and derive the handful of business fields that both Genie
-- Agents filter on (license_status, stay_type, is_hotel). Column comments and
-- primary/foreign keys belong to gold, where Genie reads them.
--
-- Columns dropped on purpose: the 13 that are entirely null in the 2026 export
-- (host_since, host_response_*, host_acceptance_rate, host_thumbnail_url,
-- host_neighbourhood, host_total_listings_count, host_verifications,
-- neighbourhood, neighbourhood_group_cleansed, calendar_updated, instant_bookable,
-- neighborhood_overview) and the URL and raw-quote columns no agent needs.
--
-- Numeric strings arrive as "2.0", so integers are cast through DOUBLE.
-- A materialized view recomputes in full on every update; at 7,332 rows that is
-- the simplest correct choice.
CREATE OR REFRESH MATERIALIZED VIEW silver_listings (
  CONSTRAINT listing_id_present   EXPECT (listing_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT host_id_present      EXPECT (host_id IS NOT NULL),
  CONSTRAINT neighbourhood_present EXPECT (neighbourhood IS NOT NULL),
  CONSTRAINT price_positive       EXPECT (nightly_price IS NULL OR nightly_price > 0),
  CONSTRAINT minimum_nights_known EXPECT (minimum_nights IS NOT NULL)
)
COMMENT 'Typed Inside Airbnb listings, one row per listing (latest scrape). Prices parsed from "$1,234.00" text; booleans from t/f; amenities as an array. Adds license_status, stay_type and is_hotel. Not a Genie source; feeds dim_listing, dim_host and fact_listing_activity.'
TBLPROPERTIES ('quality' = 'silver')
AS
WITH latest AS (
  SELECT *
  FROM bronze_listings
  QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY last_scraped DESC, _ingested_at DESC) = 1
),
typed AS (
  SELECT
    TRY_CAST(id AS BIGINT)                                                AS listing_id,
    listing_url,
    name,
    description,
    TRY_CAST(host_id AS BIGINT)                                           AS host_id,
    host_name,
    CAST(TRY_CAST(hosts_time_as_host_years AS DOUBLE)
         + TRY_CAST(hosts_time_as_host_months AS DOUBLE) / 12 AS DECIMAL(5,2)) AS host_tenure_years,
    host_location,
    host_about,
    CASE host_is_superhost      WHEN 't' THEN true WHEN 'f' THEN false END AS host_is_superhost,
    CASE host_has_profile_pic   WHEN 't' THEN true WHEN 'f' THEN false END AS host_has_profile_pic,
    CASE host_identity_verified WHEN 't' THEN true WHEN 'f' THEN false END AS host_identity_verified,
    CAST(TRY_CAST(host_listings_count AS DOUBLE) AS INT)                  AS host_listings_count,
    neighbourhood_cleansed                                                AS neighbourhood,
    TRY_CAST(latitude  AS DOUBLE)                                         AS latitude,
    TRY_CAST(longitude AS DOUBLE)                                         AS longitude,
    property_type,
    room_type,
    CAST(TRY_CAST(accommodates AS DOUBLE) AS INT)                         AS accommodates,
    TRY_CAST(bathrooms AS DECIMAL(4,1))                                   AS bathrooms,
    bathrooms_text,
    CAST(TRY_CAST(bedrooms AS DOUBLE) AS INT)                             AS bedrooms,
    CAST(TRY_CAST(beds AS DOUBLE) AS INT)                                 AS beds,
    from_json(amenities, 'ARRAY<STRING>')                                 AS amenities,
    TRY_CAST(regexp_replace(price, '[$,]', '') AS DECIMAL(10,2))          AS nightly_price,
    TRY_CAST(price_quote_checkin_date  AS DATE)                           AS price_quote_checkin_date,
    TRY_CAST(price_quote_checkout_date AS DATE)                           AS price_quote_checkout_date,
    CAST(TRY_CAST(minimum_nights AS DOUBLE) AS INT)                       AS minimum_nights,
    CAST(TRY_CAST(maximum_nights AS DOUBLE) AS INT)                       AS maximum_nights,
    CASE has_availability WHEN 't' THEN true WHEN 'f' THEN false END      AS has_availability,
    CAST(TRY_CAST(availability_30  AS DOUBLE) AS INT)                     AS availability_30,
    CAST(TRY_CAST(availability_60  AS DOUBLE) AS INT)                     AS availability_60,
    CAST(TRY_CAST(availability_90  AS DOUBLE) AS INT)                     AS availability_90,
    CAST(TRY_CAST(availability_365 AS DOUBLE) AS INT)                     AS availability_365,
    CAST(TRY_CAST(number_of_reviews      AS DOUBLE) AS INT)               AS number_of_reviews,
    CAST(TRY_CAST(number_of_reviews_ltm  AS DOUBLE) AS INT)               AS number_of_reviews_ltm,
    CAST(TRY_CAST(number_of_reviews_l30d AS DOUBLE) AS INT)               AS number_of_reviews_l30d,
    TRY_CAST(first_review AS DATE)                                        AS first_review,
    TRY_CAST(last_review  AS DATE)                                        AS last_review,
    TRY_CAST(review_scores_rating        AS DECIMAL(3,2))                 AS review_score_rating,
    TRY_CAST(review_scores_accuracy      AS DECIMAL(3,2))                 AS review_score_accuracy,
    TRY_CAST(review_scores_cleanliness   AS DECIMAL(3,2))                 AS review_score_cleanliness,
    TRY_CAST(review_scores_checkin       AS DECIMAL(3,2))                 AS review_score_checkin,
    TRY_CAST(review_scores_communication AS DECIMAL(3,2))                 AS review_score_communication,
    TRY_CAST(review_scores_location      AS DECIMAL(3,2))                 AS review_score_location,
    TRY_CAST(review_scores_value         AS DECIMAL(3,2))                 AS review_score_value,
    TRY_CAST(reviews_per_month AS DECIMAL(6,2))                           AS reviews_per_month,
    NULLIF(TRIM(license), '')                                             AS license,
    CAST(TRY_CAST(calculated_host_listings_count AS DOUBLE) AS INT)       AS sf_listings_count,
    CAST(TRY_CAST(estimated_occupancy_l365d AS DOUBLE) AS INT)            AS published_occupancy_l365d,
    TRY_CAST(estimated_revenue_l365d AS DECIMAL(12,2))                    AS published_revenue_l365d,
    TRY_CAST(last_scraped AS DATE)                                        AS last_scraped,
    source                                                                AS scrape_source
  FROM latest
)
SELECT
  typed.*,
  -- Same rules as tools/generate_documents.py classify_license(), so the
  -- regulation PDF and the compliance metrics agree.
  CASE
    WHEN license IS NULL                                  THEN 'missing'
    WHEN license RLIKE '^(?i)STR-[0-9]+$'                 THEN 'certificate'
    WHEN license RLIKE '^(?i)[0-9]{4}-[0-9]+STR$'         THEN 'pending'
    WHEN LOWER(license) LIKE 'exempt%'
      OR LOWER(license) LIKE '%not needed%'               THEN 'exempt'
    ELSE 'other'
  END                                                                     AS license_status,
  -- Stays of 30 nights or more fall outside the short-term rental ordinance.
  CASE WHEN minimum_nights < 30 THEN 'short_term' ELSE 'long_term' END    AS stay_type,
  (room_type = 'Hotel room' OR LOWER(property_type) LIKE '%hotel%')       AS is_hotel
FROM typed;
