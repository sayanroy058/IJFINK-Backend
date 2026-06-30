-- ====================================================
-- Journal Publication Management System Database
-- MySQL 8.0
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
    title VARCHAR(20),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    bio TEXT,
    profile_image VARCHAR(1000),
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
) ENGINE=InnoDB COMMENT='Author profile data; one author profile belongs to one authentication user. The optional title field stores honorifics such as Mr., Mrs., Dr., or Prof. Bio and profile image fields support author profiles for publication display.';

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

-- Table: articles
-- Purpose: Stores article metadata and current workflow status.
CREATE TABLE articles (
    article_id INT AUTO_INCREMENT PRIMARY KEY,
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
        'Publication Review',
        'Submitted To Organization',
        'Rejected',
        'Published'
    ) NOT NULL DEFAULT 'Submitted',
    submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT chk_articles_status CHECK (status IN (
        'Submitted',
        'Admin Approved',
        'Admin Rejected',
        'Chief Editor Review',
        'Editorial Review',
        'Revision Requested',
        'Accepted',
        'Publication Review',
        'Submitted To Organization',
        'Rejected',
        'Published'
    )),
    CONSTRAINT fk_articles_author
        FOREIGN KEY (author_id) REFERENCES authors(author_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Submitted article records with normalized author ownership and workflow state.';

-- Table: co_authors
-- Purpose: Stores article co-author details in ordered form.
CREATE TABLE co_authors (
    co_author_id INT AUTO_INCREMENT PRIMARY KEY,
    article_id INT NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    email VARCHAR(255) NOT NULL,
    institution VARCHAR(255) NOT NULL,
    orcid VARCHAR(19),
    author_order INT NOT NULL,
    CONSTRAINT uq_co_authors_order UNIQUE (article_id, author_order),
    CONSTRAINT uq_co_authors_email_per_article UNIQUE (article_id, email),
    CONSTRAINT chk_co_authors_email_format CHECK (email LIKE '%_@_%._%'),
    CONSTRAINT chk_co_authors_author_order CHECK (author_order >= 1),
    CONSTRAINT chk_co_authors_orcid_format CHECK (orcid IS NULL OR orcid REGEXP '^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$'),
    CONSTRAINT fk_co_authors_article
        FOREIGN KEY (article_id) REFERENCES articles(article_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Ordered co-author list for each article.';

-- Table: article_files
-- Purpose: Stores uploaded article files and generated screening reports.
CREATE TABLE article_files (
    file_id INT AUTO_INCREMENT PRIMARY KEY,
    article_id INT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_type ENUM(
        'Main Manuscript',
        'Editable Manuscript',
        'Video Abstract',
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
    CONSTRAINT uq_article_files_article_type_version UNIQUE (article_id, file_type, version),
    CONSTRAINT chk_article_files_type CHECK (file_type IN (
        'Main Manuscript',
        'Editable Manuscript',
        'Video Abstract',
        'Cover Letter',
        'Copyright Form',
        'Figures',
        'Supplementary File',
        'Plagiarism Report',
        'AI Detection Report',
        'Revision File'
    )),
    CONSTRAINT chk_article_files_version CHECK (version >= 1),
    CONSTRAINT fk_article_files_article
        FOREIGN KEY (article_id) REFERENCES articles(article_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='All article-related uploads and screening report files.';

-- Table: admin_screening`r`n-- Purpose: Stores the initial administrative screening decision.
CREATE TABLE admin_screening (
    screening_id INT AUTO_INCREMENT PRIMARY KEY,
    article_id INT NOT NULL,
    admin_id INT NOT NULL,
    decision ENUM('Approved', 'Rejected') NOT NULL,
    remarks TEXT,
    screened_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_admin_screening_article UNIQUE (article_id),
    CONSTRAINT chk_admin_screening_decision CHECK (decision IN ('Approved', 'Rejected')),
    CONSTRAINT fk_admin_screening_article
        FOREIGN KEY (article_id) REFERENCES articles(article_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_admin_screening_admin
        FOREIGN KEY (admin_id) REFERENCES admins(admin_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='One initial screening record per Article, performed by an admin.';

-- Table: editorial_assignment
-- Purpose: Stores editor assignments made by admins. Only one active assignment is allowed per Article.
CREATE TABLE editorial_assignment (
    assignment_id INT AUTO_INCREMENT PRIMARY KEY,
    article_id INT NOT NULL,
    admin_id INT NOT NULL,
    editor_id INT NOT NULL,
    assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status ENUM('Active', 'Completed', 'Cancelled') NOT NULL DEFAULT 'Active',
    CONSTRAINT chk_editorial_assignment_status CHECK (status IN ('Active', 'Completed', 'Cancelled')),
    CONSTRAINT fk_editorial_assignment_article
        FOREIGN KEY (article_id) REFERENCES articles(article_id)
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
    article_id INT NOT NULL,
    editorial_review_id INT NOT NULL,
    author_id INT NOT NULL,
    revision_number INT NOT NULL,
    response_letter TEXT NOT NULL,
    submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_revisions_article_number UNIQUE (article_id, revision_number),
    CONSTRAINT chk_revisions_number CHECK (revision_number >= 1),
    CONSTRAINT fk_revisions_article
        FOREIGN KEY (article_id) REFERENCES articles(article_id)
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
    article_id INT NOT NULL,
    publication_team_id INT NOT NULL,
    organization_name VARCHAR(255) NOT NULL,
    doi VARCHAR(255) NOT NULL,
    article_url VARCHAR(700) NOT NULL,
    volume VARCHAR(50) NOT NULL,
    issue VARCHAR(50) NOT NULL,
    pages VARCHAR(50) NOT NULL,
    publication_date DATE NOT NULL,
    published_file_name VARCHAR(255),
    published_file_path VARCHAR(1000),
    published_file_type VARCHAR(100),
    CONSTRAINT uq_publications_article UNIQUE (article_id),
    CONSTRAINT uq_publications_doi UNIQUE (doi),
    CONSTRAINT uq_publications_article_url UNIQUE (article_url),
    CONSTRAINT chk_publications_doi_format CHECK (doi LIKE '10.%/%'),
    CONSTRAINT fk_publications_article
        FOREIGN KEY (article_id) REFERENCES articles(article_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT fk_publications_publication_team
        FOREIGN KEY (publication_team_id) REFERENCES publication_team(publication_team_id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='Final publication records with unique DOI and article URL.';

-- Table: notifications
-- Purpose: Stores workflow notifications sent to users for Article events.
CREATE TABLE notifications (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    article_id INT,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notifications_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_notifications_article
        FOREIGN KEY (article_id) REFERENCES articles(article_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='User notifications generated during Article workflow transitions.';

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
-- Seed Data
-- ====================================================

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


-- ====================================================
-- Indexes
-- ====================================================

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_status ON users(status);

CREATE INDEX idx_authors_user_id ON authors(user_id);

CREATE INDEX idx_articles_author_id ON articles(author_id);
CREATE INDEX idx_articles_status ON articles(status);

CREATE INDEX idx_co_authors_article_id ON co_authors(article_id);
CREATE INDEX idx_article_files_article_id ON article_files(article_id);

CREATE INDEX idx_admin_screening_article_id ON admin_screening(article_id);
CREATE INDEX idx_admin_screening_admin_id ON admin_screening(admin_id);

CREATE INDEX idx_editorial_assignment_article_id ON editorial_assignment(article_id);
CREATE INDEX idx_editorial_assignment_admin_id ON editorial_assignment(admin_id);
CREATE INDEX idx_editorial_assignment_editor_id ON editorial_assignment(editor_id);
CREATE INDEX idx_editorial_assignment_status ON editorial_assignment(status);

CREATE INDEX idx_chief_editor_review_assignment_id ON chief_editor_review(assignment_id);
CREATE INDEX idx_chief_editor_review_chief_editor_id ON chief_editor_review(chief_editor_id);

CREATE INDEX idx_editorial_review_assignment_id ON editorial_review(assignment_id);
CREATE INDEX idx_editorial_review_editor_id ON editorial_review(editor_id);

CREATE INDEX idx_revisions_article_id ON revisions(article_id);
CREATE INDEX idx_revisions_author_id ON revisions(author_id);

CREATE INDEX idx_publications_article_id ON publications(article_id);
CREATE INDEX idx_publications_publication_team_id ON publications(publication_team_id);
CREATE INDEX idx_publications_organization_name ON publications(organization_name);
CREATE INDEX idx_publications_publication_date ON publications(publication_date);
CREATE INDEX idx_publications_doi ON publications(doi);
CREATE INDEX idx_publications_article_url ON publications(article_url(191));

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_article_id ON notifications(article_id);
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

CREATE TRIGGER trg_articles_set_updated_at
BEFORE UPDATE ON articles
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

CREATE TRIGGER trg_articles_after_insert_notify
AFTER INSERT ON articles
FOR EACH ROW
BEGIN
    INSERT INTO notifications (user_id, article_id, title, message)
    SELECT a.user_id, NEW.article_id, 'Submission Received',
           CONCAT('Your Article "', NEW.title, '" has been received.')
    FROM authors a
    WHERE a.author_id = NEW.author_id;
END$$

CREATE TRIGGER trg_admin_screening_after_insert
AFTER INSERT ON admin_screening
FOR EACH ROW
BEGIN
    IF NEW.decision = 'Approved' THEN
        UPDATE articles
        SET status = 'Admin Approved'
        WHERE article_id = NEW.article_id;

        INSERT INTO notifications (user_id, article_id, title, message)
        SELECT a.user_id, NEW.article_id, 'Admin Approved',
               'Your Article passed initial administrative screening.'
        FROM articles m
        JOIN authors a ON a.author_id = m.author_id
        WHERE m.article_id = NEW.article_id;
    ELSE
        UPDATE articles
        SET status = 'Admin Rejected'
        WHERE article_id = NEW.article_id;

        INSERT INTO notifications (user_id, article_id, title, message)
        SELECT a.user_id, NEW.article_id, 'Admin Rejected',
               'Your Article did not pass initial administrative screening.'
        FROM articles m
        JOIN authors a ON a.author_id = m.author_id
        WHERE m.article_id = NEW.article_id;
    END IF;
END$$

CREATE TRIGGER trg_editorial_assignment_before_insert
BEFORE INSERT ON editorial_assignment
FOR EACH ROW
BEGIN
    IF (SELECT status FROM articles WHERE article_id = NEW.article_id) <> 'Admin Approved' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'An editor can be assigned only after admin approval';
    END IF;

    IF NEW.status = 'Active'
        AND EXISTS (
            SELECT 1
            FROM editorial_assignment
            WHERE article_id = NEW.article_id
              AND status = 'Active'
        ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Only one active editorial assignment is allowed per Article';
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
            WHERE article_id = NEW.article_id
              AND status = 'Active'
              AND assignment_id <> OLD.assignment_id
        ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Only one active editorial assignment is allowed per Article';
    END IF;
END$$

CREATE TRIGGER trg_editorial_assignment_after_insert
AFTER INSERT ON editorial_assignment
FOR EACH ROW
BEGIN
    UPDATE articles
    SET status = 'Chief Editor Review'
    WHERE article_id = NEW.article_id;
END$$

CREATE TRIGGER trg_chief_editor_review_before_insert
BEFORE INSERT ON chief_editor_review
FOR EACH ROW
BEGIN
    DECLARE v_article_id INT;

    IF NOT EXISTS (
        SELECT 1 FROM editors
        WHERE editor_id = NEW.chief_editor_id
          AND is_chief_editor = TRUE
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'chief_editor_id must reference an editor marked as chief editor';
    END IF;

    SELECT article_id
    INTO v_article_id
    FROM editorial_assignment
    WHERE assignment_id = NEW.assignment_id;

    IF NEW.decision = 'Approved' AND NEW.file_check_status <> 'Passed' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Chief editor approval requires passed file checks';
    END IF;

    IF NEW.decision = 'Approved' AND (
        NOT EXISTS (SELECT 1 FROM article_files WHERE article_id = v_article_id AND file_type = 'Main Manuscript')
        OR NOT EXISTS (SELECT 1 FROM article_files WHERE article_id = v_article_id AND file_type = 'Plagiarism Report')
        OR NOT EXISTS (SELECT 1 FROM article_files WHERE article_id = v_article_id AND file_type = 'AI Detection Report')
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Chief editor approval requires Article, plagiarism report, and AI detection report files';
    END IF;
END$$

CREATE TRIGGER trg_chief_editor_review_after_insert
AFTER INSERT ON chief_editor_review
FOR EACH ROW
BEGIN
    DECLARE v_article_id INT;

    SELECT article_id
    INTO v_article_id
    FROM editorial_assignment
    WHERE assignment_id = NEW.assignment_id;

    IF NEW.decision = 'Approved' THEN
        UPDATE articles
        SET status = 'Editorial Review'
        WHERE article_id = v_article_id;
    ELSEIF NEW.decision = 'Return to Author' THEN
        UPDATE articles
        SET status = 'Revision Requested'
        WHERE article_id = v_article_id;

        INSERT INTO notifications (user_id, article_id, title, message)
        SELECT a.user_id, v_article_id, 'Chief Editor Returned Paper',
               'The chief editor returned your Article for correction before editorial review.'
        FROM articles m
        JOIN authors a ON a.author_id = m.author_id
        WHERE m.article_id = v_article_id;
    ELSE
        UPDATE articles
        SET status = 'Rejected'
        WHERE article_id = v_article_id;

        INSERT INTO notifications (user_id, article_id, title, message)
        SELECT a.user_id, v_article_id, 'Rejected',
               'Your Article was rejected during chief editor verification.'
        FROM articles m
        JOIN authors a ON a.author_id = m.author_id
        WHERE m.article_id = v_article_id;
    END IF;
END$$

CREATE TRIGGER trg_editorial_review_before_insert
BEFORE INSERT ON editorial_review
FOR EACH ROW
BEGIN
    DECLARE v_assignment_editor_id INT;
    DECLARE v_article_status VARCHAR(50);

    SELECT ea.editor_id, m.status
    INTO v_assignment_editor_id, v_article_status
    FROM editorial_assignment ea
    JOIN articles m ON m.article_id = ea.article_id
    WHERE ea.assignment_id = NEW.assignment_id;

    IF NEW.editor_id <> v_assignment_editor_id THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Editorial review must be performed by the assigned editor';
    END IF;

    IF v_article_status NOT IN ('Editorial Review', 'Revision Requested') THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Editorial review is allowed only during editorial review or revision workflow';
    END IF;
END$$

CREATE TRIGGER trg_editorial_review_after_insert
AFTER INSERT ON editorial_review
FOR EACH ROW
BEGIN
    DECLARE v_article_id INT;

    SELECT article_id
    INTO v_article_id
    FROM editorial_assignment
    WHERE assignment_id = NEW.assignment_id;

    IF NEW.decision = 'Accepted' THEN
        UPDATE articles
        SET status = 'Accepted'
        WHERE article_id = v_article_id;

        UPDATE editorial_assignment
        SET status = 'Completed'
        WHERE assignment_id = NEW.assignment_id;

        INSERT INTO notifications (user_id, article_id, title, message)
        SELECT a.user_id, v_article_id, 'Accepted',
               'Your Article has been accepted for publication.'
        FROM articles m
        JOIN authors a ON a.author_id = m.author_id
        WHERE m.article_id = v_article_id;
    ELSEIF NEW.decision IN ('Minor Revision', 'Major Revision') THEN
        UPDATE articles
        SET status = 'Revision Requested'
        WHERE article_id = v_article_id;

        INSERT INTO notifications (user_id, article_id, title, message)
        SELECT a.user_id, v_article_id, 'Revision Requested',
               CONCAT('Your Article requires ', NEW.decision, '.')
        FROM articles m
        JOIN authors a ON a.author_id = m.author_id
        WHERE m.article_id = v_article_id;
    ELSE
        UPDATE articles
        SET status = 'Rejected'
        WHERE article_id = v_article_id;

        UPDATE editorial_assignment
        SET status = 'Completed'
        WHERE assignment_id = NEW.assignment_id;

        INSERT INTO notifications (user_id, article_id, title, message)
        SELECT a.user_id, v_article_id, 'Rejected',
               'Your Article was rejected after editorial review.'
        FROM articles m
        JOIN authors a ON a.author_id = m.author_id
        WHERE m.article_id = v_article_id;
    END IF;
END$$

CREATE TRIGGER trg_revisions_before_insert
BEFORE INSERT ON revisions
FOR EACH ROW
BEGIN
    DECLARE v_review_decision VARCHAR(50);
    DECLARE v_review_article_id INT;

    SELECT er.decision, ea.article_id
    INTO v_review_decision, v_review_article_id
    FROM editorial_review er
    JOIN editorial_assignment ea ON ea.assignment_id = er.assignment_id
    WHERE er.editorial_review_id = NEW.editorial_review_id;

    IF v_review_decision NOT IN ('Minor Revision', 'Major Revision') THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'A revision can be submitted only after a minor or major revision decision';
    END IF;

    IF NEW.article_id <> v_review_article_id THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Revision Article must match the editorial review assignment Article';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM articles
        WHERE article_id = NEW.article_id
          AND author_id = NEW.author_id
    ) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Revision author must be the Article owner';
    END IF;
END$$

CREATE TRIGGER trg_revisions_after_insert
AFTER INSERT ON revisions
FOR EACH ROW
BEGIN
    UPDATE articles
    SET status = 'Editorial Review'
    WHERE article_id = NEW.article_id;
END$$

CREATE TRIGGER trg_publications_before_insert
BEFORE INSERT ON publications
FOR EACH ROW
BEGIN
    IF (SELECT status FROM articles WHERE article_id = NEW.article_id) <> 'Submitted To Organization' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Only articles submitted to an organization can be published';
    END IF;
END$$

CREATE TRIGGER trg_publications_after_insert
AFTER INSERT ON publications
FOR EACH ROW
BEGIN
    UPDATE articles
    SET status = 'Published'
    WHERE article_id = NEW.article_id;

    INSERT INTO notifications (user_id, article_id, title, message)
    SELECT a.user_id, NEW.article_id, 'Published',
           CONCAT('Your article has been published with DOI ', NEW.doi, '.')
    FROM articles m
    JOIN authors a ON a.author_id = m.author_id
    WHERE m.article_id = NEW.article_id;
END$$

DELIMITER ;

-- ====================================================
-- Views
-- ====================================================

CREATE VIEW vw_current_article_status AS
SELECT
    m.article_id,
    m.title,
    TRIM(CONCAT_WS(' ', a.title, a.first_name, a.last_name)) AS author_name,
    u.email AS author_email,
    m.article_type,
    m.subject_area,
    m.status,
    m.submitted_at,
    m.updated_at
FROM articles m
JOIN authors a ON a.author_id = m.author_id
JOIN users u ON u.user_id = a.user_id;

CREATE VIEW vw_published_articles AS
SELECT
    p.publication_id,
    m.article_id,
    m.title,
    TRIM(CONCAT_WS(' ', a.title, a.first_name, a.last_name)) AS author_name,
    p.organization_name,
    p.doi,
    p.article_url,
    p.volume,
    p.issue,
    p.pages,
    p.publication_date,
    p.published_file_name,
    p.published_file_path,
    p.published_file_type
FROM publications p
JOIN articles m ON m.article_id = p.article_id
JOIN authors a ON a.author_id = m.author_id;

CREATE VIEW vw_pending_editorial_assignments AS
SELECT
    m.article_id,
    m.title,
    m.status,
    s.screened_at,
    CONCAT(ad.first_name, ' ', ad.last_name) AS screened_by
FROM articles m
JOIN admin_screening s ON s.article_id = m.article_id
JOIN admins ad ON ad.admin_id = s.admin_id
LEFT JOIN editorial_assignment ea
    ON ea.article_id = m.article_id
   AND ea.status = 'Active'
WHERE m.status = 'Admin Approved'
  AND ea.assignment_id IS NULL;

CREATE VIEW vw_pending_chief_editor_reviews AS
SELECT
    ea.assignment_id,
    m.article_id,
    m.title,
    CONCAT(e.first_name, ' ', e.last_name) AS assigned_editor,
    ea.assigned_at
FROM editorial_assignment ea
JOIN articles m ON m.article_id = ea.article_id
JOIN editors e ON e.editor_id = ea.editor_id
LEFT JOIN chief_editor_review cer ON cer.assignment_id = ea.assignment_id
WHERE ea.status = 'Active'
  AND m.status = 'Chief Editor Review'
  AND cer.review_id IS NULL;

CREATE VIEW vw_pending_revisions AS
SELECT
    m.article_id,
    m.title,
    TRIM(CONCAT_WS(' ', a.title, a.first_name, a.last_name)) AS author_name,
    er.editorial_review_id,
    er.decision AS revision_type,
    er.reviewed_at
FROM articles m
JOIN authors a ON a.author_id = m.author_id
JOIN editorial_assignment ea ON ea.article_id = m.article_id
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
    n.article_id,
    n.title,
    n.message,
    n.created_at
FROM notifications n
JOIN users u ON u.user_id = n.user_id
WHERE n.is_read = FALSE;
