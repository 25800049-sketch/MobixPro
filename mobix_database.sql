-- MOBIX Mobile Shop Management System
-- MySQL / MariaDB Database Dump for phpMyAdmin
-- Compatible with MySQL 5.7+, MySQL 8.0+, and MariaDB 10.x+

SET FOREIGN_KEY_CHECKS = 0;
SET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';
SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS `mobix_db`;
USE `mobix_db`;

-- Table structure for `accessories`
DROP TABLE IF EXISTS `accessories`;
CREATE TABLE accessories (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(120) NOT NULL, 
	category VARCHAR(60) NOT NULL, 
	brand VARCHAR(60), 
	compatibility VARCHAR(120), 
	purchase_price FLOAT NOT NULL, 
	selling_price FLOAT NOT NULL, 
	stock_quantity INTEGER, 
	min_stock_alert INTEGER, 
	created_at DATETIME, 
	PRIMARY KEY (id)
);

-- Table structure for `customers`
DROP TABLE IF EXISTS `customers`;
CREATE TABLE customers (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(120) NOT NULL, 
	phone VARCHAR(20) NOT NULL, 
	email VARCHAR(120), 
	address TEXT, 
	outstanding_balance FLOAT, 
	created_at DATETIME, 
	PRIMARY KEY (id)
);

-- Table structure for `lost_sales_requests`
DROP TABLE IF EXISTS `lost_sales_requests`;
CREATE TABLE lost_sales_requests (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	customer_name VARCHAR(120) NOT NULL, 
	customer_phone VARCHAR(20) NOT NULL, 
	customer_email VARCHAR(120), 
	brand VARCHAR(60) NOT NULL, 
	model VARCHAR(100) NOT NULL, 
	variant VARCHAR(80), 
	max_budget FLOAT, 
	status VARCHAR(20), 
	notes TEXT, 
	created_at DATETIME, 
	PRIMARY KEY (id)
);

-- Table structure for `mobiles`
DROP TABLE IF EXISTS `mobiles`;
CREATE TABLE mobiles (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	brand VARCHAR(64) NOT NULL, 
	model VARCHAR(100) NOT NULL, 
	imei_1 VARCHAR(30) NOT NULL, 
	imei_2 VARCHAR(30), 
	ram VARCHAR(20) NOT NULL, 
	storage VARCHAR(20) NOT NULL, 
	color VARCHAR(40) NOT NULL, 
	purchase_price FLOAT NOT NULL, 
	selling_price FLOAT NOT NULL, 
	stock_quantity INTEGER, 
	image_url VARCHAR(350), 
	display VARCHAR(120), 
	processor VARCHAR(120), 
	camera VARCHAR(120), 
	battery VARCHAR(80), 
	warranty_months INTEGER, 
	status VARCHAR(20), 
	min_stock_alert INTEGER, 
	created_at DATETIME, 
	PRIMARY KEY (id)
);

-- Table structure for `suppliers`
DROP TABLE IF EXISTS `suppliers`;
CREATE TABLE suppliers (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(120) NOT NULL, 
	company VARCHAR(120) NOT NULL, 
	phone VARCHAR(20) NOT NULL, 
	email VARCHAR(120), 
	address TEXT, 
	balance_due FLOAT, 
	created_at DATETIME, 
	PRIMARY KEY (id)
);

-- Table structure for `users`
DROP TABLE IF EXISTS `users`;
CREATE TABLE users (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	username VARCHAR(64) NOT NULL, 
	password_hash VARCHAR(256) NOT NULL, 
	full_name VARCHAR(120) NOT NULL, 
	`role` VARCHAR(20) NOT NULL, 
	email VARCHAR(120), 
	phone VARCHAR(20), 
	is_active BOOL, 
	created_at DATETIME, 
	monthly_salary FLOAT, 
	daily_rate FLOAT, 
	salary_type VARCHAR(20), 
	PRIMARY KEY (id)
);

