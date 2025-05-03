-- Create payment tables for Stripe integration

-- Table for payments
CREATE TABLE IF NOT EXISTS order_service.payments (
    id SERIAL PRIMARY KEY,
    payment_intent_id VARCHAR(255) NOT NULL UNIQUE,
    order_id UUID NOT NULL REFERENCES order_service.orders(id),
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'usd',
    status VARCHAR(50) NOT NULL DEFAULT 'created',
    payment_method VARCHAR(50),
    client_secret TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index on order_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_payments_order_id ON order_service.payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON order_service.payments(status);

-- Table for customer payment profiles
CREATE TABLE IF NOT EXISTS order_service.customer_payment_profiles (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE REFERENCES user_service.users(id),
    stripe_customer_id VARCHAR(255),
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index on stripe_customer_id
CREATE INDEX IF NOT EXISTS idx_customer_payment_profiles_stripe_customer_id ON order_service.customer_payment_profiles(stripe_customer_id);

-- Table for payment methods
CREATE TABLE IF NOT EXISTS order_service.payment_methods (
    id SERIAL PRIMARY KEY,
    payment_method_id VARCHAR(255) NOT NULL UNIQUE,
    user_id UUID NOT NULL REFERENCES user_service.users(id),
    stripe_customer_id VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    last4 VARCHAR(4),
    exp_month INTEGER,
    exp_year INTEGER,
    brand VARCHAR(50),
    is_default BOOLEAN DEFAULT FALSE,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_payment_methods_user_id ON order_service.payment_methods(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_methods_stripe_customer_id ON order_service.payment_methods(stripe_customer_id);

-- Add trigger to update timestamps
CREATE OR REPLACE FUNCTION order_service.update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = CURRENT_TIMESTAMP;
   RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'trigger_payments_update_timestamp'
    ) THEN
        CREATE TRIGGER trigger_payments_update_timestamp
        BEFORE UPDATE ON order_service.payments
        FOR EACH ROW EXECUTE FUNCTION order_service.update_timestamp();
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'trigger_customer_payment_profiles_update_timestamp'
    ) THEN
        CREATE TRIGGER trigger_customer_payment_profiles_update_timestamp
        BEFORE UPDATE ON order_service.customer_payment_profiles
        FOR EACH ROW EXECUTE FUNCTION order_service.update_timestamp();
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'trigger_payment_methods_update_timestamp'
    ) THEN
        CREATE TRIGGER trigger_payment_methods_update_timestamp
        BEFORE UPDATE ON order_service.payment_methods
        FOR EACH ROW EXECUTE FUNCTION order_service.update_timestamp();
    END IF;
END $$;