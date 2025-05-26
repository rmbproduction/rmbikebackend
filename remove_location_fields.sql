DO $$
BEGIN
    -- Check and remove preferredLocation column
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'accounts_userprofile' 
        AND column_name = 'preferredlocation'
    ) THEN
        ALTER TABLE accounts_userprofile DROP COLUMN preferredlocation;
    END IF;

    -- Check and remove latitude column
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'accounts_userprofile' 
        AND column_name = 'latitude'
    ) THEN
        ALTER TABLE accounts_userprofile DROP COLUMN latitude;
    END IF;

    -- Check and remove longitude column
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'accounts_userprofile' 
        AND column_name = 'longitude'
    ) THEN
        ALTER TABLE accounts_userprofile DROP COLUMN longitude;
    END IF;
END $$; 