-- Table structure for `attendance`
DROP TABLE IF EXISTS `attendance`;
CREATE TABLE attendance (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id INTEGER NOT NULL, 
	date DATE NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	check_in VARCHAR(10), 
	check_out VARCHAR(10), 
	notes VARCHAR(255), 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_attendance_date UNIQUE (user_id, date), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

-- Table structure for `invoices`
DROP TABLE IF EXISTS `invoices`;
CREATE TABLE invoices (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	invoice_number VARCHAR(50) NOT NULL, 
	customer_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	subtotal FLOAT, 
	tax_rate FLOAT, 
	tax_amount FLOAT, 
	discount_amount FLOAT, 
	exchange_discount FLOAT, 
	final_total FLOAT, 
	payment_mode VARCHAR(30), 
	payment_status VARCHAR(20), 
	notes TEXT, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

-- Table structure for `payroll_records`
DROP TABLE IF EXISTS `payroll_records`;
CREATE TABLE payroll_records (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id INTEGER NOT NULL, 
	month_year VARCHAR(7) NOT NULL, 
	total_working_days INTEGER, 
	present_days FLOAT, 
	half_days INTEGER, 
	paid_leaves FLOAT, 
	effective_work_days FLOAT, 
	base_salary FLOAT NOT NULL, 
	daily_wage FLOAT NOT NULL, 
	earned_salary FLOAT NOT NULL, 
	bonus_incentive FLOAT, 
	advances_deducted FLOAT, 
	net_salary FLOAT NOT NULL, 
	payment_status VARCHAR(20), 
	payment_date DATE, 
	payment_method VARCHAR(50), 
	notes TEXT, 
	generated_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

-- Table structure for `repair_tickets`
DROP TABLE IF EXISTS `repair_tickets`;
CREATE TABLE repair_tickets (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	ticket_no VARCHAR(40) NOT NULL, 
	customer_id INTEGER NOT NULL, 
	technician_id INTEGER, 
	brand VARCHAR(60) NOT NULL, 
	model VARCHAR(100) NOT NULL, 
	imei VARCHAR(30), 
	problem_description TEXT NOT NULL, 
	estimated_cost FLOAT, 
	final_cost FLOAT, 
	advance_paid FLOAT, 
	status VARCHAR(30), 
	parts_used TEXT, 
	technician_notes TEXT, 
	warranty_days INTEGER, 
	delivery_date DATE, 
	payment_status VARCHAR(20), 
	payment_mode VARCHAR(30), 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id), 
	FOREIGN KEY(technician_id) REFERENCES users (id)
);

-- Table structure for `supplier_purchases`
DROP TABLE IF EXISTS `supplier_purchases`;
CREATE TABLE supplier_purchases (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	supplier_id INTEGER NOT NULL, 
	invoice_no VARCHAR(50) NOT NULL, 
	total_amount FLOAT NOT NULL, 
	paid_amount FLOAT, 
	status VARCHAR(20), 
	notes TEXT, 
	purchase_date DATE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(supplier_id) REFERENCES suppliers (id)
);

-- Table structure for `emi_accounts`
DROP TABLE IF EXISTS `emi_accounts`;
CREATE TABLE emi_accounts (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	invoice_id INTEGER NOT NULL, 
	customer_id INTEGER NOT NULL, 
	total_amount FLOAT NOT NULL, 
	down_payment FLOAT, 
	principal_remaining FLOAT NOT NULL, 
	emi_amount FLOAT NOT NULL, 
	tenure_months INTEGER NOT NULL, 
	fine_per_cycle FLOAT, 
	start_date DATE, 
	status VARCHAR(20), 
	notes VARCHAR(200), 
	PRIMARY KEY (id), 
	FOREIGN KEY(invoice_id) REFERENCES invoices (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id)
);

-- Table structure for `exchange_records`
DROP TABLE IF EXISTS `exchange_records`;
CREATE TABLE exchange_records (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	customer_id INTEGER, 
	invoice_id INTEGER, 
	brand VARCHAR(60) NOT NULL, 
	model VARCHAR(100) NOT NULL, 
	imei VARCHAR(30), 
	original_price FLOAT, 
	age_months INTEGER, 
	storage VARCHAR(20), 
	battery_health INTEGER, 
	condition_screen VARCHAR(40), 
	condition_body VARCHAR(40), 
	camera_working BOOL, 
	face_or_touch_id BOOL, 
	ai_estimated_value FLOAT NOT NULL, 
	offered_value FLOAT NOT NULL, 
	status VARCHAR(20), 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id), 
	FOREIGN KEY(invoice_id) REFERENCES invoices (id)
);

-- Table structure for `invoice_items`
DROP TABLE IF EXISTS `invoice_items`;
CREATE TABLE invoice_items (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	invoice_id INTEGER NOT NULL, 
	item_type VARCHAR(20) NOT NULL, 
	mobile_id INTEGER, 
	accessory_id INTEGER, 
	item_name VARCHAR(150) NOT NULL, 
	imei VARCHAR(50), 
	quantity INTEGER, 
	unit_price FLOAT NOT NULL, 
	total_price FLOAT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(invoice_id) REFERENCES invoices (id), 
	FOREIGN KEY(mobile_id) REFERENCES mobiles (id), 
	FOREIGN KEY(accessory_id) REFERENCES accessories (id)
);

-- Table structure for `pre_bookings`
DROP TABLE IF EXISTS `pre_bookings`;
CREATE TABLE pre_bookings (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	booking_no VARCHAR(40) NOT NULL, 
	customer_id INTEGER NOT NULL, 
	brand VARCHAR(60) NOT NULL, 
	model VARCHAR(100) NOT NULL, 
	variant VARCHAR(80) NOT NULL, 
	color VARCHAR(50), 
	storage VARCHAR(30), 
	expected_price FLOAT, 
	token_advance FLOAT NOT NULL, 
	payment_mode VARCHAR(30), 
	payment_status VARCHAR(20), 
	booking_source VARCHAR(30), 
	queue_priority INTEGER, 
	status VARCHAR(30), 
	allocated_mobile_id INTEGER, 
	invoice_id INTEGER, 
	expected_delivery_date DATE, 
	notes TEXT, 
	created_at DATETIME, 
	fulfilled_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id), 
	FOREIGN KEY(allocated_mobile_id) REFERENCES mobiles (id), 
	FOREIGN KEY(invoice_id) REFERENCES invoices (id)
);

-- Table structure for `salary_advances`
DROP TABLE IF EXISTS `salary_advances`;
CREATE TABLE salary_advances (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id INTEGER NOT NULL, 
	amount FLOAT NOT NULL, 
	date DATE, 
	reason VARCHAR(255), 
	is_settled BOOL, 
	payroll_record_id INTEGER, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(payroll_record_id) REFERENCES payroll_records (id)
);

-- Table structure for `emi_installments`
DROP TABLE IF EXISTS `emi_installments`;
CREATE TABLE emi_installments (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	emi_account_id INTEGER NOT NULL, 
	installment_no INTEGER NOT NULL, 
	due_date DATE NOT NULL, 
	amount FLOAT NOT NULL, 
	fine_amount FLOAT, 
	paid_amount FLOAT, 
	payment_date DATE, 
	payment_mode VARCHAR(30), 
	status VARCHAR(20), 
	PRIMARY KEY (id), 
	FOREIGN KEY(emi_account_id) REFERENCES emi_accounts (id)
);

