-- ============================================================
-- Optional demo data for manual testing via psql.
-- Password for both accounts below is: ChangeMe123!
-- (bcrypt/werkzeug hash shown is illustrative — prefer `flask seed-db`,
--  which generates a correct hash using the app's own password hasher,
--  over inserting a hash manually here.)
-- ============================================================

-- Recommended: run `flask seed-db` instead of this file.
-- This file is kept only as a reference for the expected row shapes.

-- INSERT INTO users (name, email, password_hash, role, roll_number)
-- VALUES ('Dr. Ananya Kulkarni', 'faculty@example.edu', '<generated-hash>', 'faculty', NULL);

-- INSERT INTO users (name, email, password_hash, role, roll_number)
-- VALUES ('Rohan Deshmukh', 'student@example.edu', '<generated-hash>', 'student', 'RCPIT2023CO045');

-- INSERT INTO courses (name, code, faculty_id)
-- VALUES ('Cloud Computing Fundamentals', 'CS401', 1);

-- INSERT INTO enrollments (student_id, course_id) VALUES (2, 1);
