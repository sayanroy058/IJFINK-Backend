-- ====================================================
-- Migration: Publication Team API workflow updates
-- Target: Existing journaldb created before publication API changes
-- Notes:
--   - Run this once on the existing database.
--   - If you recreated the DB from journaldb.sql after the publication changes,
--     this migration is not needed.
-- ====================================================

USE journaldb;

-- 1. Extend article workflow statuses.
ALTER TABLE articles
    DROP CHECK chk_articles_status;

ALTER TABLE articles
    MODIFY status ENUM(
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
    ) NOT NULL DEFAULT 'Submitted';

ALTER TABLE articles
    ADD CONSTRAINT chk_articles_status CHECK (status IN (
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
    ));

-- 2. Store final publication organization and published file metadata.
ALTER TABLE publications
    ADD COLUMN organization_name VARCHAR(255) NOT NULL AFTER publication_team_id,
    ADD COLUMN published_file_name VARCHAR(255) AFTER publication_date,
    ADD COLUMN published_file_path VARCHAR(1000) AFTER published_file_name,
    ADD COLUMN published_file_type VARCHAR(100) AFTER published_file_path;

CREATE INDEX idx_publications_organization_name ON publications(organization_name);

-- 3. Require organization submission before final publication.
DROP TRIGGER IF EXISTS trg_publications_before_insert;
DROP TRIGGER IF EXISTS trg_publications_after_insert;

DELIMITER $$

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

-- 4. Refresh the published articles view to include final publisher/file data.
DROP VIEW IF EXISTS vw_published_articles;

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