-- Dumping data for table `accessories`
INSERT INTO `accessories` (`id`, `name`, `category`, `brand`, `compatibility`, `purchase_price`, `selling_price`, `stock_quantity`, `min_stock_alert`, `created_at`) VALUES (1, '65W GaN Dual USB-C Fast Charger', 'Chargers', 'Anker', 'All Type-C Laptops & Mobiles', 1400.0, 2499.0, 15, 5, '2026-09-07 14:01:11.184148');
INSERT INTO `accessories` (`id`, `name`, `category`, `brand`, `compatibility`, `purchase_price`, `selling_price`, `stock_quantity`, `min_stock_alert`, `created_at`) VALUES (2, 'Apple 20W USB-C Power Adapter', 'Chargers', 'Apple', 'iPhone 11/12/13/14/15', 1250.0, 1899.0, 22, 5, '2026-09-07 14:01:11.184148');
INSERT INTO `accessories` (`id`, `name`, `category`, `brand`, `compatibility`, `purchase_price`, `selling_price`, `stock_quantity`, `min_stock_alert`, `created_at`) VALUES (3, 'boAt Rockerz 450 Bluetooth Headset', 'Earphones', 'boAt', 'Universal Bluetooth', 950.0, 1499.0, 14, 4, '2026-09-07 14:01:11.184148');
INSERT INTO `accessories` (`id`, `name`, `category`, `brand`, `compatibility`, `purchase_price`, `selling_price`, `stock_quantity`, `min_stock_alert`, `created_at`) VALUES (4, 'OnePlus Buds 3 ANC Earbuds', 'Earphones', 'OnePlus', 'Universal Bluetooth 5.3', 3900.0, 5499.0, 8, 3, '2026-09-07 14:01:11.184148');
INSERT INTO `accessories` (`id`, `name`, `category`, `brand`, `compatibility`, `purchase_price`, `selling_price`, `stock_quantity`, `min_stock_alert`, `created_at`) VALUES (5, '20,000mAh 22.5W Fast Power Bank', 'Power banks', 'Mi', 'USB-A & Type-C', 1350.0, 1999.0, 12, 4, '2026-09-07 14:01:11.184148');
INSERT INTO `accessories` (`id`, `name`, `category`, `brand`, `compatibility`, `purchase_price`, `selling_price`, `stock_quantity`, `min_stock_alert`, `created_at`) VALUES (6, 'Heavy-Duty Magnetic Armor Case', 'Cases & Covers', 'Spigen', 'iPhone 15 Series', 450.0, 999.0, 2, 5, '2026-09-07 14:01:11.184148');
INSERT INTO `accessories` (`id`, `name`, `category`, `brand`, `compatibility`, `purchase_price`, `selling_price`, `stock_quantity`, `min_stock_alert`, `created_at`) VALUES (7, '9H Edge-to-Edge Tempered Glass Screen Protector', 'Screen Protectors', 'GorillaShield', 'Samsung S24 / S23 Series', 80.0, 299.0, 45, 10, '2026-09-07 14:01:11.184148');
INSERT INTO `accessories` (`id`, `name`, `category`, `brand`, `compatibility`, `purchase_price`, `selling_price`, `stock_quantity`, `min_stock_alert`, `created_at`) VALUES (8, '100W Braided USB-C to USB-C Fast Cable (2m)', 'Cables', 'Baseus', 'Type-C High Speed', 220.0, 599.0, 30, 8, '2026-09-07 14:01:11.184148');
INSERT INTO `accessories` (`id`, `name`, `category`, `brand`, `compatibility`, `purchase_price`, `selling_price`, `stock_quantity`, `min_stock_alert`, `created_at`) VALUES (9, 'Noise ColorFit Pro 5 Smart Watch', 'Smart Watches', 'Noise', 'Android & iOS', 2200.0, 3499.0, 7, 3, '2026-09-07 14:01:11.184148');

-- Dumping data for table `customers`
INSERT INTO `customers` (`id`, `name`, `phone`, `email`, `address`, `outstanding_balance`, `created_at`) VALUES (1, 'Rahul Sharma', '9820112345', 'rahul.sharma@gmail.com', '402, Sunshine Apts, Bandra West, Mumbai', 72600.0, '2026-09-07 14:01:11.163111');
INSERT INTO `customers` (`id`, `name`, `phone`, `email`, `address`, `outstanding_balance`, `created_at`) VALUES (2, 'Priya Patel', '9898067890', 'priya.patel@yahoo.com', '12, Navrangpura, Ahmedabad', 20200.0, '2026-09-07 14:01:11.163111');
INSERT INTO `customers` (`id`, `name`, `phone`, `email`, `address`, `outstanding_balance`, `created_at`) VALUES (3, 'Amit Verma', '9711054321', 'amit.verma@outlook.com', 'B-14, Connaught Place, New Delhi', 0.0, '2026-09-07 14:01:11.163111');
INSERT INTO `customers` (`id`, `name`, `phone`, `email`, `address`, `outstanding_balance`, `created_at`) VALUES (4, 'Sneha Kulkarni', '9422098765', 'sneha.k@gmail.com', '88, Kothrud, Pune', 0.0, '2026-09-07 14:01:11.163111');
INSERT INTO `customers` (`id`, `name`, `phone`, `email`, `address`, `outstanding_balance`, `created_at`) VALUES (5, 'Vikram Reddy', '9949011223', 'vikram.reddy@gmail.com', 'Plot 45, Jubilee Hills, Hyderabad', 0.0, '2026-09-07 14:01:11.163111');
INSERT INTO `customers` (`id`, `name`, `phone`, `email`, `address`, `outstanding_balance`, `created_at`) VALUES (6, 'Test Checkout Customer', '9988776655', 'testcust@gmail.com', NULL, 0.0, '2026-09-07 14:01:12.543594');

