CREATE TABLE series (
    id            TEXT PRIMARY KEY,
    label         TEXT NOT NULL,
    unit          TEXT NOT NULL,
    source        TEXT NOT NULL DEFAULT 'FRED',
    frequency     TEXT NOT NULL,
    notes         TEXT
);

CREATE TABLE observation (
    series_id   TEXT      NOT NULL REFERENCES series(id),
    obs_date    DATE      NOT NULL,
    value       DOUBLE PRECISION,
    PRIMARY KEY (series_id, obs_date)
);
CREATE INDEX observation_series_date_idx ON observation (series_id, obs_date DESC);

CREATE TABLE monthly_fact (
    obs_date              DATE PRIMARY KEY,
    median_price          DOUBLE PRECISION,
    median_income         DOUBLE PRECISION,
    mortgage_rate_30y     DOUBLE PRECISION,
    oer_index             DOUBLE PRECISION,
    cs_hpi                DOUBLE PRECISION,
    zhvi                  DOUBLE PRECISION,
    treasury_10y          DOUBLE PRECISION,
    cpi                   DOUBLE PRECISION,
    real_dpi_per_capita   DOUBLE PRECISION
);

CREATE TABLE composite_history (
    obs_date            DATE PRIMARY KEY,
    z_affordability     DOUBLE PRECISION NOT NULL,
    z_price_income      DOUBLE PRECISION NOT NULL,
    z_price_rent        DOUBLE PRECISION NOT NULL,
    composite_z         DOUBLE PRECISION NOT NULL,
    overvaluation_pct   DOUBLE PRECISION NOT NULL,
    percentile_rank     DOUBLE PRECISION NOT NULL
);

INSERT INTO series (id, label, unit, frequency, notes) VALUES
  ('MSPUS',                  'Median sale price, existing homes',     'USD',           'Q', NULL),
  ('MEHOINUSA646N',          'Median household income',               'USD',           'A', 'Pre-1984 backfilled from A229RX0'),
  ('MORTGAGE30US',           '30-year fixed mortgage rate',           'percent',       'W', NULL),
  ('CUSR0000SEHC',           'CPI: Owners equivalent rent',           'index 1982=100','M', NULL),
  ('CSUSHPINSA',             'Case-Shiller National HPI',             'index Jan2000=100','M', NULL),
  ('USAUCSFRCONDOSMSAMID',   'ZHVI National',                         'USD',           'M', NULL),
  ('DGS10',                  '10-year Treasury constant maturity',    'percent',       'D', NULL),
  ('CPIAUCSL',               'CPI All Items',                         'index 1982-84=100','M', NULL),
  ('A229RX0',                'Real disposable personal income / capita','USD chained 2017','M', 'Used for pre-1984 income stitch');
