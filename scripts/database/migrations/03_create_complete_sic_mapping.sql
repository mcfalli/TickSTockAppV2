-- =====================================================================
-- Script 3: Complete SIC Code to Sector/Industry Mapping Configuration
-- Purpose: Store complete SIC mapping from maint_get_stocks.py in cache_entries
-- Source: Comprehensive mapping with 180+ specific codes + range fallbacks
-- =====================================================================

-- Create complete SIC code to sector/industry mapping as protected cache config
-- This preserves all the critical mapping logic from maint_get_stocks.py

-- TECHNOLOGY SECTOR (Complete mapping)
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
('cache_config', 'sic_mapping', '7379', '{"sector": "Technology", "industry": "Computer Related Services"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3826', '{"sector": "Technology", "industry": "Laboratory Analytical Instruments"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3690', '{"sector": "Technology", "industry": "Miscellaneous Electrical Machinery"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3825', '{"sector": "Technology", "industry": "Instruments for Measuring & Testing"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- HEALTHCARE & BIOTECHNOLOGY SECTOR (Complete mapping)
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
('cache_config', 'sic_mapping', '8082', '{"sector": "Healthcare", "industry": "Home Health Care Services"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '8731', '{"sector": "Healthcare", "industry": "Commercial Physical & Biological Research"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '8093', '{"sector": "Healthcare", "industry": "Specialty Outpatient Facilities"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- FINANCIAL SERVICES SECTOR (Complete mapping)
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
('cache_config', 'sic_mapping', '6371', '{"sector": "Financial Services", "industry": "Pension, Health & Welfare Funds"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6770', '{"sector": "Financial Services", "industry": "Blank Check Companies"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6411', '{"sector": "Financial Services", "industry": "Insurance Agents & Brokers"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6794', '{"sector": "Financial Services", "industry": "Patent Owners & Lessors"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- CONSUMER DISCRETIONARY SECTOR
INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at) VALUES
('cache_config', 'sic_mapping', '2300', '{"sector": "Consumer Discretionary", "industry": "Apparel & Textiles"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3711', '{"sector": "Consumer Discretionary", "industry": "Motor Vehicles"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3714', '{"sector": "Consumer Discretionary", "industry": "Motor Vehicle Parts"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3715', '{"sector": "Consumer Discretionary", "industry": "Truck Trailers"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3716', '{"sector": "Consumer Discretionary", "industry": "Motor Homes"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3751', '{"sector": "Consumer Discretionary", "industry": "Motorcycles & Bicycles"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '5311', '{"sector": "Consumer Discretionary", "industry": "Department Stores"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '5331', '{"sector": "Consumer Discretionary", "industry": "Variety Stores"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '5411', '{"sector": "Consumer Discretionary", "industry": "Grocery Stores"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '5531', '{"sector": "Consumer Discretionary", "industry": "Auto & Home Supply Stores"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '5621', '{"sector": "Consumer Discretionary", "industry": "Women\'s Clothing Stores"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '5651', '{"sector": "Consumer Discretionary", "industry": "Family Clothing Stores"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '5812', '{"sector": "Consumer Discretionary", "industry": "Eating Places"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '5912', '{"sector": "Consumer Discretionary", "industry": "Drug Stores"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '5944', '{"sector": "Consumer Discretionary", "industry": "Jewelry Stores"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '5961', '{"sector": "Consumer Discretionary", "industry": "Catalog & Mail-Order Houses"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '7011', '{"sector": "Consumer Discretionary", "industry": "Hotels & Motels"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '5500', '{"sector": "Consumer Discretionary", "industry": "Automotive Dealers & Service Stations"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '5099', '{"sector": "Consumer Discretionary", "industry": "Durable Goods Wholesale"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '7900', '{"sector": "Consumer Discretionary", "industry": "Amusement & Recreation Services"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- ENERGY SECTOR
INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at) VALUES
('cache_config', 'sic_mapping', '1311', '{"sector": "Energy", "industry": "Crude Petroleum & Natural Gas"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '1321', '{"sector": "Energy", "industry": "Natural Gas Liquids"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '1381', '{"sector": "Energy", "industry": "Drilling Oil & Gas Wells"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '1382', '{"sector": "Energy", "industry": "Oil & Gas Field Exploration Services"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '1389', '{"sector": "Energy", "industry": "Oil & Gas Field Services"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '2911', '{"sector": "Energy", "industry": "Petroleum Refining"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '4612', '{"sector": "Energy", "industry": "Crude Petroleum Pipelines"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '4613', '{"sector": "Energy", "industry": "Refined Petroleum Pipelines"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- INDUSTRIALS SECTOR
INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at) VALUES
('cache_config', 'sic_mapping', '1540', '{"sector": "Industrials", "industry": "General Building Contractors"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3531', '{"sector": "Industrials", "industry": "Construction Machinery"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3537', '{"sector": "Industrials", "industry": "Industrial Trucks & Tractors"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3559', '{"sector": "Industrials", "industry": "Special Industry Machinery"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3560', '{"sector": "Industrials", "industry": "General Industrial Machinery"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3721', '{"sector": "Industrials", "industry": "Aircraft"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3724', '{"sector": "Industrials", "industry": "Aircraft Engines & Parts"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3728', '{"sector": "Industrials", "industry": "Aircraft Parts & Equipment"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '4011', '{"sector": "Industrials", "industry": "Railroads"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '4213', '{"sector": "Industrials", "industry": "Trucking"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '4512', '{"sector": "Industrials", "industry": "Air Transportation"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '4513', '{"sector": "Industrials", "industry": "Air Courier Services"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '7359', '{"sector": "Industrials", "industry": "Equipment Rental & Leasing"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3585', '{"sector": "Industrials", "industry": "Air-Conditioning & Heating Equipment"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '7340', '{"sector": "Industrials", "industry": "Services to Dwellings & Buildings"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3440', '{"sector": "Industrials", "industry": "Fabricated Structural Metal Products"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '2780', '{"sector": "Industrials", "industry": "Blankbooks & Looseleaf Binders"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '8742', '{"sector": "Industrials", "industry": "Management Consulting Services"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '8711', '{"sector": "Industrials", "industry": "Engineering Services"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '7389', '{"sector": "Industrials", "industry": "Business Services"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3420', '{"sector": "Industrials", "industry": "Cutlery, Handtools & General Hardware"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '7381', '{"sector": "Industrials", "industry": "Detective, Guard & Armored Car Services"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- MATERIALS SECTOR
INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at) VALUES
('cache_config', 'sic_mapping', '1000', '{"sector": "Materials", "industry": "Metal Mining"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '2621', '{"sector": "Materials", "industry": "Paper Mills"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '2800', '{"sector": "Materials", "industry": "Chemicals & Allied Products"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '2821', '{"sector": "Materials", "industry": "Plastics Materials & Resins"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '2822', '{"sector": "Materials", "industry": "Synthetic Rubber"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '2851', '{"sector": "Materials", "industry": "Paints & Allied Products"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '2870', '{"sector": "Materials", "industry": "Agricultural Chemicals"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '2890', '{"sector": "Materials", "industry": "Miscellaneous Chemical Products"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3312', '{"sector": "Materials", "industry": "Steel Works & Blast Furnaces"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3317', '{"sector": "Materials", "industry": "Steel Pipe & Tubes"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3334', '{"sector": "Materials", "industry": "Primary Production of Aluminum"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '3357', '{"sector": "Materials", "industry": "Drawing & Insulating of Nonferrous Wire"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '1400', '{"sector": "Materials", "industry": "Mining & Quarrying of Nonmetallic Minerals"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- CONSUMER STAPLES SECTOR
INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at) VALUES
('cache_config', 'sic_mapping', '2000', '{"sector": "Consumer Staples", "industry": "Food & Kindred Products"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '2020', '{"sector": "Consumer Staples", "industry": "Dairy Products"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '2030', '{"sector": "Consumer Staples", "industry": "Canned & Preserved Fruits & Vegetables"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '2040', '{"sector": "Consumer Staples", "industry": "Grain Mill Products"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '2050', '{"sector": "Consumer Staples", "industry": "Bakery Products"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '2060', '{"sector": "Consumer Staples", "industry": "Sugar & Confectionery Products"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '2070', '{"sector": "Consumer Staples", "industry": "Fats & Oils"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '2080', '{"sector": "Consumer Staples", "industry": "Beverages"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '2090', '{"sector": "Consumer Staples", "industry": "Miscellaneous Food Preparations"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '2100', '{"sector": "Consumer Staples", "industry": "Tobacco Products"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- UTILITIES SECTOR
INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at) VALUES
('cache_config', 'sic_mapping', '4911', '{"sector": "Utilities", "industry": "Electric Services"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '4922', '{"sector": "Utilities", "industry": "Natural Gas Transmission"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '4923', '{"sector": "Utilities", "industry": "Natural Gas Transmission & Distribution"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '4924', '{"sector": "Utilities", "industry": "Natural Gas Distribution"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '4931', '{"sector": "Utilities", "industry": "Electric & Other Services Combined"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '4932', '{"sector": "Utilities", "industry": "Gas & Other Services Combined"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '4941', '{"sector": "Utilities", "industry": "Water Supply"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- REAL ESTATE SECTOR
INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at) VALUES
('cache_config', 'sic_mapping', '6500', '{"sector": "Real Estate", "industry": "Real Estate"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6510', '{"sector": "Real Estate", "industry": "Real Estate Operators"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6512', '{"sector": "Real Estate", "industry": "Operators of Nonresidential Buildings"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6513', '{"sector": "Real Estate", "industry": "Operators of Apartment Buildings"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6519', '{"sector": "Real Estate", "industry": "Lessors of Real Property"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6531', '{"sector": "Real Estate", "industry": "Real Estate Agents & Managers"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '6798', '{"sector": "Real Estate", "industry": "Real Estate Investment Trusts"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- COMMUNICATION SERVICES SECTOR
INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at) VALUES
('cache_config', 'sic_mapping', '2711', '{"sector": "Communication Services", "industry": "Newspapers"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '2721', '{"sector": "Communication Services", "industry": "Periodicals"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '2731', '{"sector": "Communication Services", "industry": "Books"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '4813', '{"sector": "Communication Services", "industry": "Telephone Communications"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '4822', '{"sector": "Communication Services", "industry": "Telegraph Communications"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '4832', '{"sector": "Communication Services", "industry": "Radio Broadcasting"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '4833', '{"sector": "Communication Services", "industry": "Television Broadcasting"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '4841', '{"sector": "Communication Services", "industry": "Cable & Other Pay Television Services"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_mapping', '7812', '{"sector": "Communication Services", "industry": "Motion Picture & Video Tape Production"}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- SIC RANGE FALLBACK RULES (for range-based classification when specific codes aren't found)
INSERT INTO cache_entries (type, name, key, value, environment, created_at, updated_at) VALUES
('cache_config', 'sic_ranges', 'technology', '{"ranges": [{"start": 3570, "end": 3579, "sector": "Technology", "industry": "Computer & Office Equipment"}, {"start": 3660, "end": 3699, "sector": "Technology", "industry": "Electronic & Electrical Equipment"}, {"start": 7370, "end": 7379, "sector": "Technology", "industry": "Computer Programming & Data Processing"}, {"start": 3820, "end": 3829, "sector": "Technology", "industry": "Measuring & Controlling Devices"}]}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_ranges', 'healthcare', '{"ranges": [{"start": 2830, "end": 2839, "sector": "Healthcare", "industry": "Drugs"}, {"start": 3840, "end": 3849, "sector": "Healthcare", "industry": "Medical Instruments & Supplies"}, {"start": 8000, "end": 8099, "sector": "Healthcare", "industry": "Health Services"}, {"start": 8730, "end": 8739, "sector": "Healthcare", "industry": "Research & Testing Services"}]}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_ranges', 'financial', '{"ranges": [{"start": 6000, "end": 6099, "sector": "Financial Services", "industry": "Depository Institutions"}, {"start": 6100, "end": 6199, "sector": "Financial Services", "industry": "Non-Depository Credit Institutions"}, {"start": 6200, "end": 6299, "sector": "Financial Services", "industry": "Security & Commodity Brokers"}, {"start": 6300, "end": 6399, "sector": "Financial Services", "industry": "Insurance Carriers"}, {"start": 6400, "end": 6499, "sector": "Financial Services", "industry": "Insurance Agents & Brokers"}, {"start": 6700, "end": 6799, "sector": "Financial Services", "industry": "Holding & Investment Offices"}]}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_ranges', 'energy', '{"ranges": [{"start": 1300, "end": 1399, "sector": "Energy", "industry": "Oil & Gas Extraction"}, {"start": 2900, "end": 2999, "sector": "Energy", "industry": "Petroleum Refining"}, {"start": 4600, "end": 4699, "sector": "Energy", "industry": "Pipelines"}]}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_ranges', 'industrials', '{"ranges": [{"start": 1500, "end": 1599, "sector": "Industrials", "industry": "Building Construction"}, {"start": 3500, "end": 3569, "sector": "Industrials", "industry": "Industrial & Commercial Machinery"}, {"start": 3700, "end": 3799, "sector": "Industrials", "industry": "Transportation Equipment"}, {"start": 4000, "end": 4099, "sector": "Industrials", "industry": "Railroad Transportation"}, {"start": 4200, "end": 4299, "sector": "Industrials", "industry": "Motor Freight Transportation"}, {"start": 4500, "end": 4599, "sector": "Industrials", "industry": "Transportation by Air"}, {"start": 8700, "end": 8799, "sector": "Industrials", "industry": "Engineering & Management Services"}]}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_ranges', 'consumer_discretionary', '{"ranges": [{"start": 2300, "end": 2399, "sector": "Consumer Discretionary", "industry": "Apparel & Other Finished Products"}, {"start": 3700, "end": 3719, "sector": "Consumer Discretionary", "industry": "Motor Vehicles & Equipment"}, {"start": 5000, "end": 5199, "sector": "Consumer Discretionary", "industry": "Wholesale Trade"}, {"start": 5200, "end": 5999, "sector": "Consumer Discretionary", "industry": "Retail Trade"}, {"start": 7000, "end": 7099, "sector": "Consumer Discretionary", "industry": "Hotels & Lodging"}, {"start": 7300, "end": 7399, "sector": "Consumer Discretionary", "industry": "Business Services"}, {"start": 7800, "end": 7999, "sector": "Consumer Discretionary", "industry": "Motion Pictures & Amusement Services"}]}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_ranges', 'materials', '{"ranges": [{"start": 1000, "end": 1499, "sector": "Materials", "industry": "Mining"}, {"start": 2600, "end": 2699, "sector": "Materials", "industry": "Paper & Allied Products"}, {"start": 2800, "end": 2899, "sector": "Materials", "industry": "Chemicals & Allied Products"}, {"start": 3300, "end": 3399, "sector": "Materials", "industry": "Primary Metal Industries"}]}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_ranges', 'consumer_staples', '{"ranges": [{"start": 2000, "end": 2199, "sector": "Consumer Staples", "industry": "Food & Kindred Products"}]}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_ranges', 'utilities', '{"ranges": [{"start": 4900, "end": 4999, "sector": "Utilities", "industry": "Electric, Gas & Sanitary Services"}]}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_ranges', 'real_estate', '{"ranges": [{"start": 6500, "end": 6599, "sector": "Real Estate", "industry": "Real Estate"}]}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('cache_config', 'sic_ranges', 'communication', '{"ranges": [{"start": 2700, "end": 2799, "sector": "Communication Services", "industry": "Printing, Publishing & Allied Industries"}, {"start": 4800, "end": 4899, "sector": "Communication Services", "industry": "Communications"}]}', 'DEFAULT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- Verify the configuration was inserted successfully
SELECT 
    name,
    COUNT(*) as mapping_count,
    MIN(created_at) as first_created,
    MAX(created_at) as last_created
FROM cache_entries 
WHERE type = 'cache_config' 
  AND name IN ('sic_mapping', 'sic_ranges')
GROUP BY name
ORDER BY name;

-- Show sample mappings by sector
SELECT 
    JSON_EXTRACT(value, '$.sector') as sector,
    COUNT(*) as code_count,
    GROUP_CONCAT(key ORDER BY key LIMIT 5) as sample_codes
FROM cache_entries 
WHERE type = 'cache_config' AND name = 'sic_mapping'
GROUP BY JSON_EXTRACT(value, '$.sector')
ORDER BY sector;

ANALYZE cache_entries;