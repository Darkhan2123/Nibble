-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable PostGIS for spatial features
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create schema for each service
CREATE SCHEMA IF NOT EXISTS user_service;
CREATE SCHEMA IF NOT EXISTS restaurant_service;
CREATE SCHEMA IF NOT EXISTS driver_service;
CREATE SCHEMA IF NOT EXISTS order_service;
CREATE SCHEMA IF NOT EXISTS admin_service;

-- Users Table
CREATE TABLE IF NOT EXISTS user_service.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE,
    profile_picture_url VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User Roles Table
CREATE TABLE IF NOT EXISTS user_service.roles (
    id SMALLINT PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255)
);

-- Insert default roles
INSERT INTO user_service.roles (id, name, description) VALUES
    (1, 'customer', 'Regular customer who orders food'),
    (2, 'restaurant', 'Restaurant owner or manager'),
    (3, 'driver', 'Delivery driver'),
    (4, 'admin', 'System administrator')
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS user_service.user_roles (
    user_id UUID REFERENCES user_service.users(id) ON DELETE CASCADE,
    role_id SMALLINT REFERENCES user_service.roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

-- Addresses Table
CREATE TABLE IF NOT EXISTS user_service.addresses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES user_service.users(id) ON DELETE CASCADE,
    address_line1 VARCHAR(255) NOT NULL,
    address_line2 VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    postal_code VARCHAR(20) NOT NULL,
    country VARCHAR(100) NOT NULL DEFAULT 'Казахстан',
    location GEOGRAPHY(POINT) NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    address_type VARCHAR(50) NOT NULL, -- 'home', 'work', 'other'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Spatial index on location for geographic queries
CREATE INDEX IF NOT EXISTS addresses_location_idx ON user_service.addresses USING GIST(location);

-- Customer Profiles Table
CREATE TABLE IF NOT EXISTS user_service.customer_profiles (
    user_id UUID PRIMARY KEY REFERENCES user_service.users(id) ON DELETE CASCADE,
    dietary_preferences JSONB,
    favorite_cuisines JSONB,
    average_rating DECIMAL(3, 2),
    stripe_customer_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Restaurant Profiles Table
CREATE TABLE IF NOT EXISTS restaurant_service.restaurant_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    logo_url VARCHAR(255),
    banner_url VARCHAR(255),
    cuisine_type VARCHAR(100)[],
    price_range SMALLINT NOT NULL, -- 1: $, 2: $$, 3: $$$, 4: $$$$
    phone_number VARCHAR(20) NOT NULL,
    email VARCHAR(255) NOT NULL,
    website_url VARCHAR(255),
    address_id UUID,
    is_featured BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    average_rating DECIMAL(3, 2) DEFAULT 0,
    total_ratings INTEGER DEFAULT 0,
    estimated_delivery_time INTEGER, -- in minutes
    delivery_fee DECIMAL(10, 2),
    minimum_order_amount DECIMAL(10, 2) DEFAULT 0,
    commission_rate DECIMAL(5, 2) DEFAULT 15.00, -- percentage
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for location-based queries
CREATE INDEX IF NOT EXISTS restaurant_profile_user_id_idx ON restaurant_service.restaurant_profiles(user_id);

-- Restaurant Operating Hours Table
CREATE TABLE IF NOT EXISTS restaurant_service.restaurant_hours (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurant_id UUID REFERENCES restaurant_service.restaurant_profiles(id) ON DELETE CASCADE,
    day_of_week SMALLINT NOT NULL, -- 0: Sunday, 1: Monday, ..., 6: Saturday
    open_time TIME NOT NULL,
    close_time TIME NOT NULL,
    is_closed BOOLEAN DEFAULT FALSE,
    CONSTRAINT unique_restaurant_day UNIQUE (restaurant_id, day_of_week)
);

-- Menu Categories Table
CREATE TABLE IF NOT EXISTS restaurant_service.menu_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurant_id UUID REFERENCES restaurant_service.restaurant_profiles(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_category_name_per_restaurant UNIQUE (restaurant_id, name)
);

-- Menu Items Table
CREATE TABLE IF NOT EXISTS restaurant_service.menu_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    restaurant_id UUID REFERENCES restaurant_service.restaurant_profiles(id) ON DELETE CASCADE,
    category_id UUID REFERENCES restaurant_service.menu_categories(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    image_url VARCHAR(255),
    is_vegetarian BOOLEAN DEFAULT FALSE,
    is_vegan BOOLEAN DEFAULT FALSE,
    is_gluten_free BOOLEAN DEFAULT FALSE,
    spice_level SMALLINT, -- 0: Not spicy, 1: Mild, 2: Medium, 3: Hot, 4: Extra Hot
    preparation_time INTEGER, -- in minutes
    calories INTEGER,
    allergens VARCHAR(50)[],
    is_available BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Menu Item Customizations Table
CREATE TABLE IF NOT EXISTS restaurant_service.customization_groups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    menu_item_id UUID REFERENCES restaurant_service.menu_items(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_required BOOLEAN DEFAULT FALSE,
    min_selections INTEGER DEFAULT 0,
    max_selections INTEGER,
    display_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS restaurant_service.customization_options (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_id UUID REFERENCES restaurant_service.customization_groups(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price_adjustment DECIMAL(10, 2) DEFAULT 0,
    is_default BOOLEAN DEFAULT FALSE,
    display_order INTEGER DEFAULT 0
);

-- Driver Profiles Table
CREATE TABLE IF NOT EXISTS driver_service.driver_profiles (
    user_id UUID PRIMARY KEY,
    vehicle_type VARCHAR(50) NOT NULL, -- 'car', 'motorcycle', 'bicycle', 'scooter'
    vehicle_make VARCHAR(100),
    vehicle_model VARCHAR(100),
    vehicle_year INTEGER,
    license_plate VARCHAR(20),
    driver_license_number VARCHAR(50),
    driver_license_expiry DATE,
    insurance_number VARCHAR(100),
    insurance_expiry DATE,
    background_check_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
    is_available BOOLEAN DEFAULT FALSE,
    current_location GEOGRAPHY(POINT),
    average_rating DECIMAL(3, 2) DEFAULT 0,
    total_deliveries INTEGER DEFAULT 0,
    banking_info JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Spatial index on current_location for driver matching
CREATE INDEX IF NOT EXISTS driver_location_idx ON driver_service.driver_profiles USING GIST(current_location);

-- Orders Table
CREATE TABLE IF NOT EXISTS order_service.orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL,
    restaurant_id UUID NOT NULL,
    driver_id UUID,
    order_number VARCHAR(20) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL, -- 'placed', 'confirmed', 'preparing', 'ready_for_pickup', 'out_for_delivery', 'delivered', 'cancelled'
    subtotal DECIMAL(10, 2) NOT NULL,
    tax DECIMAL(10, 2) NOT NULL,
    delivery_fee DECIMAL(10, 2) NOT NULL,
    tip DECIMAL(10, 2) DEFAULT 0,
    promo_discount DECIMAL(10, 2) DEFAULT 0,
    total_amount DECIMAL(10, 2) NOT NULL,
    payment_method VARCHAR(50),
    payment_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'completed', 'failed', 'refunded'
    stripe_payment_id VARCHAR(255),
    delivery_address_id UUID,
    special_instructions TEXT,
    estimated_delivery_time TIMESTAMP WITH TIME ZONE,
    actual_delivery_time TIMESTAMP WITH TIME ZONE,
    restaurant_preparation_time INTEGER, -- in minutes
    cancellation_reason TEXT,
    cancellation_time TIMESTAMP WITH TIME ZONE,
    cancelled_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for customer order history
CREATE INDEX IF NOT EXISTS orders_customer_id_idx ON order_service.orders(customer_id);
-- Index for restaurant orders
CREATE INDEX IF NOT EXISTS orders_restaurant_id_idx ON order_service.orders(restaurant_id);
-- Index for driver orders
CREATE INDEX IF NOT EXISTS orders_driver_id_idx ON order_service.orders(driver_id);

-- Order Items Table
CREATE TABLE IF NOT EXISTS order_service.order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID REFERENCES order_service.orders(id) ON DELETE CASCADE,
    menu_item_id UUID NOT NULL,
    menu_item_name VARCHAR(255) NOT NULL, -- Denormalized for historical records
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL,
    special_instructions TEXT,
    customizations JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Order Status History Table
CREATE TABLE IF NOT EXISTS order_service.order_status_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID REFERENCES order_service.orders(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,
    updated_by_user_id UUID,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Rating and Reviews Table
CREATE TABLE IF NOT EXISTS order_service.ratings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID REFERENCES order_service.orders(id) ON DELETE SET NULL,
    customer_id UUID NOT NULL,
    restaurant_id UUID NOT NULL,
    driver_id UUID,
    food_rating SMALLINT, -- 1-5
    delivery_rating SMALLINT, -- 1-5
    review_text TEXT,
    review_response TEXT,
    reviewed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    response_at TIMESTAMP WITH TIME ZONE,
    is_flagged BOOLEAN DEFAULT FALSE,
    flagged_reason VARCHAR(255)
);

-- Promotions Table
CREATE TABLE IF NOT EXISTS admin_service.promotions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    promo_code VARCHAR(50) UNIQUE,
    discount_type VARCHAR(20) NOT NULL, -- 'percentage', 'fixed_amount', 'free_item', 'free_delivery'
    discount_value DECIMAL(10, 2),
    min_order_amount DECIMAL(10, 2),
    max_discount_amount DECIMAL(10, 2),
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    usage_limit INTEGER,
    current_usage INTEGER DEFAULT 0,
    applies_to VARCHAR(50)[], -- 'all', 'restaurant_id', 'menu_item_id', 'cuisine_type', etc.
    applies_to_ids UUID[],
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User Promotions Table (for tracking usage)
CREATE TABLE IF NOT EXISTS admin_service.user_promotions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    promotion_id UUID REFERENCES admin_service.promotions(id) ON DELETE CASCADE,
    usage_count INTEGER DEFAULT 0,
    first_used_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE
);

-- Customer Favorites Table
CREATE TABLE IF NOT EXISTS user_service.customer_favorites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID REFERENCES user_service.users(id) ON DELETE CASCADE,
    restaurant_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_customer_restaurant_favorite UNIQUE (customer_id, restaurant_id)
);

-- Menu Item Favorites Table
CREATE TABLE IF NOT EXISTS user_service.menu_item_favorites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID REFERENCES user_service.users(id) ON DELETE CASCADE,
    menu_item_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_customer_menu_item_favorite UNIQUE (customer_id, menu_item_id)
);

-- Support Tickets Table
CREATE TABLE IF NOT EXISTS admin_service.support_tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    order_id UUID,
    subject VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'open', -- 'open', 'in_progress', 'resolved', 'closed'
    priority VARCHAR(50) DEFAULT 'medium', -- 'low', 'medium', 'high', 'urgent'
    assigned_to UUID,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Notification Settings Table
CREATE TABLE IF NOT EXISTS user_service.notification_settings (
    user_id UUID PRIMARY KEY,
    email_notifications BOOLEAN DEFAULT TRUE,
    sms_notifications BOOLEAN DEFAULT TRUE,
    push_notifications BOOLEAN DEFAULT TRUE,
    order_updates BOOLEAN DEFAULT TRUE,
    promotional_emails BOOLEAN DEFAULT TRUE,
    new_restaurant_alerts BOOLEAN DEFAULT FALSE,
    special_offers BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Notifications Table
CREATE TABLE IF NOT EXISTS user_service.notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'order_update', 'promotion', 'system', etc.
    reference_id UUID, -- Could be order_id, promotion_id, etc.
    reference_type VARCHAR(50), -- 'order', 'promotion', etc.
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);