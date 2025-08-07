-- Fix the get_next_employee_id function to use proper gap-filling logic
CREATE OR REPLACE FUNCTION get_next_employee_id(p_role VARCHAR)
RETURNS VARCHAR AS $$
DECLARE
    next_id INTEGER;
    prefix VARCHAR(10);
    result VARCHAR(50);
    existing_ids INTEGER[];
    i INTEGER;
BEGIN
    -- Set prefix based on role
    CASE p_role
        WHEN 'admin' THEN prefix := 'ADMIN_';
        WHEN 'operator' THEN prefix := 'OP_';
        WHEN 'personnel' THEN prefix := 'PER_';
        ELSE prefix := 'USER_';
    END CASE;
    
    -- Get all existing employee IDs for this role
    SELECT ARRAY_AGG(CAST(SUBSTRING(employee_id FROM LENGTH(prefix) + 1) AS INTEGER) ORDER BY CAST(SUBSTRING(employee_id FROM LENGTH(prefix) + 1) AS INTEGER))
    INTO existing_ids
    FROM users 
    WHERE employee_id LIKE prefix || '%' 
    AND employee_id ~ ('^' || prefix || '[0-9]+$');
    
    -- If no existing IDs, start with 1
    IF existing_ids IS NULL OR array_length(existing_ids, 1) IS NULL THEN
        next_id := 1;
    ELSE
        -- Find the first gap
        next_id := 1;
        FOR i IN 1..array_length(existing_ids, 1) LOOP
            IF existing_ids[i] = next_id THEN
                next_id := next_id + 1;
            ELSE
                EXIT;
            END IF;
        END LOOP;
    END IF;
    
    -- Format the result
    result := prefix || LPAD(next_id::TEXT, 2, '0');
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Fix the gap-filling logic for table IDs
-- Update the users table to use sequential IDs starting from 1
UPDATE users SET id = new_id FROM (
    SELECT username, ROW_NUMBER() OVER (ORDER BY id) as new_id 
    FROM users
) AS numbered WHERE users.username = numbered.username;

-- Reset the users_id_seq to the current maximum
SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id), 0) FROM users));

-- Update operators table to use sequential IDs
UPDATE operators SET id = new_id FROM (
    SELECT username, ROW_NUMBER() OVER (ORDER BY id) as new_id 
    FROM operators
) AS numbered WHERE operators.username = numbered.username;

-- Reset the operators_id_seq to the current maximum
SELECT setval('operators_id_seq', (SELECT COALESCE(MAX(id), 0) FROM operators));

-- Update personnel table to use sequential IDs
UPDATE personnel SET id = new_id FROM (
    SELECT username, ROW_NUMBER() OVER (ORDER BY id) as new_id 
    FROM personnel
) AS numbered WHERE personnel.username = numbered.username;

-- Reset the personnel_id_seq to the current maximum
SELECT setval('personnel_id_seq', (SELECT COALESCE(MAX(id), 0) FROM personnel));

-- Now fix the employee IDs to be sequential
-- For admin users
UPDATE users SET employee_id = 'ADMIN_' || LPAD(ROW_NUMBER() OVER (ORDER BY id)::TEXT, 2, '0')
WHERE role = 'admin';

-- For operator users
UPDATE users SET employee_id = 'OP_' || LPAD(ROW_NUMBER() OVER (ORDER BY id)::TEXT, 2, '0')
WHERE role = 'operator';

-- For personnel users
UPDATE users SET employee_id = 'PER_' || LPAD(ROW_NUMBER() OVER (ORDER BY id)::TEXT, 2, '0')
WHERE role = 'personnel';

-- Update the role-specific tables to match
UPDATE operators SET employee_id = users.employee_id 
FROM users WHERE operators.username = users.username AND users.role = 'operator';

UPDATE personnel SET employee_id = users.employee_id 
FROM users WHERE personnel.username = users.username AND users.role = 'personnel';
