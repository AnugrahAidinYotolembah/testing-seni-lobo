-- ==============================================
-- ARSIP DIGITAL KOMUNITAS SENI LOBO PALU
-- FIXED VERSION (SAFE FOR SUPABASE)
-- ==============================================

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    specialization VARCHAR(255) DEFAULT '',
    avatar_url TEXT DEFAULT '',
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'on_leave', 'new', 'inactive')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Collections Table
CREATE TABLE IF NOT EXISTS collections (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT DEFAULT '',
    category VARCHAR(100) NOT NULL CHECK (
        category IN (
            'Photography','Cinematography','Manuscript',
            'Oral History','Textile','Audio Record',
            'Video','Artifact','Lukisan','Tari',
            'Cerpen','Puisi','Teater','Musik Tradisional',
            'Kerajinan','Ritual','Cerita Rakyat',
            'Arsitektur Tradisional'
        )
    ),
    file_url TEXT DEFAULT '',
    thumbnail_url TEXT DEFAULT '',
    creator_name VARCHAR(255) DEFAULT '',
    historical_date VARCHAR(100) DEFAULT '',
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Indexes
CREATE INDEX IF NOT EXISTS idx_collections_user_id ON collections(user_id);
CREATE INDEX IF NOT EXISTS idx_collections_category ON collections(category);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- 4. Trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 5. Triggers
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_collections_updated_at ON collections;
CREATE TRIGGER update_collections_updated_at
BEFORE UPDATE ON collections
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- 6. RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE collections ENABLE ROW LEVEL SECURITY;

-- DROP dulu biar tidak duplicate
DROP POLICY IF EXISTS "Allow all for service" ON users;
CREATE POLICY "Allow all for service"
ON users FOR ALL
USING (true)
WITH CHECK (true);

DROP POLICY IF EXISTS "Allow all for service" ON collections;
CREATE POLICY "Allow all for service"
ON collections FOR ALL
USING (true)
WITH CHECK (true);

-- 7. STORAGE (IMPORTANT FIX HERE)

-- create bucket safely
INSERT INTO storage.buckets (id, name, public)
VALUES ('archives', 'archives', true)
ON CONFLICT (id) DO NOTHING;

-- DELETE ALL OLD POLICIES (ANTI ERROR)
DROP POLICY IF EXISTS "Public Access" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated Upload" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated Update" ON storage.objects;
DROP POLICY IF EXISTS "Authenticated Delete" ON storage.objects;

-- CREATE CLEAN POLICIES
CREATE POLICY "Public Access"
ON storage.objects
FOR SELECT
USING (bucket_id = 'archives');

CREATE POLICY "Authenticated Upload"
ON storage.objects
FOR INSERT
WITH CHECK (bucket_id = 'archives');

CREATE POLICY "Authenticated Update"
ON storage.objects
FOR UPDATE
USING (bucket_id = 'archives');

CREATE POLICY "Authenticated Delete"
ON storage.objects
FOR DELETE
USING (bucket_id = 'archives');

-- 8. Default admin
INSERT INTO users (email, password_hash, full_name, role, specialization, status)
VALUES (
    'admin@lobopalu.id',
    '$2b$12$LJ3f1qM9Y5X5Z5Z5Z5Z5ZeKX5X5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z5Z',
    'Administrator Lobo Palu',
    'admin',
    'System Administrator',
    'active'
)
ON CONFLICT (email) DO NOTHING;