-- Dumping data for table `mobiles`
INSERT INTO `mobiles` (`id`, `brand`, `model`, `imei_1`, `imei_2`, `ram`, `storage`, `color`, `purchase_price`, `selling_price`, `stock_quantity`, `warranty_months`, `status`, `min_stock_alert`, `created_at`, `image_url`, `display`, `processor`, `camera`, `battery`) VALUES (1, 'Apple', 'iPhone 15 Pro Max', '359128374829101', '359128374829102', '8GB', '256GB', 'Natural Titanium', 125000.0, 139900.0, 1, 12, 'in_stock', 2, '2026-09-07 14:01:11.175107', '/static/img/phones/iphone_15_pro_max.jpg', '6.7" Super Retina XDR OLED, 120Hz ProMotion', 'Apple A17 Pro (3nm)', '48MP Main + 12MP Ultra-wide + 12MP 5x Telephoto', '4422 mAh, 25W Fast Charge, MagSafe');
INSERT INTO `mobiles` (`id`, `brand`, `model`, `imei_1`, `imei_2`, `ram`, `storage`, `color`, `purchase_price`, `selling_price`, `stock_quantity`, `warranty_months`, `status`, `min_stock_alert`, `created_at`, `image_url`, `display`, `processor`, `camera`, `battery`) VALUES (2, 'Apple', 'iPhone 14', '359128374829201', NULL, '6GB', '128GB', 'Starlight', 52000.0, 59999.0, 6, 12, 'in_stock', 2, '2026-09-07 14:01:11.175107', '/static/img/phones/iphone_14.jpg', '6.1" Super Retina XDR OLED, HDR10', 'Apple A15 Bionic (5nm)', '12MP Dual Pixel OIS + 12MP Ultra-wide', '3279 mAh, 20W Fast Charge');
INSERT INTO `mobiles` (`id`, `brand`, `model`, `imei_1`, `imei_2`, `ram`, `storage`, `color`, `purchase_price`, `selling_price`, `stock_quantity`, `warranty_months`, `status`, `min_stock_alert`, `created_at`, `image_url`, `display`, `processor`, `camera`, `battery`) VALUES (3, 'Samsung', 'Galaxy S24 Ultra', '359128374829301', '359128374829302', '12GB', '256GB', 'Titanium Gray', 114000.0, 129999.0, 3, 12, 'in_stock', 2, '2026-09-07 14:01:11.175107', '/static/img/phones/galaxy_s24_ultra.jpg', '6.8" Dynamic LTPO AMOLED 2X, 120Hz, 2600 nits', 'Snapdragon 8 Gen 3 for Galaxy (4nm)', '200MP OIS + 50MP 5x Periscope + 10MP 3x + 12MP Ultra-wide', '5000 mAh, 45W Wired, 15W Wireless');
INSERT INTO `mobiles` (`id`, `brand`, `model`, `imei_1`, `imei_2`, `ram`, `storage`, `color`, `purchase_price`, `selling_price`, `stock_quantity`, `warranty_months`, `status`, `min_stock_alert`, `created_at`, `image_url`, `display`, `processor`, `camera`, `battery`) VALUES (4, 'Samsung', 'Galaxy A55 5G', '359128374829401', '359128374829402', '8GB', '128GB', 'Awesome Iceblue', 31000.0, 36999.0, 1, 12, 'in_stock', 2, '2026-09-07 14:01:11.175107', '/static/img/phones/galaxy_a55.jpg', '6.6" Super AMOLED 120Hz Gorilla Glass Victus+', 'Samsung Exynos 1480 (4nm)', '50MP OIS Main + 12MP Ultra-wide + 5MP Macro', '5000 mAh, 25W Fast Charging');
INSERT INTO `mobiles` (`id`, `brand`, `model`, `imei_1`, `imei_2`, `ram`, `storage`, `color`, `purchase_price`, `selling_price`, `stock_quantity`, `warranty_months`, `status`, `min_stock_alert`, `created_at`, `image_url`, `display`, `processor`, `camera`, `battery`) VALUES (5, 'OnePlus', '12', '359128374829501', '359128374829502', '12GB', '256GB', 'Silky Black', 57000.0, 64999.0, 5, 12, 'in_stock', 2, '2026-09-07 14:01:11.175107', '/static/img/phones/oneplus_12.jpg', '6.82" 2K 120Hz ProXDR LTPO AMOLED, 4500 nits', 'Snapdragon 8 Gen 3 (4nm)', '50MP Sony LYT-808 + 64MP 3x Periscope + 48MP Ultra-wide', '5400 mAh, 100W SUPERVOOC, 50W AIRVOOC');
INSERT INTO `mobiles` (`id`, `brand`, `model`, `imei_1`, `imei_2`, `ram`, `storage`, `color`, `purchase_price`, `selling_price`, `stock_quantity`, `warranty_months`, `status`, `min_stock_alert`, `created_at`, `image_url`, `display`, `processor`, `camera`, `battery`) VALUES (6, 'OnePlus', 'Nord CE 4 5G', '359128374829601', '359128374829602', '8GB', '128GB', 'Dark Chrome', 21000.0, 24999.0, 8, 12, 'in_stock', 2, '2026-09-07 14:01:11.175107', '/static/img/phones/oneplus_nord_ce_4.jpg', '6.7" Fluid AMOLED, 120Hz, HDR10+', 'Snapdragon 7 Gen 3 (4nm)', '50MP Sony LYT-600 OIS + 8MP Ultra-wide', '5500 mAh, 100W SuperVOOC Fast Charge');
INSERT INTO `mobiles` (`id`, `brand`, `model`, `imei_1`, `imei_2`, `ram`, `storage`, `color`, `purchase_price`, `selling_price`, `stock_quantity`, `warranty_months`, `status`, `min_stock_alert`, `created_at`, `image_url`, `display`, `processor`, `camera`, `battery`) VALUES (7, 'Xiaomi', 'Redmi Note 13 Pro+', '359128374829701', '359128374829702', '12GB', '256GB', 'Fusion Purple', 27500.0, 31999.0, 4, 12, 'in_stock', 2, '2026-09-07 14:01:11.175107', '/static/img/phones/redmi_note_13.jpg', '6.67" 1.5K Curved AMOLED, 120Hz, Dolby Vision', 'MediaTek Dimensity 7200 Ultra (4nm)', '200MP Samsung ISOCELL HP3 OIS + 8MP + 2MP', '5000 mAh, 120W HyperCharge');
INSERT INTO `mobiles` (`id`, `brand`, `model`, `imei_1`, `imei_2`, `ram`, `storage`, `color`, `purchase_price`, `selling_price`, `stock_quantity`, `warranty_months`, `status`, `min_stock_alert`, `created_at`, `image_url`, `display`, `processor`, `camera`, `battery`) VALUES (8, 'Realme', '12 Pro+ 5G', '359128374829801', '359128374829802', '8GB', '256GB', 'Submarine Blue', 25000.0, 29999.0, 2, 12, 'in_stock', 2, '2026-09-07 14:01:11.175107', '/static/img/phones/realme_12_pro.jpg', '6.7" 120Hz Curved Vision AMOLED', 'Snapdragon 7s Gen 2 (4nm)', '64MP Periscope OIS + 50MP Sony IMX890 + 8MP', '5000 mAh, 67W SUPERVOOC Charge');
INSERT INTO `mobiles` (`id`, `brand`, `model`, `imei_1`, `imei_2`, `ram`, `storage`, `color`, `purchase_price`, `selling_price`, `stock_quantity`, `warranty_months`, `status`, `min_stock_alert`, `created_at`, `image_url`, `display`, `processor`, `camera`, `battery`) VALUES (9, 'Vivo', 'V30 Pro 5G', '359128374829901', '359128374829902', '8GB', '256GB', 'Andaman Blue', 36000.0, 41999.0, 3, 12, 'in_stock', 2, '2026-09-07 14:01:11.175107', '/static/img/phones/vivo_v30_pro.jpg', '6.78" 1.5K 3D Curved AMOLED 120Hz, 2800 nits', 'MediaTek Dimensity 8200 (4nm)', '50MP ZEISS Main + 50MP ZEISS Telephoto + 50MP Ultra-wide', '5000 mAh, 80W FlashCharge');
INSERT INTO `mobiles` (`id`, `brand`, `model`, `imei_1`, `imei_2`, `ram`, `storage`, `color`, `purchase_price`, `selling_price`, `stock_quantity`, `warranty_months`, `status`, `min_stock_alert`, `created_at`, `image_url`, `display`, `processor`, `camera`, `battery`) VALUES (10, 'Motorola', 'Edge 50 Pro', '359128374830001', '359128374830002', '12GB', '256GB', 'Luxe Lavender', 27000.0, 31999.0, 5, 12, 'in_stock', 2, '2026-09-07 14:01:11.175107', '/static/img/phones/motorola_edge_50_pro.jpg', '6.7" 1.5K True Color pOLED 144Hz, Pantone Validated', 'Snapdragon 7 Gen 3 (4nm)', '50MP AI OIS + 10MP 3x Telephoto + 13MP Macro/Ultra-wide', '4500 mAh, 125W TurboPower, 50W Wireless');

