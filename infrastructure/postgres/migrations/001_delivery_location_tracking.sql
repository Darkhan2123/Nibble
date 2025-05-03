-- Create delivery_location_history table
CREATE TABLE IF NOT EXISTS order_service.delivery_location_history (
    id SERIAL PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES order_service.orders(id),
    driver_id UUID NOT NULL REFERENCES user_service.users(id),
    location GEOMETRY(Point, 4326) NOT NULL, -- PostGIS geometry type for lat/long coordinates
    status VARCHAR(50) NOT NULL, -- Current delivery status at this location
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_driver FOREIGN KEY (driver_id) REFERENCES user_service.users(id),
    CONSTRAINT fk_order FOREIGN KEY (order_id) REFERENCES order_service.orders(id)
);

-- Add indices for faster querying
CREATE INDEX IF NOT EXISTS idx_delivery_location_history_order_id ON order_service.delivery_location_history(order_id);
CREATE INDEX IF NOT EXISTS idx_delivery_location_history_driver_id ON order_service.delivery_location_history(driver_id);
CREATE INDEX IF NOT EXISTS idx_delivery_location_history_recorded_at ON order_service.delivery_location_history(recorded_at);

-- Add current_location column to orders table if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'order_service' 
        AND table_name = 'orders' 
        AND column_name = 'current_location'
    ) THEN
        ALTER TABLE order_service.orders ADD COLUMN current_location GEOMETRY(Point, 4326);
    END IF;
END $$;

-- Create a function to record location history
CREATE OR REPLACE FUNCTION order_service.record_delivery_location()
RETURNS TRIGGER AS $$
BEGIN
    -- Only record if location has changed
    IF NEW.current_location IS NOT NULL AND 
       (OLD.current_location IS NULL OR 
        ST_AsText(NEW.current_location) != ST_AsText(OLD.current_location)) THEN
        
        INSERT INTO order_service.delivery_location_history
            (order_id, driver_id, location, status)
        VALUES
            (NEW.id, NEW.driver_id, NEW.current_location, NEW.status);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create a trigger to automatically record location history
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'trigger_record_delivery_location'
    ) THEN
        CREATE TRIGGER trigger_record_delivery_location
        AFTER UPDATE OF current_location, status ON order_service.orders
        FOR EACH ROW
        EXECUTE FUNCTION order_service.record_delivery_location();
    END IF;
END $$;