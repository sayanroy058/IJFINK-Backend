-- ====================================================
-- Initial admin seed data
-- Database: journaldb
-- Inserts Admin Trimplin as user_id 1 and admin_id 1
-- Password hash generated from: Admin@123
-- ====================================================

USE journaldb;

INSERT INTO users (user_id, email, password_hash, role, status)
VALUES (
    1,
    'trimplin@admin.com',
    'scrypt:32768:8:1$qKPz7FWn3vYhjiGu$d14fe7529200a2294e08c5ebb505f52b7f4b190784835c320aa723fa14a549c3ce7465dbd5a47534cc830faab354fe6fb1a8f02ba2d7c3a097d45c78fab980b0',
    'Admin',
    'Active'
);

INSERT INTO admins (admin_id, user_id, first_name, last_name)
VALUES (
    1,
    1,
    'Admin',
    'Trimplin'
);

ALTER TABLE users AUTO_INCREMENT = 2;
ALTER TABLE admins AUTO_INCREMENT = 2;
