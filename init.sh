#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL

    -- ============================================
    -- СХЕМА
    -- ============================================
    CREATE SCHEMA IF NOT EXISTS taxi;

    -- ============================================
    -- APP-ПОЛЬЗОВАТЕЛЬ
    -- ============================================
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${APP_DB_USER}') THEN
            CREATE ROLE ${APP_DB_USER} WITH LOGIN PASSWORD '${APP_DB_PASSWORD}';
        END IF;
    END
    \$\$;

    -- ============================================
    -- ТАБЛИЦА ПОЕЗДОК (с новыми полями)
    -- ============================================
    CREATE TABLE taxi.trips (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(255) NOT NULL,
        start_lat DOUBLE PRECISION NOT NULL,
        start_lon DOUBLE PRECISION NOT NULL,
        end_lat DOUBLE PRECISION NOT NULL,
        end_lon DOUBLE PRECISION NOT NULL,
        start_address VARCHAR(500),
        end_address VARCHAR(500),
        route_geometry JSONB,
        distance_m INTEGER,
        duration_s INTEGER,
        status VARCHAR(50) DEFAULT 'created',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        -- Новые поля для карточки поездки
        tariff VARCHAR(20) DEFAULT 'economy',
        price NUMERIC(10, 2),
        payment_method VARCHAR(20) DEFAULT 'card',
        car_model VARCHAR(50),
        car_number VARCHAR(20),
        driver_name VARCHAR(100),
        driver_phone VARCHAR(20),
        rating INTEGER CHECK (rating BETWEEN 1 AND 5)
    );

    CREATE INDEX idx_trips_user_id ON taxi.trips(user_id);
    CREATE INDEX idx_trips_created_at ON taxi.trips(created_at DESC);
    CREATE INDEX idx_trips_status ON taxi.trips(status);

    -- ============================================
    -- ХРАНИМЫЕ ФУНКЦИИ
    -- ============================================
    CREATE OR REPLACE FUNCTION taxi.create_trip(
        p_user_id VARCHAR,
        p_start_lat DOUBLE PRECISION,
        p_start_lon DOUBLE PRECISION,
        p_end_lat DOUBLE PRECISION,
        p_end_lon DOUBLE PRECISION,
        p_start_address VARCHAR,
        p_end_address VARCHAR,
        p_route_geometry JSONB,
        p_distance_m INTEGER,
        p_duration_s INTEGER,
        p_tariff VARCHAR DEFAULT 'economy',
        p_price NUMERIC DEFAULT NULL,
        p_payment_method VARCHAR DEFAULT 'card',
        p_car_model VARCHAR DEFAULT NULL,
        p_car_number VARCHAR DEFAULT NULL,
        p_driver_name VARCHAR DEFAULT NULL,
        p_driver_phone VARCHAR DEFAULT NULL
    ) RETURNS INTEGER AS \$\$
    DECLARE
        v_trip_id INTEGER;
    BEGIN
        INSERT INTO taxi.trips (
            user_id, start_lat, start_lon, end_lat, end_lon,
            start_address, end_address, route_geometry,
            distance_m, duration_s,
            tariff, price, payment_method,
            car_model, car_number, driver_name, driver_phone
        ) VALUES (
            p_user_id, p_start_lat, p_start_lon, p_end_lat, p_end_lon,
            p_start_address, p_end_address, p_route_geometry,
            p_distance_m, p_duration_s,
            p_tariff, p_price, p_payment_method,
            p_car_model, p_car_number, p_driver_name, p_driver_phone
        ) RETURNING id INTO v_trip_id;
        RETURN v_trip_id;
    END;
    \$\$ LANGUAGE plpgsql;

    CREATE OR REPLACE FUNCTION taxi.get_trip_by_id(p_trip_id INTEGER)
    RETURNS TABLE (
        id INTEGER, user_id VARCHAR,
        start_lat DOUBLE PRECISION, start_lon DOUBLE PRECISION,
        end_lat DOUBLE PRECISION, end_lon DOUBLE PRECISION,
        start_address VARCHAR, end_address VARCHAR,
        route_geometry JSONB,
        distance_m INTEGER, duration_s INTEGER,
        status VARCHAR, created_at TIMESTAMP WITH TIME ZONE,
        tariff VARCHAR, price NUMERIC, payment_method VARCHAR,
        car_model VARCHAR, car_number VARCHAR,
        driver_name VARCHAR, driver_phone VARCHAR,
        rating INTEGER
    ) AS \$\$
    BEGIN
        RETURN QUERY SELECT t.* FROM taxi.trips t WHERE t.id = p_trip_id;
    END;
    \$\$ LANGUAGE plpgsql;

    CREATE OR REPLACE FUNCTION taxi.list_user_trips(
        p_user_id VARCHAR,
        p_limit INTEGER DEFAULT 50,
        p_offset INTEGER DEFAULT 0
    ) RETURNS TABLE (
        id INTEGER,
        start_address VARCHAR, end_address VARCHAR,
        distance_m INTEGER, duration_s INTEGER,
        status VARCHAR, created_at TIMESTAMP WITH TIME ZONE,
        tariff VARCHAR, price NUMERIC,
        car_model VARCHAR, driver_name VARCHAR,
        rating INTEGER
    ) AS \$\$
    BEGIN
        RETURN QUERY
        SELECT 
            t.id, t.start_address, t.end_address,
            t.distance_m, t.duration_s, t.status, t.created_at,
            t.tariff, t.price, t.car_model, t.driver_name, t.rating
        FROM taxi.trips t
        WHERE t.user_id = p_user_id
        ORDER BY t.created_at DESC
        LIMIT p_limit OFFSET p_offset;
    END;
    \$\$ LANGUAGE plpgsql;

    CREATE OR REPLACE FUNCTION taxi.rate_trip(
        p_trip_id INTEGER,
        p_user_id VARCHAR,
        p_rating INTEGER
    ) RETURNS BOOLEAN AS \$\$
    DECLARE
        v_success BOOLEAN := FALSE;
    BEGIN
        IF p_rating < 1 OR p_rating > 5 THEN
            RAISE EXCEPTION 'Rating must be between 1 and 5';
        END IF;
        
        UPDATE taxi.trips
        SET rating = p_rating
        WHERE id = p_trip_id AND user_id = p_user_id;
        
        GET DIAGNOSTICS v_success = ROW_COUNT;
        RETURN v_success > 0;
    END;
    \$\$ LANGUAGE plpgsql;

    CREATE OR REPLACE FUNCTION taxi.get_user_trip_stats(p_user_id VARCHAR)
    RETURNS TABLE (
        total_trips BIGINT,
        month_trips BIGINT,
        total_spent NUMERIC,
        month_spent NUMERIC,
        avg_rating NUMERIC
    ) AS \$\$
    BEGIN
        RETURN QUERY
        SELECT 
            COUNT(*)::BIGINT AS total_trips,
            COUNT(*) FILTER (
                WHERE created_at >= date_trunc('month', CURRENT_DATE)
            )::BIGINT AS month_trips,
            COALESCE(SUM(price), 0)::NUMERIC AS total_spent,
            COALESCE(SUM(price) FILTER (
                WHERE created_at >= date_trunc('month', CURRENT_DATE)
            ), 0)::NUMERIC AS month_spent,
            ROUND(AVG(rating)::NUMERIC, 2) AS avg_rating
        FROM taxi.trips
        WHERE user_id = p_user_id;
    END;
    \$\$ LANGUAGE plpgsql;

    -- ============================================
    -- ПРАВА APP-ПОЛЬЗОВАТЕЛЮ
    -- ============================================
    GRANT USAGE ON SCHEMA taxi TO ${APP_DB_USER};
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA taxi TO ${APP_DB_USER};
    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA taxi TO ${APP_DB_USER};
    GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA taxi TO ${APP_DB_USER};

    ALTER DEFAULT PRIVILEGES IN SCHEMA taxi GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ${APP_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA taxi GRANT USAGE, SELECT ON SEQUENCES TO ${APP_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA taxi GRANT EXECUTE ON FUNCTIONS TO ${APP_DB_USER};

EOSQL