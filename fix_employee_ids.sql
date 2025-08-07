-- Fix employee IDs using a different approach
-- For admin users
UPDATE users SET employee_id = 'ADMIN_' || LPAD(new_id::TEXT, 2, '0')
FROM (
    SELECT username, ROW_NUMBER() OVER (ORDER BY id) as new_id 
    FROM users WHERE role = 'admin'
) AS numbered 
WHERE users.username = numbered.username AND users.role = 'admin';

-- For operator users
UPDATE users SET employee_id = 'OP_' || LPAD(new_id::TEXT, 2, '0')
FROM (
    SELECT username, ROW_NUMBER() OVER (ORDER BY id) as new_id 
    FROM users WHERE role = 'operator'
) AS numbered 
WHERE users.username = numbered.username AND users.role = 'operator';

-- For personnel users
UPDATE users SET employee_id = 'PER_' || LPAD(new_id::TEXT, 2, '0')
FROM (
    SELECT username, ROW_NUMBER() OVER (ORDER BY id) as new_id 
    FROM users WHERE role = 'personnel'
) AS numbered 
WHERE users.username = numbered.username AND users.role = 'personnel';

-- Update the role-specific tables to match
UPDATE operators SET employee_id = users.employee_id 
FROM users WHERE operators.username = users.username AND users.role = 'operator';

UPDATE personnel SET employee_id = users.employee_id 
FROM users WHERE personnel.username = users.username AND users.role = 'personnel';
