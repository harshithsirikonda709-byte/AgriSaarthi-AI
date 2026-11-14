-- ============================================================================
-- AgriSaarthi AI — Supabase PostgreSQL Database Schema
-- Run this script in the Supabase SQL Editor (Dashboard -> SQL Editor -> New Query)
-- ============================================================================

-- 1. Farmers table (Core accounts & profile)
CREATE TABLE IF NOT EXISTS public.farmers (
    id BIGSERIAL PRIMARY KEY,
    full_name TEXT NOT NULL,
    identifier TEXT UNIQUE NOT NULL,
    email TEXT NOT NULL DEFAULT '',
    phone_number TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL,
    password_salt TEXT NOT NULL,
    preferred_language TEXT NOT NULL DEFAULT 'te',
    state TEXT NOT NULL DEFAULT '',
    district TEXT NOT NULL DEFAULT '',
    mandal TEXT NOT NULL DEFAULT '',
    village TEXT NOT NULL DEFAULT '',
    land_size_acres DOUBLE PRECISION,
    soil_type TEXT NOT NULL DEFAULT '',
    water_availability TEXT NOT NULL DEFAULT '',
    season TEXT NOT NULL DEFAULT '',
    sowing_date TEXT NOT NULL DEFAULT '',
    crop_growth_stage TEXT NOT NULL DEFAULT '',
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    budget_inr DOUBLE PRECISION,
    risk_tolerance TEXT NOT NULL DEFAULT 'moderate',
    primary_crops_grown TEXT NOT NULL DEFAULT '',
    profile_completed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for fast identifier / mobile / email lookups
CREATE INDEX IF NOT EXISTS idx_farmers_identifier ON public.farmers(identifier);
CREATE INDEX IF NOT EXISTS idx_farmers_phone ON public.farmers(phone_number);
CREATE INDEX IF NOT EXISTS idx_farmers_email ON public.farmers(email);
CREATE INDEX IF NOT EXISTS idx_farmers_coords ON public.farmers(latitude, longitude);

-- 2. Sessions table (Secure Bearer Tokens)
CREATE TABLE IF NOT EXISTS public.sessions (
    token TEXT PRIMARY KEY,
    farmer_id BIGINT NOT NULL REFERENCES public.farmers(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_farmer ON public.sessions(farmer_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON public.sessions(expires_at);

-- 3. Advisory History table (Recommendations & Diagnostics)
CREATE TABLE IF NOT EXISTS public.advisory_history (
    id BIGSERIAL PRIMARY KEY,
    farmer_id BIGINT NOT NULL REFERENCES public.farmers(id) ON DELETE CASCADE,
    advisory_type TEXT NOT NULL,
    query_summary TEXT NOT NULL,
    result_summary TEXT NOT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_advisory_farmer ON public.advisory_history(farmer_id);

-- 4. Crop Observations table (Location-Aware Peer Intelligence)
CREATE TABLE IF NOT EXISTS public.crop_observations (
    id BIGSERIAL PRIMARY KEY,
    farmer_id BIGINT REFERENCES public.farmers(id) ON DELETE SET NULL,
    farmer_name TEXT NOT NULL DEFAULT '',
    crop_name TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    sowing_date TEXT NOT NULL,
    crop_growth_stage TEXT NOT NULL,
    consent_shared BOOLEAN NOT NULL DEFAULT TRUE,
    field_notes TEXT NOT NULL DEFAULT '',
    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_obs_coords ON public.crop_observations(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_obs_crop ON public.crop_observations(crop_name);
CREATE INDEX IF NOT EXISTS idx_obs_consent ON public.crop_observations(consent_shared);

-- 5. Relational Views (Matching local database views)
CREATE OR REPLACE VIEW public.users AS
    SELECT 
        id,
        identifier,
        password_hash,
        password_salt,
        created_at,
        updated_at
    FROM public.farmers;

CREATE OR REPLACE VIEW public.farmer_profiles AS
    SELECT 
        id,
        id AS user_id,
        full_name,
        email,
        phone_number,
        preferred_language,
        state,
        district,
        mandal,
        village,
        latitude,
        longitude,
        profile_completed,
        created_at,
        updated_at
    FROM public.farmers;

CREATE OR REPLACE VIEW public.farm_details AS
    SELECT 
        id,
        id AS user_id,
        land_size_acres,
        soil_type,
        water_availability,
        season,
        sowing_date,
        crop_growth_stage,
        latitude,
        longitude,
        budget_inr,
        risk_tolerance,
        primary_crops_grown,
        created_at,
        updated_at
    FROM public.farmers;