-- Dumping data for table `suppliers`
INSERT INTO `suppliers` (`id`, `name`, `company`, `phone`, `email`, `address`, `balance_due`, `created_at`) VALUES (1, 'Sunil Singhania', 'Apex Tele-Distributors Pvt Ltd', '9811223344', 'orders@apexdist.in', 'G-12, Electronics Trade Complex, Okhla, New Delhi', 45000.0, '2026-09-07 14:01:11.169107');
INSERT INTO `suppliers` (`id`, `name`, `company`, `phone`, `email`, `address`, `balance_due`, `created_at`) VALUES (2, 'Karan Malhotra', 'TechSource Peripherals Hub', '9822334455', 'sales@techsourcehub.com', 'Shop 18, Lamington Road, Mumbai', 12500.0, '2026-09-07 14:01:11.169107');

-- Dumping data for table `users`
INSERT INTO `users` (`id`, `username`, `password_hash`, `full_name`, `role`, `email`, `phone`, `is_active`, `created_at`) VALUES (1, 'admin', 'scrypt:32768:8:1$rbYwCF4JQlX8SN70$e5755d091f7673ced727d8dfc30b82e9044e9af4590e06ad10ea82e187263f4314e97cb73a038029ac79bdcadbc48490ced6650e01ce5e693d38a11dc75f669c', 'Arjun Mehta (Admin)', 'admin', 'admin@mobix.com', '9876500001', 1, '2026-09-07 14:01:11.151181');
INSERT INTO `users` (`id`, `username`, `password_hash`, `full_name`, `role`, `email`, `phone`, `is_active`, `created_at`) VALUES (2, 'cashier', 'scrypt:32768:8:1$JDloI5IOVPMBGmzs$ed58a0dc24eb9942cec1086293e3b552785fc989861f9a7ff110cc38be1c1a0ec980e494660644f9524b8c5d550ee55ff7fcb7dd5c4ac5c3060380fea24b5962', 'Pooja Nair (Cashier)', 'cashier', 'cashier@mobix.com', '9876500002', 1, '2026-09-07 14:01:11.151181');
INSERT INTO `users` (`id`, `username`, `password_hash`, `full_name`, `role`, `email`, `phone`, `is_active`, `created_at`) VALUES (3, 'tech', 'scrypt:32768:8:1$0ebHDrHyOFNs5Y5N$0c5fe88615aa8bb7fbbf34de48337160280b1d09a96bafb8e15f5bea508d4b486f90e99773f44f44457d2253e076d7fe79a447bf0d61f933ccc167e5221d2e4d', 'Rohan Joshi (Technician)', 'technician', 'tech@mobix.com', '9876500003', 1, '2026-09-07 14:01:11.151181');

-- Dumping data for table `invoices`
INSERT INTO `invoices` (`id`, `invoice_number`, `customer_id`, `user_id`, `subtotal`, `tax_rate`, `tax_amount`, `discount_amount`, `exchange_discount`, `final_total`, `payment_mode`, `payment_status`, `notes`, `created_at`) VALUES (1, 'INV-20260901-A101', 1, 2, 62498.0, 18.0, 11249.64, 1500.0, 0.0, 72247.64, 'UPI', 'Paid', NULL, '2026-09-01 14:01:11.186151');
INSERT INTO `invoices` (`id`, `invoice_number`, `customer_id`, `user_id`, `subtotal`, `tax_rate`, `tax_amount`, `discount_amount`, `exchange_discount`, `final_total`, `payment_mode`, `payment_status`, `notes`, `created_at`) VALUES (2, 'INV-20260805-E902', 2, 2, 30000.0, 0.0, 0.0, 0.0, 0.0, 30000.0, 'EMI', 'Partial', NULL, '2026-07-29 14:01:11.190153');
INSERT INTO `invoices` (`id`, `invoice_number`, `customer_id`, `user_id`, `subtotal`, `tax_rate`, `tax_amount`, `discount_amount`, `exchange_discount`, `final_total`, `payment_mode`, `payment_status`, `notes`, `created_at`) VALUES (3, 'INV-20260907-FEF3', 6, 2, 31500.0, 18.0, 5670.0, 500.0, 0.0, 36670.0, 'Cash', 'Paid', '', '2026-09-07 14:01:12.569031');
INSERT INTO `invoices` (`id`, `invoice_number`, `customer_id`, `user_id`, `subtotal`, `tax_rate`, `tax_amount`, `discount_amount`, `exchange_discount`, `final_total`, `payment_mode`, `payment_status`, `notes`, `created_at`) VALUES (4, 'INV-20260907-9905', 6, 2, 31500.0, 18.0, 5670.0, 500.0, 0.0, 36670.0, 'Cash', 'Paid', '', '2026-09-07 14:15:01.991015');
INSERT INTO `invoices` (`id`, `invoice_number`, `customer_id`, `user_id`, `subtotal`, `tax_rate`, `tax_amount`, `discount_amount`, `exchange_discount`, `final_total`, `payment_mode`, `payment_status`, `notes`, `created_at`) VALUES (5, 'INV-20260907-43AC', 6, 2, 31500.0, 18.0, 5670.0, 500.0, 0.0, 36670.0, 'Cash', 'Paid', '', '2026-09-07 14:53:21.507413');

