-- Gold: one row per listing with its activity over the last 365 days and its
-- forward availability. This is the only table where the three source files meet.
--
-- Estimated nights follow Inside Airbnb's published occupancy model: a 50 percent
-- review rate (x2), an average stay of 5.5 nights or the listing minimum if
-- longer, capped at 255 nights (70 percent occupancy). The review count uses
-- Inside Airbnb's window, which runs from the listing's own scrape date back 365
-- days inclusive; with it the estimate equals dim_listing.published_occupancy_l365d
-- for every listing, which is the acceptance test. A window anchored on the
-- latest scrape date instead matches only 95 percent, because most listings were
-- scraped a week earlier.
--
-- snapshot_date is the listing's scrape date, so loading a newer drop moves each
-- window with its data. Calendar windows start at snapshot_date.
CREATE OR REFRESH MATERIALIZED VIEW fact_listing_activity (
  listing_id BIGINT NOT NULL COMMENT 'Listing. Primary key and foreign key to dim_listing.',
  host_id BIGINT COMMENT 'Host of the listing. Foreign key to dim_host.',
  snapshot_date DATE COMMENT 'Scrape date of the listing. The activity windows end on this date and the calendar windows start on it.',
  reviews_l365d INT COMMENT 'Reviews received in the 365 days up to and including snapshot_date.',
  reviews_l30d INT COMMENT 'Reviews received in the 30 days up to and including snapshot_date.',
  estimated_nights_l365d INT COMMENT 'Estimated occupied nights in the last 365 days: LEAST(255, reviews_l365d * 2 * GREATEST(minimum_nights, 5.5)).',
  estimated_revenue_l365d DECIMAL(12,2) COMMENT 'Estimated revenue in US dollars in the last 365 days: estimated_nights_l365d times nightly_price. NULL when the listing has no price.',
  open_nights_next_90 INT COMMENT 'Bookable nights from snapshot_date over the next 90 days.',
  open_nights_next_365 INT COMMENT 'Bookable nights from snapshot_date over the next 365 days.',
  blocked_nights_next_365 INT COMMENT 'Nights from snapshot_date over the next 365 days that are not bookable (booked or closed by the host).',
  is_active BOOLEAN COMMENT 'True if the listing had a review in the last 365 days or has any availability.',
  CONSTRAINT fact_listing_activity_pk PRIMARY KEY (listing_id) RELY,
  CONSTRAINT fact_listing_activity_listing_fk FOREIGN KEY (listing_id) REFERENCES dim_listing(listing_id) RELY,
  CONSTRAINT fact_listing_activity_host_fk FOREIGN KEY (host_id) REFERENCES dim_host(host_id) RELY
)
COMMENT 'One row per listing: estimated occupied nights and revenue for the last 365 days, reviews in the last 30 and 365 days, and open and blocked nights ahead. Combines reviews, calendar and listing attributes. Use for revenue, occupancy and activity questions.'
TBLPROPERTIES ('quality' = 'gold')
AS
WITH reviews AS (
  SELECT
    l.listing_id,
    COUNT(*) FILTER (WHERE r.review_date >= date_sub(l.last_scraped, 365)) AS reviews_l365d,
    COUNT(*) FILTER (WHERE r.review_date >= date_sub(l.last_scraped, 30))  AS reviews_l30d
  FROM silver_listings l
  JOIN silver_reviews r ON r.listing_id = l.listing_id AND r.review_date <= l.last_scraped
  GROUP BY l.listing_id
),
calendar AS (
  SELECT
    l.listing_id,
    COUNT(*) FILTER (WHERE c.is_available AND c.calendar_date < date_add(l.last_scraped, 90)) AS open_nights_next_90,
    COUNT(*) FILTER (WHERE c.is_available)     AS open_nights_next_365,
    COUNT(*) FILTER (WHERE NOT c.is_available) AS blocked_nights_next_365
  FROM silver_listings l
  JOIN silver_calendar c ON c.listing_id = l.listing_id
   AND c.calendar_date >= l.last_scraped
   AND c.calendar_date <  date_add(l.last_scraped, 365)
  GROUP BY l.listing_id
),
base AS (
  SELECT
    l.listing_id,
    l.host_id,
    l.last_scraped AS snapshot_date,
    COALESCE(r.reviews_l365d, 0) AS reviews_l365d,
    COALESCE(r.reviews_l30d, 0)  AS reviews_l30d,
    l.minimum_nights,
    l.nightly_price,
    l.has_availability,
    COALESCE(c.open_nights_next_90, 0)     AS open_nights_next_90,
    COALESCE(c.open_nights_next_365, 0)    AS open_nights_next_365,
    COALESCE(c.blocked_nights_next_365, 0) AS blocked_nights_next_365
  FROM silver_listings l
  LEFT JOIN reviews  r ON r.listing_id = l.listing_id
  LEFT JOIN calendar c ON c.listing_id = l.listing_id
),
estimated AS (
  SELECT *,
    CAST(LEAST(255, reviews_l365d * 2 * GREATEST(minimum_nights, 5.5)) AS INT) AS estimated_nights_l365d
  FROM base
)
SELECT
  listing_id,
  host_id,
  snapshot_date,
  CAST(reviews_l365d AS INT) AS reviews_l365d,
  CAST(reviews_l30d AS INT)  AS reviews_l30d,
  estimated_nights_l365d,
  CAST(estimated_nights_l365d * nightly_price AS DECIMAL(12,2)) AS estimated_revenue_l365d,
  CAST(open_nights_next_90 AS INT)     AS open_nights_next_90,
  CAST(open_nights_next_365 AS INT)    AS open_nights_next_365,
  CAST(blocked_nights_next_365 AS INT) AS blocked_nights_next_365,
  (reviews_l365d > 0 OR COALESCE(has_availability, false)) AS is_active
FROM estimated;
