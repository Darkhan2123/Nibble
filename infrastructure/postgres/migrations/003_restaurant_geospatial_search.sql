-- Enable PostGIS extension if not already enabled
CREATE EXTENSION IF NOT EXISTS postgis;

-- Ensure the address table has a location column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'user_service'
        AND table_name = 'addresses'
        AND column_name = 'location'
    ) THEN
        -- Add location column to addresses
        ALTER TABLE user_service.addresses 
        ADD COLUMN location GEOMETRY(Point, 4326);
        
        -- Update existing addresses with calculated locations from lat/long
        UPDATE user_service.addresses
        SET location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL;
        
        -- Create a trigger to keep location in sync with lat/long
        CREATE OR REPLACE FUNCTION user_service.update_address_location()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL) THEN
                NEW.location = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        CREATE TRIGGER trigger_update_address_location
        BEFORE INSERT OR UPDATE OF latitude, longitude ON user_service.addresses
        FOR EACH ROW
        EXECUTE FUNCTION user_service.update_address_location();
    END IF;
END $$;

-- Create spatial index on address location
CREATE INDEX IF NOT EXISTS idx_addresses_location 
ON user_service.addresses USING GIST (location);

-- Create index on restaurant address_id for faster joins
CREATE INDEX IF NOT EXISTS idx_restaurant_profiles_address_id 
ON restaurant_service.restaurant_profiles (address_id);

-- Create index on restaurant cuisine_type for faster search
CREATE INDEX IF NOT EXISTS idx_restaurant_profiles_cuisine_type 
ON restaurant_service.restaurant_profiles USING GIN (cuisine_type);

-- Create index on restaurant is_active
CREATE INDEX IF NOT EXISTS idx_restaurant_profiles_is_active 
ON restaurant_service.restaurant_profiles (is_active);

-- Add some useful functions for calculating distance
CREATE OR REPLACE FUNCTION restaurant_service.calculate_distance(
    lat1 DOUBLE PRECISION, 
    lon1 DOUBLE PRECISION,
    lat2 DOUBLE PRECISION, 
    lon2 DOUBLE PRECISION
) RETURNS DOUBLE PRECISION AS $$
DECLARE
    -- Earth radius in kilometers
    R DOUBLE PRECISION := 6371;
    dLat DOUBLE PRECISION;
    dLon DOUBLE PRECISION;
    a DOUBLE PRECISION;
    c DOUBLE PRECISION;
    d DOUBLE PRECISION;
BEGIN
    -- Convert to radians
    lat1 := radians(lat1);
    lon1 := radians(lon1);
    lat2 := radians(lat2);
    lon2 := radians(lon2);
    
    -- Haversine formula
    dLat := lat2 - lat1;
    dLon := lon2 - lon1;
    a := sin(dLat/2) * sin(dLat/2) + cos(lat1) * cos(lat2) * sin(dLon/2) * sin(dLon/2);
    c := 2 * asin(sqrt(a));
    d := R * c;
    
    RETURN d;
END;
$$ LANGUAGE plpgsql;

-- Function to find restaurants within a radius
CREATE OR REPLACE FUNCTION restaurant_service.find_restaurants_within_radius(
    user_lat DOUBLE PRECISION,
    user_lon DOUBLE PRECISION,
    radius_meters DOUBLE PRECISION
) RETURNS TABLE (
    restaurant_id UUID,
    distance_meters DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        r.id::UUID AS restaurant_id,
        ST_Distance(
            a.location::geography,
            ST_SetSRID(ST_MakePoint(user_lon, user_lat), 4326)::geography
        ) AS distance_meters
    FROM 
        restaurant_service.restaurant_profiles r
    JOIN 
        user_service.addresses a ON r.address_id = a.id
    WHERE 
        r.is_active = TRUE
    AND
        ST_DWithin(
            a.location::geography,
            ST_SetSRID(ST_MakePoint(user_lon, user_lat), 4326)::geography,
            radius_meters
        )
    ORDER BY 
        distance_meters;
END;
$$ LANGUAGE plpgsql;