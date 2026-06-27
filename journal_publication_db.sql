-- ====================================================
-- Journal Publication Management System Database
-- MySQL 8.0
-- Database: journaldb
-- ====================================================

DROP DATABASE IF EXISTS journaldb;
CREATE DATABASE journaldb
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE journaldb;

-- ====================================================
-- Tables
-- ====================================================

-- Table: users
-- Purpose: Stores authentication-only data. Personal information is kept in role-specific tables.
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('Author', 'Admin', 'Editor', 'Publication Team') NOT NULL,
    status ENUM('Active', 'Inactive') NOT NULL DEFAULT 'Active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT chk_users_email_format CHECK (email LIKE '%_@_%._%'),
    CONSTRAINT chk_users_role CHECK (role IN ('Author', 'Admin', 'Editor', 'Publication Team')),
    CONSTRAINT chk_users_status CHECK (status IN ('Active', 'Inactive'))
) ENGINE=InnoDB COMMENT='Authentication accounts only; no personal profile data is stored here.';

-- Table: authors
-- Purpose: Stores author profile data linked one-to-one with a user account.
CREATE TABLE authors (
    author_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    orcid VARCHAR(19),
    institution VARCHAR(255) NOT NULL,
    phone_number VARCHAR(30),
    CONSTRAINT uq_authors_user_id UNIQUE (user_id),
    CONSTRAINT uq_authors_orcid UNIQUE (orcid),
    CONSTRAINT chk_authors_orcid_format CHECK (orcid IS NULL OR orcid REGEXP '^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$'),
    CONSTRAINT fk_authors_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Author profile data; one author profile belongs to one authentication user.';

-- Table: admins
-- Purpose: Stores admin profile data linked one-to-one with a user account.
CREATE TABLE admins (
    admin_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    CONSTRAINT uq_admins_user_id UNIQUE (user_id),
    CONSTRAINT fk_admins_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Administrative staff profiles. Admins do not store institution data.';

-- Table: editors
-- Purpose: Stores editorial board member profiles, including the chief editor flag.
CREATE TABLE editors (
    editor_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    institution VARCHAR(255) NOT NULL,
    is_chief_editor BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_editors_user_id UNIQUE (user_id),
    CONSTRAINT fk_editors_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Editorial board member profiles. A trigger limits the database to one chief editor.';

-- Table: publication_team
-- Purpose: Stores publication team profile data linked one-to-one with a user account.
CREATE TABLE publication_team (
    publication_team_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    CONSTRAINT uq_publication_team_user_id UNIQUE (user_id),
    CONSTRAINT fk_publication_team_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Publication team profiles. No institution or designation data is stored.';

-- Table: manuscripts
-- Purpose: Stores manuscript metadata and current workflow status.
CREATE TABLE manuscripts (
    manuscript_id INT AUTO_INCREMENT PRIMARY KEY,
    author_id INT NOT NULL,
    title VARCHAR(500) NOT NULL,
    abstract TEXT NOT NULL,
    keywords VARCHAR(500),
    article_type VARCHAR(100) NOT NULL,
    subject_area VARCHAR(150) NOT NULL,
    status ENUM(
        'Submitted',
        'Admin Approved',
        'Admin Rejected',
        'Chief Editor Review',
        'Editorial Review',
        'Revision Requested',
        'Accepted',
        'Rejected',
        'Published'
    ) NOT NULL DEFAULT 'Submitted',
    submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_manuscripts_status CHECK (status IN (
        'Submitted',
        'Admin Approved',
        'Admin Rejected',
        'Chief Editor Review',
        'Editorial Review',
        'Revision Requested',
        'Accepted',
        'Rejected',
        'Published'
    )),
    CONSTRAINT fk_manuscripts_author
        FOREIGN KEY (author_id) REFERENCES authors(author_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Submitted manuscript records with normalized author ownership and workflow state.';

-- Table: co_authors
-- Purpose: Stores manuscript co-author details in ordered form.
CREATE TABLE co_authors (
    co_author_id INT AUTO_INCREMENT PRIMARY KEY,
    manuscript_id INT NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    email VARCHAR(255) NOT NULL,
    institution VARCHAR(255) NOT NULL,
    orcid VARCHAR(19),
    author_order INT NOT NULL,
    CONSTRAINT uq_co_authors_order UNIQUE (manuscript_id, author_order),
    CONSTRAINT uq_co_authors_email_per_manuscript UNIQUE (manuscript_id, email),
    CONSTRAINT chk_co_authors_email_format CHECK (email LIKE '%_@_%._%'),
    CONSTRAINT chk_co_authors_author_order CHECK (author_order >= 1),
    CONSTRAINT chk_co_authors_orcid_format CHECK (orcid IS NULL OR orcid REGEXP '^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$'),
    CONSTRAINT fk_co_authors_manuscript
        FOREIGN KEY (manuscript_id) REFERENCES manuscripts(manuscript_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Ordered co-author list for each manuscript.';

-- Table: files
-- Purpose: Stores uploaded manuscript files and generated screening reports.
CREATE TABLE files (
    file_id INT AUTO_INCREMENT PRIMARY KEY,
    manuscript_id INT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_type ENUM(
        'Manuscript',
        'Cover Letter',
        'Copyright Form',
        'Figures',
        'Supplementary File',
        'Plagiarism Report',
        'AI Detection Report',
        'Revision File'
    ) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    version INT NOT NULL DEFAULT 1,
    uploaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_files_manuscript_type_version UNIQUE (manuscript_id, file_type, version),
    CONSTRAINT chk_files_type CHECK (file_type IN (
        'Manuscript',
        'Cover Letter',
        'Copyright Form',
        'Figures',
        'Supplementary File',
        'Plagiarism Report',
        'AI Detection Report',
        'Revision File'
    )),
    CONSTRAINT chk_files_version CHECK (version >= 1),
    CONSTRAINT fk_files_manuscript
        FOREIGN KEY (manuscript_id) REFERENCES manuscripts(manuscript_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='All manuscript-related uploads and screening report files.';

-- Table: admin_screening
-- Purpose: Stores the initial administrative screening decision.
CREATE TABLE admin_screening (
    screening_id INT AUTO_INCREMENT PRIMARY KEY,
    manuscript_id INT NOT NULL,
    admin_id INT NOT NULL,
    decision ENUM('Approved', 'Rejected') NOT NULL,
    remarks TEXT,
    screened_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_admin_screening_manuscript UNIQUE (manuscript_id),
    CONSTRAINT chk_admin_screening_decision CHECK (decision IN ('Approved', 'Rejected')),
    CONSTRAINT fk_admin_screening_manuscript
        FOREIGN KEY (manuscript_id) REFERENCES manuscripts(manuscript_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_admin_screening_admin
        FOREIGN KEY (admin_id) REFERENCES admins(admin_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='One initial screening record per manuscript, performed by an admin.';

-- Table: editorial_assignment
-- Purpose: Stores editor assignments made by admins. Only one active assignment is allowed per manuscript.
CREATE TABLE editorial_assignment (
    assignment_id INT AUTO_INCREMENT PRIMARY KEY,
    manuscript_id INT NOT NULL,
    admin_id INT NOT NULL,
    editor_id INT NOT NULL,
    assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status ENUM('Active', 'Completed', 'Cancelled') NOT NULL DEFAULT 'Active',
    CONSTRAINT chk_editorial_assignment_status CHECK (status IN ('Active', 'Completed', 'Cancelled')),
    CONSTRAINT fk_editorial_assignment_manuscript
        FOREIGN KEY (manuscript_id) REFERENCES manuscripts(manuscript_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_editorial_assignment_admin
        FOREIGN KEY (admin_id) REFERENCES admins(admin_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT fk_editorial_assignment_editor
        FOREIGN KEY (editor_id) REFERENCES editors(editor_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Admin-created editorial board assignments; chief editor is not stored here.';

-- Table: chief_editor_review
-- Purpose: Stores chief editor verification of files, plagiarism report, and AI detection report.
CREATE TABLE chief_editor_review (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    assignment_id INT NOT NULL,
    chief_editor_id INT NOT NULL,
    plagiarism_percentage DECIMAL(5,2) NOT NULL,
    ai_percentage DECIMAL(5,2) NOT NULL,
    file_check_status ENUM('Passed', 'Failed') NOT NULL,
    decision ENUM('Approved', 'Return to Author', 'Rejected') NOT NULL,
    remarks TEXT,
    reviewed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_chief_editor_review_assignment UNIQUE (assignment_id),
    CONSTRAINT chk_chief_editor_review_plagiarism CHECK (plagiarism_percentage BETWEEN 0 AND 100),
    CONSTRAINT chk_chief_editor_review_ai CHECK (ai_percentage BETWEEN 0 AND 100),
    CONSTRAINT chk_chief_editor_review_file_status CHECK (file_check_status IN ('Passed', 'Failed')),
    CONSTRAINT chk_chief_editor_review_decision CHECK (decision IN ('Approved', 'Return to Author', 'Rejected')),
    CONSTRAINT fk_chief_editor_review_assignment
        FOREIGN KEY (assignment_id) REFERENCES editorial_assignment(assignment_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_chief_editor_review_chief_editor
        FOREIGN KEY (chief_editor_id) REFERENCES editors(editor_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Chief editor verification step for uploaded files, plagiarism, and AI detection only.';

-- Table: editorial_review
-- Purpose: Stores review decisions made by the assigned editorial board member.
CREATE TABLE editorial_review (
    editorial_review_id INT AUTO_INCREMENT PRIMARY KEY,
    assignment_id INT NOT NULL,
    editor_id INT NOT NULL,
    decision ENUM('Accepted', 'Minor Revision', 'Major Revision', 'Rejected') NOT NULL,
    comments TEXT,
    reviewed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_editorial_review_decision CHECK (decision IN ('Accepted', 'Minor Revision', 'Major Revision', 'Rejected')),
    CONSTRAINT fk_editorial_review_assignment
        FOREIGN KEY (assignment_id) REFERENCES editorial_assignment(assignment_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_editorial_review_editor
        FOREIGN KEY (editor_id) REFERENCES editors(editor_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Editorial board review history for each assignment, including revision decisions.';

-- Table: revisions
-- Purpose: Stores author-submitted revision responses tied to prior editorial reviews.
CREATE TABLE revisions (
    revision_id INT AUTO_INCREMENT PRIMARY KEY,
    manuscript_id INT NOT NULL,
    editorial_review_id INT NOT NULL,
    author_id INT NOT NULL,
    revision_number INT NOT NULL,
    response_letter TEXT NOT NULL,
    submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_revisions_manuscript_number UNIQUE (manuscript_id, revision_number),
    CONSTRAINT chk_revisions_number CHECK (revision_number >= 1),
    CONSTRAINT fk_revisions_manuscript
        FOREIGN KEY (manuscript_id) REFERENCES manuscripts(manuscript_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_revisions_editorial_review
        FOREIGN KEY (editorial_review_id) REFERENCES editorial_review(editorial_review_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT fk_revisions_author
        FOREIGN KEY (author_id) REFERENCES authors(author_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Revision submissions uploaded by authors after minor or major revision requests.';

-- Table: publications
-- Purpose: Stores publication metadata assigned by the publication team.
CREATE TABLE publications (
    publication_id INT AUTO_INCREMENT PRIMARY KEY,
    manuscript_id INT NOT NULL,
    publication_team_id INT NOT NULL,
    doi VARCHAR(255) NOT NULL,
    article_url VARCHAR(700) NOT NULL,
    volume VARCHAR(50) NOT NULL,
    issue VARCHAR(50) NOT NULL,
    pages VARCHAR(50) NOT NULL,
    publication_date DATE NOT NULL,
    CONSTRAINT uq_publications_manuscript UNIQUE (manuscript_id),
    CONSTRAINT uq_publications_doi UNIQUE (doi),
    CONSTRAINT uq_publications_article_url UNIQUE (article_url),
    CONSTRAINT chk_publications_doi_format CHECK (doi LIKE '10.%/%'),
    CONSTRAINT fk_publications_manuscript
        FOREIGN KEY (manuscript_id) REFERENCES manuscripts(manuscript_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT fk_publications_publication_team
        FOREIGN KEY (publication_team_id) REFERENCES publication_team(publication_team_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Final publication records with unique DOI and article URL.';

-- Table: notifications
-- Purpose: Stores workflow notifications sent to users for manuscript events.
CREATE TABLE notifications (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    manuscript_id INT,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notifications_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_notifications_manuscript
        FOREIGN KEY (manuscript_id) REFERENCES manuscripts(manuscript_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='User notifications generated during manuscript workflow transitions.';

-- Table: contact_queries
-- Purpose: Stores contact form messages and admin resolution tracking.
CREATE TABLE contact_queries (
    query_id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    status ENUM('Pending', 'Resolved') NOT NULL DEFAULT 'Pending',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,
    CONSTRAINT chk_contact_queries_email_format CHECK (email LIKE '%_@_%._%'),
    CONSTRAINT chk_contact_queries_status CHECK (status IN ('Pending', 'Resolved')),
    CONSTRAINT chk_contact_queries_resolved_at CHECK (
        (status = 'Pending' AND resolved_at IS NULL)
        OR (status = 'Resolved' AND resolved_at IS NOT NULL)
    ),
    CONSTRAINT fk_contact_queries_admin
        FOREIGN KEY (admin_id) REFERENCES admins(admin_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Public contact queries optionally assigned to admins for resolution.';

-- ====================================================
-- Indexes
-- ====================================================

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_status ON users(status);

CREATE INDEX idx_authors_user_id ON authors(user_id);

CREATE INDEX idx_manuscripts_author_id ON manuscripts(author_id);
CREATE INDEX idx_manuscripts_status ON manuscripts(status);

CREATE INDEX idx_co_authors_manuscript_id ON co_authors(manuscript_id);
CREATE INDEX idx_files_manuscript_id ON files(manuscript_id);

CREATE INDEX idx_admin_screening_manuscript_id ON admin_screening(manuscript_id);
CREATE INDEX idx_admin_screening_admin_id ON admin_screening(admin_id);

CREATE INDEX idx_editorial_assignment_manuscript_id ON editorial_assignment(manuscript_id);
CREATE INDEX idx_editorial_assignment_admin_id ON editorial_assignment(admin_id);
CREATE INDEX idx_editorial_assignment_editor_id ON editorial_assignment(editor_id);
CREATE INDEX idx_editorial_assignment_status ON editorial_assignment(status);

CREATE INDEX idx_chief_editor_review_assignment_id ON chief_editor_review(assignment_id);
CREATE INDEX idx_chief_editor_review_chief_editor_id ON chief_editor_review(chief_editor_id);

CREATE INDEX idx_editorial_review_assignment_id ON editorial_review(assignment_id);
CREATE INDEX idx_editorial_review_editor_id ON editorial_review(editor_id);

CREATE INDEX idx_revisions_manuscript_id ON revisions(manuscript_id);
CREATE INDEX idx_revisions_author_id ON revisions(author_id);

CREATE INDEX idx_publications_manuscript_id ON publications(manuscript_id);
CREATE INDEX idx_publications_publication_team_id ON publications(publication_team_id);
CREATE INDEX idx_publications_publication_date ON publications(publication_date);
CREATE INDEX idx_publications_doi ON publications(doi);
CREATE INDEX idx_publications_article_url ON publications(article_url(191));

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_manuscript_id ON notifications(manuscript_id);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);

CREATE INDEX idx_contact_queries_admin_id ON contact_queries(admin_id);
CREATE INDEX idx_contact_queries_status ON contact_queries(status);

-- ====================================================
-- Triggers
-- ====================================================

DELIMITER $$

CREATE TRIGGER trg_users_set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
BEGIN
    SET NEW.updated_at = CURRENT_TIMESTAMP;
END$$

CREATE TRIGGER trg_manuscripts_set_updated_at
BEFORE UPDATE ON manuscripts
FOR EACH ROW
BEGIN
    SET NEW.updated_at = CURRENT_TIMESTAMP;
END$$

CREATE TRIGGER trg_authors_validate_user_role
BEFORE INSERT ON authors
FOR EACH ROW
BEGIN
    IF (SELECT role FROM users WHERE user_id = NEW.user_id) <> 'Author' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'authors.user_id must reference a user with role Author';
    END IF;
END$$

CREATE TRIGGER trg_authors_validate_user_role_update
BEFORE UPDATE ON authors
FOR EACH ROW
BEGIN
    IF (SELECT role FROM users WHERE user_id = NEW.user_id) <> 'Author' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'authors.user_id must reference a user with role Author';
    END IF;
END$$

CREATE TRIGGER trg_admins_validate_user_role
BEFORE INSERT ON admins
FOR EACH ROW
BEGIN
    IF (SELECT role FROM users WHERE user_id = NEW.user_id) <> 'Admin' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'admins.user_id must reference a user with role Admin';
    END IF;
END$$

CREATE TRIGGER trg_admins_validate_user_role_update
BEFORE UPDATE ON admins
FOR EACH ROW
BEGIN
    IF (SELECT role FROM users WHERE user_id = NEW.user_id) <> 'Admin' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'admins.user_id must reference a user with role Admin';
    END IF;
END$$

CREATE TRIGGER trg_editors_validate_user_role
BEFORE INSERT ON editors
FOR EACH ROW
BEGIN
    IF (SELECT role FROM users WHERE user_id = NEW.user_id) <> 'Editor' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'editors.user_id must reference a user with role Editor';
    END IF;

    IF NEW.is_chief_editor = TRUE
        AND EXISTS (SELECT 1 FROM editors WHERE is_chief_editor = TRUE) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Only one editor can be marked as chief editor';
    END IF;
END$$

CREATE TRIGGER trg_editors_validate_user_role_update
BEFORE UPDATE ON editors
FOR EACH ROW
BEGIN
    IF (SELECT role FROM users WHERE user_id = NEW.user_id) <> 'Editor' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'editors.user_id must reference a user with role Editor';
    END IF;

    IF NEW.is_chief_editor = TRUE
        AND EXISTS (
            SELECT 1
            FROM editors
            WHERE is_chief_editor = TRUE
              AND editor_id <> OLD.editor_id
        ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Only one editor can be marked as chief editor';
    END IF;
END$$

CREATE TRIGGER trg_publication_team_validate_user_role
BEFORE INSERT ON publication_team
FOR EACH ROW
BEGIN
    IF (SELECT role FROM users WHERE user_id = NEW.user_id) <> 'Publication Team' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'publication_team.user_id must reference a user with role Publication Team';
    END IF;
END$$

CREATE TRIGGER trg_publication_team_validate_user_role_update
BEFORE UPDATE ON publication_team
FOR EACH ROW
BEGIN
    IF (SELECT role FROM users WHERE user_id = NEW.user_id) <> 'Publication Team' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'publication_team.user_id must reference a user with role Publication Team';
    END IF;
END$$

CREATE TRIGGER trg_manuscripts_after_insert_notify
AFTER INSERT ON manuscripts
FOR EACH ROW
BEGIN
    INSERT INTO notifications (user_id, manuscript_id, title, message)
    SELECT a.user_id, NEW.manuscript_id, 'Submission Received',
           CONCAT('Your manuscript "', NEW.title, '" has been received.')
    FROM authors a
    WHERE a.author_id = NEW.author_id;
END$$

CREATE TRIGGER trg_admin_screening_after_insert
AFTER INSERT ON admin_screening
FOR EACH ROW
BEGIN
    IF NEW.decision = 'Approved' THEN
        UPDATE manuscripts
        SET status = 'Admin Approved'
        WHERE manuscript_id = NEW.manuscript_id;

        INSERT INTO notifications (user_id, manuscript_id, title, message)
        SELECT a.user_id, NEW.manuscript_id, 'Admin Approved',
               'Your manuscript passed initial administrative screening.'
        FROM manuscripts m
        JOIN authors a ON a.author_id = m.author_id
        WHERE m.manuscript_id = NEW.manuscript_id;
    ELSE
        UPDATE manuscripts
        SET status = 'Admin Rejected'
        WHERE manuscript_id = NEW.manuscript_id;

        INSERT INTO notifications (user_id, manuscript_id, title, message)
        SELECT a.user_id, NEW.manuscript_id, 'Admin Rejected',
               'Your manuscript did not pass initial administrative screening.'
        FROM manuscripts m
        JOIN authors a ON a.author_id = m.author_id
        WHERE m.manuscript_id = NEW.manuscript_id;
    END IF;
END$$

CREATE TRIGGER trg_editorial_assignment_before_insert
BEFORE INSERT ON editorial_assignment
FOR EACH ROW
BEGIN
    IF (SELECT status FROM manuscripts WHERE manuscript_id = NEW.manuscript_id) <> 'Admin Approved' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'An editor can be assigned only after admin approval';
    END IF;

    IF NEW.status = 'Active'
        AND EXISTS (
            SELECT 1
            FROM editorial_assignment
            WHERE manuscript_id = NEW.manuscript_id
              AND status = 'Active'
        ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Only one active editorial assignment is allowed per manuscript';
    END IF;
END$$

CREATE TRIGGER trg_editorial_assignment_before_update
BEFORE UPDATE ON editorial_assignment
FOR EACH ROW
BEGIN
    IF NEW.status = 'Active'
        AND EXISTS (
            SELECT 1
            FROM editorial_assignment
            WHERE manuscript_id = NEW.manuscript_id
              AND status = 'Active'
              AND assignment_id <> OLD.assignment_id
        ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Only one active editorial assignment is allowed per manuscript';
    END IF;
END$$

CREATE TRIGGER trg_editorial_assignment_after_insert
AFTER INSERT ON editorial_assignment
FOR EACH ROW
BEGIN
    UPDATE manuscripts
    SET status = 'Chief Editor Review'
    WHERE manuscript_id = NEW.manuscript_id;
END$$

CREATE TRIGGER trg_chief_editor_review_before_insert
BEFORE INSERT ON chief_editor_review
FOR EACH ROW
BEGIN
    DECLARE v_manuscript_id INT;

    IF NOT EXISTS (
        SELECT 1 FROM editors
        WHERE editor_id = NEW.chief_editor_id
          AND is_chief_editor = TRUE
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'chief_editor_id must reference an editor marked as chief editor';
    END IF;

    SELECT manuscript_id
    INTO v_manuscript_id
    FROM editorial_assignment
    WHERE assignment_id = NEW.assignment_id;

    IF NEW.decision = 'Approved' AND NEW.file_check_status <> 'Passed' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Chief editor approval requires passed file checks';
    END IF;

    IF NEW.decision = 'Approved' AND (
        NOT EXISTS (SELECT 1 FROM files WHERE manuscript_id = v_manuscript_id AND file_type = 'Manuscript')
        OR NOT EXISTS (SELECT 1 FROM files WHERE manuscript_id = v_manuscript_id AND file_type = 'Plagiarism Report')
        OR NOT EXISTS (SELECT 1 FROM files WHERE manuscript_id = v_manuscript_id AND file_type = 'AI Detection Report')
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Chief editor approval requires manuscript, plagiarism report, and AI detection report files';
    END IF;
END$$

CREATE TRIGGER trg_chief_editor_review_after_insert
AFTER INSERT ON chief_editor_review
FOR EACH ROW
BEGIN
    DECLARE v_manuscript_id INT;

    SELECT manuscript_id
    INTO v_manuscript_id
    FROM editorial_assignment
    WHERE assignment_id = NEW.assignment_id;

    IF NEW.decision = 'Approved' THEN
        UPDATE manuscripts
        SET status = 'Editorial Review'
        WHERE manuscript_id = v_manuscript_id;
    ELSEIF NEW.decision = 'Return to Author' THEN
        UPDATE manuscripts
        SET status = 'Revision Requested'
        WHERE manuscript_id = v_manuscript_id;

        INSERT INTO notifications (user_id, manuscript_id, title, message)
        SELECT a.user_id, v_manuscript_id, 'Chief Editor Returned Paper',
               'The chief editor returned your manuscript for correction before editorial review.'
        FROM manuscripts m
        JOIN authors a ON a.author_id = m.author_id
        WHERE m.manuscript_id = v_manuscript_id;
    ELSE
        UPDATE manuscripts
        SET status = 'Rejected'
        WHERE manuscript_id = v_manuscript_id;

        INSERT INTO notifications (user_id, manuscript_id, title, message)
        SELECT a.user_id, v_manuscript_id, 'Rejected',
               'Your manuscript was rejected during chief editor verification.'
        FROM manuscripts m
        JOIN authors a ON a.author_id = m.author_id
        WHERE m.manuscript_id = v_manuscript_id;
    END IF;
END$$

CREATE TRIGGER trg_editorial_review_before_insert
BEFORE INSERT ON editorial_review
FOR EACH ROW
BEGIN
    DECLARE v_assignment_editor_id INT;
    DECLARE v_manuscript_status VARCHAR(50);

    SELECT ea.editor_id, m.status
    INTO v_assignment_editor_id, v_manuscript_status
    FROM editorial_assignment ea
    JOIN manuscripts m ON m.manuscript_id = ea.manuscript_id
    WHERE ea.assignment_id = NEW.assignment_id;

    IF NEW.editor_id <> v_assignment_editor_id THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Editorial review must be performed by the assigned editor';
    END IF;

    IF v_manuscript_status NOT IN ('Editorial Review', 'Revision Requested') THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Editorial review is allowed only during editorial review or revision workflow';
    END IF;
END$$

CREATE TRIGGER trg_editorial_review_after_insert
AFTER INSERT ON editorial_review
FOR EACH ROW
BEGIN
    DECLARE v_manuscript_id INT;

    SELECT manuscript_id
    INTO v_manuscript_id
    FROM editorial_assignment
    WHERE assignment_id = NEW.assignment_id;

    IF NEW.decision = 'Accepted' THEN
        UPDATE manuscripts
        SET status = 'Accepted'
        WHERE manuscript_id = v_manuscript_id;

        UPDATE editorial_assignment
        SET status = 'Completed'
        WHERE assignment_id = NEW.assignment_id;

        INSERT INTO notifications (user_id, manuscript_id, title, message)
        SELECT a.user_id, v_manuscript_id, 'Accepted',
               'Your manuscript has been accepted for publication.'
        FROM manuscripts m
        JOIN authors a ON a.author_id = m.author_id
        WHERE m.manuscript_id = v_manuscript_id;
    ELSEIF NEW.decision IN ('Minor Revision', 'Major Revision') THEN
        UPDATE manuscripts
        SET status = 'Revision Requested'
        WHERE manuscript_id = v_manuscript_id;

        INSERT INTO notifications (user_id, manuscript_id, title, message)
        SELECT a.user_id, v_manuscript_id, 'Revision Requested',
               CONCAT('Your manuscript requires ', NEW.decision, '.')
        FROM manuscripts m
        JOIN authors a ON a.author_id = m.author_id
        WHERE m.manuscript_id = v_manuscript_id;
    ELSE
        UPDATE manuscripts
        SET status = 'Rejected'
        WHERE manuscript_id = v_manuscript_id;

        UPDATE editorial_assignment
        SET status = 'Completed'
        WHERE assignment_id = NEW.assignment_id;

        INSERT INTO notifications (user_id, manuscript_id, title, message)
        SELECT a.user_id, v_manuscript_id, 'Rejected',
               'Your manuscript was rejected after editorial review.'
        FROM manuscripts m
        JOIN authors a ON a.author_id = m.author_id
        WHERE m.manuscript_id = v_manuscript_id;
    END IF;
END$$

CREATE TRIGGER trg_revisions_before_insert
BEFORE INSERT ON revisions
FOR EACH ROW
BEGIN
    DECLARE v_review_decision VARCHAR(50);
    DECLARE v_review_manuscript_id INT;

    SELECT er.decision, ea.manuscript_id
    INTO v_review_decision, v_review_manuscript_id
    FROM editorial_review er
    JOIN editorial_assignment ea ON ea.assignment_id = er.assignment_id
    WHERE er.editorial_review_id = NEW.editorial_review_id;

    IF v_review_decision NOT IN ('Minor Revision', 'Major Revision') THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'A revision can be submitted only after a minor or major revision decision';
    END IF;

    IF NEW.manuscript_id <> v_review_manuscript_id THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Revision manuscript must match the editorial review assignment manuscript';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM manuscripts
        WHERE manuscript_id = NEW.manuscript_id
          AND author_id = NEW.author_id
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Revision author must be the manuscript owner';
    END IF;
END$$

CREATE TRIGGER trg_revisions_after_insert
AFTER INSERT ON revisions
FOR EACH ROW
BEGIN
    UPDATE manuscripts
    SET status = 'Editorial Review'
    WHERE manuscript_id = NEW.manuscript_id;
END$$

CREATE TRIGGER trg_publications_before_insert
BEFORE INSERT ON publications
FOR EACH ROW
BEGIN
    IF (SELECT status FROM manuscripts WHERE manuscript_id = NEW.manuscript_id) <> 'Accepted' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Only accepted manuscripts can be published';
    END IF;
END$$

CREATE TRIGGER trg_publications_after_insert
AFTER INSERT ON publications
FOR EACH ROW
BEGIN
    UPDATE manuscripts
    SET status = 'Published'
    WHERE manuscript_id = NEW.manuscript_id;

    INSERT INTO notifications (user_id, manuscript_id, title, message)
    SELECT a.user_id, NEW.manuscript_id, 'Published',
           CONCAT('Your article has been published with DOI ', NEW.doi, '.')
    FROM manuscripts m
    JOIN authors a ON a.author_id = m.author_id
    WHERE m.manuscript_id = NEW.manuscript_id;
END$$

DELIMITER ;

-- ====================================================
-- Views
-- ====================================================

CREATE VIEW vw_current_manuscript_status AS
SELECT
    m.manuscript_id,
    m.title,
    CONCAT(a.first_name, ' ', a.last_name) AS author_name,
    u.email AS author_email,
    m.article_type,
    m.subject_area,
    m.status,
    m.submitted_at,
    m.updated_at
FROM manuscripts m
JOIN authors a ON a.author_id = m.author_id
JOIN users u ON u.user_id = a.user_id;

CREATE VIEW vw_published_articles AS
SELECT
    p.publication_id,
    m.manuscript_id,
    m.title,
    CONCAT(a.first_name, ' ', a.last_name) AS author_name,
    p.doi,
    p.article_url,
    p.volume,
    p.issue,
    p.pages,
    p.publication_date
FROM publications p
JOIN manuscripts m ON m.manuscript_id = p.manuscript_id
JOIN authors a ON a.author_id = m.author_id;

CREATE VIEW vw_pending_editorial_assignments AS
SELECT
    m.manuscript_id,
    m.title,
    m.status,
    s.screened_at,
    CONCAT(ad.first_name, ' ', ad.last_name) AS screened_by
FROM manuscripts m
JOIN admin_screening s ON s.manuscript_id = m.manuscript_id
JOIN admins ad ON ad.admin_id = s.admin_id
LEFT JOIN editorial_assignment ea
    ON ea.manuscript_id = m.manuscript_id
   AND ea.status = 'Active'
WHERE m.status = 'Admin Approved'
  AND ea.assignment_id IS NULL;

CREATE VIEW vw_pending_chief_editor_reviews AS
SELECT
    ea.assignment_id,
    m.manuscript_id,
    m.title,
    CONCAT(e.first_name, ' ', e.last_name) AS assigned_editor,
    ea.assigned_at
FROM editorial_assignment ea
JOIN manuscripts m ON m.manuscript_id = ea.manuscript_id
JOIN editors e ON e.editor_id = ea.editor_id
LEFT JOIN chief_editor_review cer ON cer.assignment_id = ea.assignment_id
WHERE ea.status = 'Active'
  AND m.status = 'Chief Editor Review'
  AND cer.review_id IS NULL;

CREATE VIEW vw_pending_revisions AS
SELECT
    m.manuscript_id,
    m.title,
    CONCAT(a.first_name, ' ', a.last_name) AS author_name,
    er.editorial_review_id,
    er.decision AS revision_type,
    er.reviewed_at
FROM manuscripts m
JOIN authors a ON a.author_id = m.author_id
JOIN editorial_assignment ea ON ea.manuscript_id = m.manuscript_id
JOIN editorial_review er ON er.assignment_id = ea.assignment_id
LEFT JOIN revisions r ON r.editorial_review_id = er.editorial_review_id
WHERE m.status = 'Revision Requested'
  AND er.decision IN ('Minor Revision', 'Major Revision')
  AND r.revision_id IS NULL;

CREATE VIEW vw_unread_notifications AS
SELECT
    n.notification_id,
    n.user_id,
    u.email,
    n.manuscript_id,
    n.title,
    n.message,
    n.created_at
FROM notifications n
JOIN users u ON u.user_id = n.user_id
WHERE n.is_read = FALSE;