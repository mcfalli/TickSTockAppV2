-- Insert SIC code to sector/industry mapping into cache_entries as protected config
-- This preserves the critical mapping logic from maint_get_stocks.py

-- Technology Sector
INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at) VALUES
('cache_config', 'sic_mapping', '3571', '{"sector": "Technology", "industry": "Computer Hardware"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3572', '{"sector": "Technology", "industry": "Computer Storage & Peripherals"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3575', '{"sector": "Technology", "industry": "Computer Terminals"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3576', '{"sector": "Technology", "industry": "Computer Communications Equipment"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3577', '{"sector": "Technology", "industry": "Computer Peripheral Equipment"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3578', '{"sector": "Technology", "industry": "Calculating & Accounting Machines"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3661', '{"sector": "Technology", "industry": "Telephone & Telegraph Equipment"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3663', '{"sector": "Technology", "industry": "Radio & TV Broadcasting Equipment"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3669', '{"sector": "Technology", "industry": "Communications Equipment"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3672', '{"sector": "Technology", "industry": "Printed Circuit Boards"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3674', '{"sector": "Technology", "industry": "Semiconductors"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3679', '{"sector": "Technology", "industry": "Electronic Components"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '7370', '{"sector": "Technology", "industry": "Computer Programming & Data Processing"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '7371', '{"sector": "Technology", "industry": "Computer Programming Services"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '7372', '{"sector": "Technology", "industry": "Prepackaged Software"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '7373', '{"sector": "Technology", "industry": "Computer Integrated Systems Design"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '7374', '{"sector": "Technology", "industry": "Computer Processing & Data Preparation"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '7375', '{"sector": "Technology", "industry": "Information Retrieval Services"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '7376', '{"sector": "Technology", "industry": "Computer Facilities Management"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '7377', '{"sector": "Technology", "industry": "Computer Rental & Leasing"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '7378', '{"sector": "Technology", "industry": "Computer Maintenance & Repair"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '7379', '{"sector": "Technology", "industry": "Computer Related Services"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- Healthcare Sector  
INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at) VALUES
('cache_config', 'sic_mapping', '2833', '{"sector": "Healthcare", "industry": "Medicinal Chemicals"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '2834', '{"sector": "Healthcare", "industry": "Pharmaceutical Preparations"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '2835', '{"sector": "Healthcare", "industry": "In Vitro Diagnostics"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '2836', '{"sector": "Healthcare", "industry": "Biological Products"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3841', '{"sector": "Healthcare", "industry": "Surgical & Medical Instruments"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3842', '{"sector": "Healthcare", "industry": "Orthopedic & Prosthetic Appliances"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3845', '{"sector": "Healthcare", "industry": "Electromedical Equipment"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '5047', '{"sector": "Healthcare", "industry": "Medical Equipment Wholesale"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '8000', '{"sector": "Healthcare", "industry": "Health Services"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '8011', '{"sector": "Healthcare", "industry": "Offices of Doctors"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '8071', '{"sector": "Healthcare", "industry": "Medical Laboratories"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '8082', '{"sector": "Healthcare", "industry": "Home Health Care Services"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- Financial Services Sector
INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at) VALUES
('cache_config', 'sic_mapping', '6021', '{"sector": "Financial Services", "industry": "National Commercial Banks"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6022', '{"sector": "Financial Services", "industry": "State Commercial Banks"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6029', '{"sector": "Financial Services", "industry": "Commercial Banks"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6035', '{"sector": "Financial Services", "industry": "Savings Institutions"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6036', '{"sector": "Financial Services", "industry": "Savings Institutions"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6141', '{"sector": "Financial Services", "industry": "Personal Credit Institutions"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6153', '{"sector": "Financial Services", "industry": "Short-Term Business Credit"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6159', '{"sector": "Financial Services", "industry": "Miscellaneous Business Credit"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6162', '{"sector": "Financial Services", "industry": "Mortgage Bankers & Brokers"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6199', '{"sector": "Financial Services", "industry": "Finance Services"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6211', '{"sector": "Financial Services", "industry": "Security Brokers & Dealers"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6221', '{"sector": "Financial Services", "industry": "Commodity Contracts Brokers"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6282', '{"sector": "Financial Services", "industry": "Investment Advice"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6311', '{"sector": "Financial Services", "industry": "Life Insurance"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6321', '{"sector": "Financial Services", "industry": "Accident & Health Insurance"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6324', '{"sector": "Financial Services", "industry": "Hospital & Medical Service Plans"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6331', '{"sector": "Financial Services", "industry": "Fire, Marine & Casualty Insurance"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6351', '{"sector": "Financial Services", "industry": "Surety Insurance"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6361', '{"sector": "Financial Services", "industry": "Title Insurance"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6371', '{"sector": "Financial Services", "industry": "Pension, Health & Welfare Funds"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- Additional critical mappings (abbreviated for space - can add more as needed)
INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at) VALUES
('cache_config', 'sic_mapping', '2300', '{"sector": "Consumer Discretionary", "industry": "Apparel & Textiles"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3711', '{"sector": "Consumer Discretionary", "industry": "Motor Vehicles"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '1311', '{"sector": "Energy", "industry": "Crude Petroleum & Natural Gas"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '2911', '{"sector": "Energy", "industry": "Petroleum Refining"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '1540', '{"sector": "Industrials", "industry": "General Building Contractors"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3721', '{"sector": "Industrials", "industry": "Aircraft"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- SIC Range Fallback Rules (for ranges not covered by specific codes)
INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at) VALUES
('cache_config', 'sic_ranges', 'technology', '{"ranges": [{"start": 3570, "end": 3579, "sector": "Technology", "industry": "Computer & Office Equipment"}, {"start": 3660, "end": 3699, "sector": "Technology", "industry": "Electronic & Electrical Equipment"}, {"start": 7370, "end": 7379, "sector": "Technology", "industry": "Computer Programming & Data Processing"}, {"start": 3820, "end": 3829, "sector": "Technology", "industry": "Measuring & Controlling Devices"}]}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_ranges', 'healthcare', '{"ranges": [{"start": 2830, "end": 2839, "sector": "Healthcare", "industry": "Drugs"}, {"start": 3840, "end": 3849, "sector": "Healthcare", "industry": "Medical Instruments & Supplies"}, {"start": 8000, "end": 8099, "sector": "Healthcare", "industry": "Health Services"}, {"start": 8730, "end": 8739, "sector": "Healthcare", "industry": "Research & Testing Services"}]}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_ranges', 'financial', '{"ranges": [{"start": 6000, "end": 6099, "sector": "Financial Services", "industry": "Depository Institutions"}, {"start": 6100, "end": 6199, "sector": "Financial Services", "industry": "Non-Depository Credit Institutions"}, {"start": 6200, "end": 6299, "sector": "Financial Services", "industry": "Security & Commodity Brokers"}, {"start": 6300, "end": 6399, "sector": "Financial Services", "industry": "Insurance Carriers"}]}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_ranges', 'energy', '{"ranges": [{"start": 1300, "end": 1399, "sector": "Energy", "industry": "Oil & Gas Extraction"}, {"start": 2900, "end": 2999, "sector": "Energy", "industry": "Petroleum Refining"}, {"start": 4600, "end": 4699, "sector": "Energy", "industry": "Pipelines"}]}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_ranges', 'industrials', '{"ranges": [{"start": 1500, "end": 1599, "sector": "Industrials", "industry": "Building Construction"}, {"start": 3500, "end": 3569, "sector": "Industrials", "industry": "Industrial & Commercial Machinery"}, {"start": 3700, "end": 3799, "sector": "Industrials", "industry": "Transportation Equipment"}, {"start": 8700, "end": 8799, "sector": "Industrials", "industry": "Engineering & Management Services"}]}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_ranges', 'materials', '{"ranges": [{"start": 1000, "end": 1499, "sector": "Materials", "industry": "Mining"}, {"start": 2600, "end": 2699, "sector": "Materials", "industry": "Paper & Allied Products"}, {"start": 2800, "end": 2899, "sector": "Materials", "industry": "Chemicals & Allied Products"}, {"start": 3300, "end": 3399, "sector": "Materials", "industry": "Primary Metal Industries"}]}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_ranges', 'consumer_staples', '{"ranges": [{"start": 2000, "end": 2199, "sector": "Consumer Staples", "industry": "Food & Kindred Products"}]}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_ranges', 'utilities', '{"ranges": [{"start": 4900, "end": 4999, "sector": "Utilities", "industry": "Electric, Gas & Sanitary Services"}]}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_ranges', 'real_estate', '{"ranges": [{"start": 6500, "end": 6599, "sector": "Real Estate", "industry": "Real Estate"}]}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_ranges', 'communication', '{"ranges": [{"start": 2700, "end": 2799, "sector": "Communication Services", "industry": "Printing, Publishing & Allied Industries"}, {"start": 4800, "end": 4899, "sector": "Communication Services", "industry": "Communications"}]}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- Note: This is a subset of the full SIC mapping. The complete mapping from maint_get_stocks.py 
-- contains 180+ specific codes that should be fully imported for production use.