-- Dumping data for table `repair_tickets`
INSERT INTO `repair_tickets` (`id`, `ticket_no`, `customer_id`, `technician_id`, `brand`, `model`, `imei`, `problem_description`, `estimated_cost`, `final_cost`, `advance_paid`, `status`, `parts_used`, `technician_notes`, `warranty_days`, `delivery_date`, `created_at`, `updated_at`) VALUES (1, 'REP-260902-7A12', 3, 3, 'OnePlus', 'OnePlus 11R', '359918273645019', 'Outer display cracked after accidental drop, touch responding irregularly.', 6500.0, 6500.0, 2000.0, 'Repairing', 'Original OnePlus Fluid AMOLED Display Panel', 'Screen disassembled, UV glue cured, undergoing touch calibration.', 60, NULL, '2026-09-07 14:01:11.223459', '2026-09-07 14:01:11.223459');
INSERT INTO `repair_tickets` (`id`, `ticket_no`, `customer_id`, `technician_id`, `brand`, `model`, `imei`, `problem_description`, `estimated_cost`, `final_cost`, `advance_paid`, `status`, `parts_used`, `technician_notes`, `warranty_days`, `delivery_date`, `created_at`, `updated_at`) VALUES (2, 'REP-260905-9B34', 4, 3, 'Apple', 'iPhone 12', '359918273645882', 'Battery health degraded to 72%, device throttles and shuts down at 20%.', 3200.0, 3200.0, 1000.0, 'Ready', 'OEM High-Capacity 2815mAh Battery + Waterproof Gasket', 'Replaced battery. Health shows 100%. Device passed 24hr discharge test. Ready for pickup.', 90, NULL, '2026-09-07 14:01:11.223459', '2026-09-07 14:01:11.223459');
INSERT INTO `repair_tickets` (`id`, `ticket_no`, `customer_id`, `technician_id`, `brand`, `model`, `imei`, `problem_description`, `estimated_cost`, `final_cost`, `advance_paid`, `status`, `parts_used`, `technician_notes`, `warranty_days`, `delivery_date`, `created_at`, `updated_at`) VALUES (3, 'REP-260906-3C56', 5, 3, 'Samsung', 'Galaxy S21 FE', '359918273645112', 'Type-C port loose, fast charging not engaging.', 1200.0, 0.0, 0.0, 'Diagnosing', NULL, NULL, 30, NULL, '2026-09-07 14:01:11.225460', '2026-09-07 14:01:11.225460');

-- Dumping data for table `supplier_purchases`
INSERT INTO `supplier_purchases` (`id`, `supplier_id`, `invoice_no`, `total_amount`, `paid_amount`, `status`, `notes`, `purchase_date`) VALUES (1, 1, 'INV-APEX-8891', 150000.0, 105000.0, 'Partial', '5x iPhone 15 units, 3x Galaxy S24', '2026-08-26');
INSERT INTO `supplier_purchases` (`id`, `supplier_id`, `invoice_no`, `total_amount`, `paid_amount`, `status`, `notes`, `purchase_date`) VALUES (2, 2, 'INV-TECH-4402', 35000.0, 22500.0, 'Partial', '50x 65W Chargers, 30x Tempered Glass', '2026-09-02');

-- Dumping data for table `emi_accounts`
INSERT INTO `emi_accounts` (`id`, `invoice_id`, `customer_id`, `total_amount`, `down_payment`, `principal_remaining`, `emi_amount`, `tenure_months`, `fine_per_cycle`, `start_date`, `status`, `notes`) VALUES (1, 2, 2, 30000.0, 6000.0, 24000.0, 4000.0, 6, 200.0, '2026-07-29', 'Overdue', 'Mobile EMI: ₹4,000 x 6 months');
INSERT INTO `emi_accounts` (`id`, `invoice_id`, `customer_id`, `total_amount`, `down_payment`, `principal_remaining`, `emi_amount`, `tenure_months`, `fine_per_cycle`, `start_date`, `status`, `notes`) VALUES (2, 1, 1, 30000.0, 6000.0, 24000.0, 4000.0, 6, 200.0, '2026-09-07', 'Overdue', NULL);
INSERT INTO `emi_accounts` (`id`, `invoice_id`, `customer_id`, `total_amount`, `down_payment`, `principal_remaining`, `emi_amount`, `tenure_months`, `fine_per_cycle`, `start_date`, `status`, `notes`) VALUES (3, 1, 1, 30000.0, 6000.0, 24000.0, 4000.0, 6, 200.0, '2026-09-07', 'Overdue', NULL);
INSERT INTO `emi_accounts` (`id`, `invoice_id`, `customer_id`, `total_amount`, `down_payment`, `principal_remaining`, `emi_amount`, `tenure_months`, `fine_per_cycle`, `start_date`, `status`, `notes`) VALUES (4, 1, 1, 30000.0, 6000.0, 24000.0, 4000.0, 6, 200.0, '2026-09-07', 'Overdue', NULL);

