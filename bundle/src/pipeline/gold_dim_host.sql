-- Gold: one row per host, attributes taken from the host's latest-scraped listing.
--
-- Hosts carry no file of their own in the Inside Airbnb export, so they are
-- derived from silver_listings. sf_listings_count counts the host's listings in
-- this snapshot; platform_listings_count is the host's Airbnb-wide figure.
CREATE OR REFRESH MATERIALIZED VIEW dim_host (
  host_id BIGINT NOT NULL COMMENT 'Airbnb host identifier. Primary key.',
  host_name STRING COMMENT 'Host first name as shown on Airbnb.',
  is_superhost BOOLEAN COMMENT 'True if the host holds Superhost status.',
  identity_verified BOOLEAN COMMENT 'True if Airbnb has verified the host identity.',
  has_profile_pic BOOLEAN COMMENT 'True if the host has a profile picture.',
  host_location STRING COMMENT 'Free-text location the host entered, for example "San Francisco, California, United States".',
  host_about STRING COMMENT 'Free-text host biography.',
  host_tenure_years DECIMAL(5,2) COMMENT 'Years the host has been on Airbnb, in fractional years, as of the snapshot.',
  platform_listings_count INT COMMENT 'Number of listings the host has on Airbnb worldwide, as reported by Airbnb.',
  sf_listings_count INT COMMENT 'Number of this host''s listings in the San Francisco snapshot. Basis for host_size_band.',
  host_size_band STRING COMMENT 'Portfolio size in San Francisco: 1, 2-4, 5-19 or 20+ listings.',
  CONSTRAINT dim_host_pk PRIMARY KEY (host_id) RELY
)
COMMENT 'One row per Airbnb host with a listing in San Francisco (Inside Airbnb snapshot 2026-06-14). Use for host lookups: portfolio size, Superhost status, tenure. Join to dim_listing on host_id.'
TBLPROPERTIES ('quality' = 'gold')
AS
WITH latest AS (
  SELECT *
  FROM silver_listings
  WHERE host_id IS NOT NULL
  QUALIFY ROW_NUMBER() OVER (PARTITION BY host_id ORDER BY last_scraped DESC, listing_id) = 1
),
portfolio AS (
  SELECT host_id, COUNT(*) AS sf_listings_count
  FROM silver_listings
  WHERE host_id IS NOT NULL
  GROUP BY host_id
)
SELECT
  l.host_id,
  l.host_name,
  l.host_is_superhost       AS is_superhost,
  l.host_identity_verified  AS identity_verified,
  l.host_has_profile_pic    AS has_profile_pic,
  l.host_location,
  l.host_about,
  l.host_tenure_years,
  l.host_listings_count     AS platform_listings_count,
  CAST(p.sf_listings_count AS INT) AS sf_listings_count,
  CASE
    WHEN p.sf_listings_count = 1  THEN '1'
    WHEN p.sf_listings_count < 5  THEN '2-4'
    WHEN p.sf_listings_count < 20 THEN '5-19'
    ELSE '20+'
  END AS host_size_band
FROM latest l
JOIN portfolio p USING (host_id);
