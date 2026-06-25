#!/bin/bash
set -e

# Этот скрипт выполняется внутри контейнера postgres при первом запуске.
# Переменные ${POSTGRES_USER}, ${POSTGRES_DB}, ${APP_DB_USER}, ${APP_DB_PASSWORD}
# передаются из docker-compose.yml → из корневого .env

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
    -- ТАБЛИЦА ПОЕЗДОК
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
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    CREATE INDEX idx_trips_user_id ON taxi.trips(user_id);
    CREATE INDEX idx_trips_created_at ON taxi.trips(created_at DESC);

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
        p_duration_s INTEGER
    ) RETURNS INTEGER AS \$\$
    DECLARE
        v_trip_id INTEGER;
    BEGIN
        INSERT INTO taxi.trips (
            user_id, start_lat, start_lon, end_lat, end_lon,
            start_address, end_address, route_geometry,
            distance_m, duration_s
        ) VALUES (
            p_user_id, p_start_lat, p_start_lon, p_end_lat, p_end_lon,
            p_start_address, p_end_address, p_route_geometry,
            p_distance_m, p_duration_s
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
        route_geometry JSONB, distance_m INTEGER, duration_s INTEGER,
        status VARCHAR, created_at TIMESTAMP WITH TIME ZONE
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
        id INTEGER, start_address VARCHAR, end_address VARCHAR,
        distance_m INTEGER, duration_s INTEGER,
        status VARCHAR, created_at TIMESTAMP WITH TIME ZONE
    ) AS \$\$
    BEGIN
        RETURN QUERY
        SELECT t.id, t.start_address, t.end_address,
               t.distance_m, t.duration_s, t.status, t.created_at
        FROM taxi.trips t
        WHERE t.user_id = p_user_id
        ORDER BY t.created_at DESC
        LIMIT p_limit OFFSET p_offset;
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