-- Dumping data for table `exchange_records`
INSERT INTO `exchange_records` (`id`, `customer_id`, `invoice_id`, `brand`, `model`, `imei`, `original_price`, `age_months`, `storage`, `battery_health`, `condition_screen`, `condition_body`, `camera_working`, `face_or_touch_id`, `ai_estimated_value`, `offered_value`, `status`, `created_at`) VALUES (1, 1, 1, 'OnePlus', 'OnePlus 9 5G', '351182736450091', 49999.0, 24, '128GB', 82, 'Minor Scratches', 'Good', 1, 1, 12400.0, 11000.0, 'Evaluated', '2026-09-07 14:01:11.219464');

-- Dumping data for table `invoice_items`
INSERT INTO `invoice_items` (`id`, `invoice_id`, `item_type`, `mobile_id`, `accessory_id`, `item_name`, `imei`, `quantity`, `unit_price`, `total_price`) VALUES (1, 1, 'mobile', 2, NULL, 'Apple iPhone 14 (6GB/128GB)', '359128374829201', 1, 59999.0, 59999.0);
INSERT INTO `invoice_items` (`id`, `invoice_id`, `item_type`, `mobile_id`, `accessory_id`, `item_name`, `imei`, `quantity`, `unit_price`, `total_price`) VALUES (2, 1, 'accessory', NULL, 1, '65W GaN Dual USB-C Fast Charger', NULL, 1, 2499.0, 2499.0);
INSERT INTO `invoice_items` (`id`, `invoice_id`, `item_type`, `mobile_id`, `accessory_id`, `item_name`, `imei`, `quantity`, `unit_price`, `total_price`) VALUES (3, 2, 'mobile', 8, NULL, 'Realme 12 Pro+ 5G (8GB/256GB)', '359128374829801', 1, 30000.0, 30000.0);
INSERT INTO `invoice_items` (`id`, `invoice_id`, `item_type`, `mobile_id`, `accessory_id`, `item_name`, `imei`, `quantity`, `unit_price`, `total_price`) VALUES (4, 3, 'mobile', 1, NULL, 'Apple iPhone 15 Pro Max (8GB/256GB)', '359128374829101', 1, 30000.0, 30000.0);
INSERT INTO `invoice_items` (`id`, `invoice_id`, `item_type`, `mobile_id`, `accessory_id`, `item_name`, `imei`, `quantity`, `unit_price`, `total_price`) VALUES (5, 3, 'accessory', NULL, 1, '65W GaN Dual USB-C Fast Charger', NULL, 1, 1500.0, 1500.0);
INSERT INTO `invoice_items` (`id`, `invoice_id`, `item_type`, `mobile_id`, `accessory_id`, `item_name`, `imei`, `quantity`, `unit_price`, `total_price`) VALUES (6, 4, 'mobile', 1, NULL, 'Apple iPhone 15 Pro Max (8GB/256GB)', '359128374829101', 1, 30000.0, 30000.0);
INSERT INTO `invoice_items` (`id`, `invoice_id`, `item_type`, `mobile_id`, `accessory_id`, `item_name`, `imei`, `quantity`, `unit_price`, `total_price`) VALUES (7, 4, 'accessory', NULL, 1, '65W GaN Dual USB-C Fast Charger', NULL, 1, 1500.0, 1500.0);
INSERT INTO `invoice_items` (`id`, `invoice_id`, `item_type`, `mobile_id`, `accessory_id`, `item_name`, `imei`, `quantity`, `unit_price`, `total_price`) VALUES (8, 5, 'mobile', 1, NULL, 'Apple iPhone 15 Pro Max (8GB/256GB)', '359128374829101', 1, 30000.0, 30000.0);
INSERT INTO `invoice_items` (`id`, `invoice_id`, `item_type`, `mobile_id`, `accessory_id`, `item_name`, `imei`, `quantity`, `unit_price`, `total_price`) VALUES (9, 5, 'accessory', NULL, 1, '65W GaN Dual USB-C Fast Charger', NULL, 1, 1500.0, 1500.0);

