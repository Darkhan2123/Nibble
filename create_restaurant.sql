INSERT INTO restaurant_service.restaurant_profiles (
    id, user_id, name, description, cuisine_type, price_range,
    phone_number, email, website_url, address_id, logo_url, banner_url,
    delivery_fee, minimum_order_amount, commission_rate
) VALUES (
    '12345678-abcd-1234-efgh-123456789012',
    'dbfbe426-d17f-47e8-b519-f5a86b3a8dd3',
    'Test Restaurant',
    'A restaurant for testing',
    ARRAY['Test', 'Food'],
    2,
    '+1234567890',
    'test@example.com',
    NULL,
    '12345678-abcd-1234-efgh-123456789012',
    NULL,
    NULL,
    5.00,
    10.00,
    15.00
);
