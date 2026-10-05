-- Gold: one row per listing, the descriptive side of the star schema.
--
-- Host attributes live in dim_host. The published_* columns are Inside Airbnb's
-- own occupancy and revenue estimates, kept to validate fact_listing_activity.
CREATE OR REFRESH MATERIALIZED VIEW dim_listing (
  listing_id BIGINT NOT NULL COMMENT 'Airbnb listing identifier. Primary key.',
  host_id BIGINT COMMENT 'Host of the listing. Foreign key to dim_host.',
  name STRING COMMENT 'Listing title as shown on Airbnb.',
  description STRING COMMENT 'Free-text listing description.',
  neighbourhood STRING COMMENT 'San Francisco neighbourhood (36 values), for example Mission or Noe Valley.',
  latitude DOUBLE COMMENT 'Approximate latitude of the listing.',
  longitude DOUBLE COMMENT 'Approximate longitude of the listing.',
  property_type STRING COMMENT 'Airbnb property type, for example "Entire rental unit" or "Private room in home".',
  room_type STRING COMMENT 'Airbnb room type: Entire home/apt, Private room, Shared room or Hotel room.',
  is_hotel BOOLEAN COMMENT 'True for hotel rooms and hotel-type properties. Hotels are exempt from short-term rental registration.',
  accommodates INT COMMENT 'Maximum number of guests.',
  bedrooms INT COMMENT 'Number of bedrooms.',
  beds INT COMMENT 'Number of beds.',
  bathrooms DECIMAL(4,1) COMMENT 'Number of bathrooms.',
  amenities ARRAY<STRING> COMMENT 'Amenities offered, one array element per amenity.',
  nightly_price DECIMAL(10,2) COMMENT 'Nightly price in US dollars at the price quote date. NULL for listings without a quoted price.',
  price_quote_checkin_date DATE COMMENT 'Check-in date of the price quote behind nightly_price.',
  price_quote_checkout_date DATE COMMENT 'Check-out date of the price quote behind nightly_price.',
  minimum_nights INT COMMENT 'Minimum nights per booking.',
  maximum_nights INT COMMENT 'Maximum nights per booking.',
  stay_type STRING COMMENT 'short_term when minimum_nights is under 30 (covered by the San Francisco short-term rental ordinance), otherwise long_term.',
  has_availability BOOLEAN COMMENT 'True if the listing has any bookable night in the next 365 days.',
  availability_30 INT COMMENT 'Bookable nights in the next 30 days, as scraped.',
  availability_60 INT COMMENT 'Bookable nights in the next 60 days, as scraped.',
  availability_90 INT COMMENT 'Bookable nights in the next 90 days, as scraped.',
  availability_365 INT COMMENT 'Bookable nights in the next 365 days, as scraped.',
  license STRING COMMENT 'Registration or license text the host entered. NULL when none.',
  license_status STRING COMMENT 'Classification of license: certificate (STR-nnnn), pending (nnnn-nnnSTR), exempt, other or missing.',
  number_of_reviews INT COMMENT 'Total reviews the listing has received.',
  first_review DATE COMMENT 'Date of the first review.',
  last_review DATE COMMENT 'Date of the most recent review.',
  review_score_rating DECIMAL(3,2) COMMENT 'Overall review score, 0 to 5.',
  review_score_accuracy DECIMAL(3,2) COMMENT 'Review score for accuracy, 0 to 5.',
  review_score_cleanliness DECIMAL(3,2) COMMENT 'Review score for cleanliness, 0 to 5.',
  review_score_checkin DECIMAL(3,2) COMMENT 'Review score for check-in, 0 to 5.',
  review_score_communication DECIMAL(3,2) COMMENT 'Review score for communication, 0 to 5.',
  review_score_location DECIMAL(3,2) COMMENT 'Review score for location, 0 to 5.',
  review_score_value DECIMAL(3,2) COMMENT 'Review score for value, 0 to 5.',
  published_occupancy_l365d INT COMMENT 'Inside Airbnb''s estimated occupied nights in the last 365 days. Reference value for validation.',
  published_revenue_l365d DECIMAL(12,2) COMMENT 'Inside Airbnb''s estimated revenue in US dollars in the last 365 days. Reference value for validation.',
  listing_url STRING COMMENT 'Link to the listing on airbnb.com.',
  CONSTRAINT dim_listing_pk PRIMARY KEY (listing_id) RELY,
  CONSTRAINT dim_listing_host_fk FOREIGN KEY (host_id) REFERENCES dim_host(host_id) RELY
)
COMMENT 'One row per Airbnb listing in San Francisco (Inside Airbnb snapshot 2026-06-14): location, type, size, price, stay rules, license, review scores. Use for row-level questions about listings. Join to dim_host on host_id.'
TBLPROPERTIES ('quality' = 'gold')
AS
SELECT
  listing_id, host_id, name, description, neighbourhood, latitude, longitude,
  property_type, room_type, is_hotel, accommodates, bedrooms, beds, bathrooms, amenities,
  nightly_price, price_quote_checkin_date, price_quote_checkout_date,
  minimum_nights, maximum_nights, stay_type,
  has_availability, availability_30, availability_60, availability_90, availability_365,
  license, license_status,
  number_of_reviews, first_review, last_review,
  review_score_rating, review_score_accuracy, review_score_cleanliness, review_score_checkin,
  review_score_communication, review_score_location, review_score_value,
  published_occupancy_l365d, published_revenue_l365d, listing_url
FROM silver_listings;