-- Dumping data for table `emi_installments`
INSERT INTO `emi_installments` (`id`, `emi_account_id`, `installment_no`, `due_date`, `amount`, `fine_amount`, `paid_amount`, `payment_date`, `payment_mode`, `status`) VALUES (1, 1, 1, '2026-08-28', 4000.0, 0.0, 4000.0, '2026-08-26', 'UPI', 'paid');
INSERT INTO `emi_installments` (`id`, `emi_account_id`, `installment_no`, `due_date`, `amount`, `fine_amount`, `paid_amount`, `payment_date`, `payment_mode`, `status`) VALUES (2, 1, 2, '2026-09-05', 4000.0, 200.0, 0.0, NULL, NULL, 'overdue');
INSERT INTO `emi_installments` (`id`, `emi_account_id`, `installment_no`, `due_date`, `amount`, `fine_amount`, `paid_amount`, `payment_date`, `payment_mode`, `status`) VALUES (3, 1, 3, '2026-10-05', 4000.0, 0.0, 0.0, NULL, NULL, 'pending');
INSERT INTO `emi_installments` (`id`, `emi_account_id`, `installment_no`, `due_date`, `amount`, `fine_amount`, `paid_amount`, `payment_date`, `payment_mode`, `status`) VALUES (4, 1, 4, '2026-11-02', 4000.0, 0.0, 0.0, NULL, NULL, 'pending');
INSERT INTO `emi_installments` (`id`, `emi_account_id`, `installment_no`, `due_date`, `amount`, `fine_amount`, `paid_amount`, `payment_date`, `payment_mode`, `status`) VALUES (5, 1, 5, '2026-11-30', 4000.0, 0.0, 0.0, NULL, NULL, 'pending');
INSERT INTO `emi_installments` (`id`, `emi_account_id`, `installment_no`, `due_date`, `amount`, `fine_amount`, `paid_amount`, `payment_date`, `payment_mode`, `status`) VALUES (6, 1, 6, '2026-12-28', 4000.0, 0.0, 0.0, NULL, NULL, 'pending');
INSERT INTO `emi_installments` (`id`, `emi_account_id`, `installment_no`, `due_date`, `amount`, `fine_amount`, `paid_amount`, `payment_date`, `payment_mode`, `status`) VALUES (7, 2, 1, '2026-09-02', 4000.0, 200.0, 0.0, NULL, NULL, 'overdue');
INSERT INTO `emi_installments` (`id`, `emi_account_id`, `installment_no`, `due_date`, `amount`, `fine_amount`, `paid_amount`, `payment_date`, `payment_mode`, `status`) VALUES (8, 2, 2, '2026-11-07', 4000.0, 0.0, 0.0, NULL, NULL, 'pending');
INSERT INTO `emi_installments` (`id`, `emi_account_id`, `installment_no`, `due_date`, `amount`, `fine_amount`, `paid_amount`, `payment_date`, `payment_mode`, `status`) VALUES (9, 2, 3, '2026-12-07', 4000.0, 0.0, 0.0, NULL, NULL, 'pending');
INSERT INTO `emi_installments` (`id`, `emi_account_id`, `installment_no`, `due_date`, `amount`, `fine_amount`, `paid_amount`, `payment_date`, `payment_mode`, `status`) VALUES (10, 2, 4, '2027-01-07', 4000.0, 0.0, 0.0, NULL, NULL, 'pending');
INSERT INTO `emi_installments` (`id`, `emi_account_id`, `installment_no`, `due_date`, `amount`, `fine_amount`, `paid_amount`, `payment_date`, `payment_mode`, `status`) VALUES (11, 2, 5, '2027-02-07', 4000.0, 0.0, 0.0, NULL, NULL, 'pending');
INSERT INTO `emi_installments` (`id`, `emi_account_id`, `installment_no`, `due_date`, `amount`, `fine_amount`, `paid_amount`, `payment_date`, `payment_mode`, `status`) VALUES (12, 2, 6, '2027-03-07', 4000.0, 0.0, 0.0, NULL, NULL, 'pending');
INSERT INTO `emi_installments` (`id`, `emi_account_id`, `installment_no`, `due_date`, `amount`, `fine_amount`, `paid_amount`, `payment_date`, `payment_mode`, `status`) VALUES (13, 3, 1, '2026-09-02', 4000.0, 200.0, 0.0, NULL, NULL, 'overdue');
INSERT INTO `emi_installments` (`id`, `emi_account_id`, `installment_no`, `due_date`, `amount`, `fine_amount`, `paid_amount`, `payment_date`, `payment_mode`, `status`) VALUES (14, 3, 2, '2026-11-07', 4000.0, 0.0, 0.0, NULL, NULL, 'pending');
INSERT INTO `emi_installments` (`id`, `emi_account_id`, `installment_no`, `due_date`, `amount`, `fine_amount`, `paid_amount`, `payment_date`, `payment_mode`, `status`) VALUES (15, 3, 3, '2026-12-07', 4000.0, 0.0, 0.0, NULL, NULL, 'pending');
INSERT INTO `emi_installments` (`id`, `emi_account_id`, `installment_no`, `due_date`, `amount`, `fine_amount`, `paid_amount`, `payment_date`, `payment_mode`, `status`) VALUES (16, 3, 4, '2027-01-07', 4000.0, 0.0, 0.0, NULL, NULL, 'pending');
INSERT INTO `emi_installments` (`id`, `emi_account_id`, `installment_no`, `due_date`, `amount`, `fine_amount`, `paid_amount`, `payment_date`, `payment_mode`, `status`) VALUES (17, 3, 5, '2027-02-07', 4000.0, 0.0, 0.0, NULL, NULL, 'pending');
INSERT INTO `emi_installments` (`id`, `emi_account_id`, `installment_no`, `due_date`, `amount`, `fine_amount`, `paid_amount`, `payment_date`, `payment_mode`, `status`) VALUES (18, 3, 6, '2027-03-07', 4000.0, 0.0, 0.0, NULL, NULL, 'pending');
INSERT INTO `emi_installments` (`id`, `emi_account_id`, `installment_no`, `due_date`, `amount`, `fine_amount`, `paid_amount`, `payment_date`, `payment_mode`, `status`) VALUES (19, 4, 1, '2026-09-02', 4000.0, 200.0, 0.0, NULL, NULL, 'overdue');
INSERT INTO `emi_installments` (`id`, `emi_account_id`, `installment_no`, `due_date`, `amount`, `fine_amount`, `paid_amount`, `payment_date`, `payment_mode`, `status`) VALUES (20, 4, 2, '2026-11-07', 4000.0, 0.0, 0.0, NULL, NULL, 'pending');
INSERT INTO `emi_installments` (`id`, `emi_account_id`, `installment_no`, `due_date`, `amount`, `fine_amount`, `paid_amount`, `payment_date`, `payment_mode`, `status`) VALUES (21, 4, 3, '2026-12-07', 4000.0, 0.0, 0.0, NULL, NULL, 'pending');
INSERT INTO `emi_installments` (`id`, `emi_account_id`, `installment_no`, `due_date`, `amount`, `fine_amount`, `paid_amount`, `payment_date`, `payment_mode`, `status`) VALUES (22, 4, 4, '2027-01-07', 4000.0, 0.0, 0.0, NULL, NULL, 'pending');
INSERT INTO `emi_installments` (`id`, `emi_account_id`, `installment_no`, `due_date`, `amount`, `fine_amount`, `paid_amount`, `payment_date`, `payment_mode`, `status`) VALUES (23, 4, 5, '2027-02-07', 4000.0, 0.0, 0.0, NULL, NULL, 'pending');
INSERT INTO `emi_installments` (`id`, `emi_account_id`, `installment_no`, `due_date`, `amount`, `fine_amount`, `paid_amount`, `payment_date`, `payment_mode`, `status`) VALUES (24, 4, 6, '2027-03-07', 4000.0, 0.0, 0.0, NULL, NULL, 'pending');

SET FOREIGN_KEY_CHECKS = 1;
