#!/usr/bin/env python3
"""
Direct Database Update & Status Verification Script
Inserts test data and verifies status updates during screening
"""

import os
from dotenv import load_dotenv
import mysql.connector
from datetime import datetime

load_dotenv()

MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')

def get_db_connection():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )

def verify_status_updates():
    """Verify status updates in both articles and admin_screening tables"""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        print("\n" + "="*80)
        print("DATABASE STATUS VERIFICATION")
        print("="*80 + "\n")
        
        # Check articles table
        print("📋 ARTICLES TABLE - Current Status\n")
        
        articles_query = """
            SELECT 
                a.article_id,
                a.title,
                a.status,
                a.submitted_at,
                CONCAT(au.first_name, ' ', au.last_name) as author,
                CASE WHEN a_s.screening_id IS NOT NULL THEN 'YES' ELSE 'NO' END as screened
            FROM articles a
            JOIN authors au ON a.author_id = au.author_id
            LEFT JOIN admin_screening a_s ON a.article_id = a_s.article_id
            WHERE a.article_id IN (5, 6, 7, 8, 9, 10, 11, 12, 13)
            ORDER BY a.article_id DESC
        """
        
        cursor.execute(articles_query)
        articles = cursor.fetchall()
        
        if articles:
            print(f"{'ID':<5} {'Title':<40} {'Status':<20} {'Screened':<10}")
            print("-" * 80)
            for article in articles:
                title = article['title'][:37] + "..." if len(article['title']) > 40 else article['title']
                print(f"{article['article_id']:<5} {title:<40} {article['status']:<20} {article['screened']:<10}")
        else:
            print("No articles found")
        
        # Check admin_screening table
        print("\n\n📝 ADMIN_SCREENING TABLE - Screening Records\n")
        
        screening_query = """
            SELECT 
                a_s.screening_id,
                a_s.article_id,
                a_s.decision,
                a_s.remarks,
                a_s.screened_at,
                CONCAT(admin.first_name, ' ', admin.last_name) as admin_name,
                a.title,
                a.status as article_status
            FROM admin_screening a_s
            JOIN admins admin ON a_s.admin_id = admin.admin_id
            JOIN articles a ON a_s.article_id = a.article_id
            ORDER BY a_s.screened_at DESC
        """
        
        cursor.execute(screening_query)
        screenings = cursor.fetchall()
        
        if screenings:
            print(f"{'ID':<5} {'Article':<5} {'Decision':<12} {'Admin':<15} {'Article Status':<20}")
            print("-" * 80)
            for screening in screenings:
                print(f"{screening['screening_id']:<5} {screening['article_id']:<5} {screening['decision']:<12} {screening['admin_name']:<15} {screening['article_status']:<20}")
        else:
            print("No screening records found")
        
        # Summary statistics
        print("\n\n📊 SUMMARY STATISTICS\n")
        
        cursor.execute("SELECT COUNT(*) as count FROM articles WHERE status = 'Submitted'")
        submitted = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM articles WHERE status = 'Admin Approved'")
        approved = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM articles WHERE status = 'Admin Rejected'")
        rejected = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM admin_screening")
        total_screenings = cursor.fetchone()['count']
        
        print(f"Total Articles Submitted:     {submitted}")
        print(f"Total Articles Admin Approved: {approved}")
        print(f"Total Articles Admin Rejected: {rejected}")
        print(f"Total Screening Records:      {total_screenings}")
        
        # Check for status consistency
        print("\n\n✅ STATUS CONSISTENCY CHECK\n")
        
        cursor.execute("""
            SELECT 
                COUNT(*) as count,
                CASE 
                    WHEN a_s.screening_id IS NULL THEN 'Not Screened'
                    ELSE CONCAT('Screened - ', a_s.decision)
                END as screening_status
            FROM articles a
            LEFT JOIN admin_screening a_s ON a.article_id = a_s.article_id
            WHERE a.article_id IN (5, 6, 7, 8, 9, 10, 11, 12, 13)
            GROUP BY screening_status
        """)
        
        consistency = cursor.fetchall()
        for row in consistency:
            print(f"  {row['screening_status']}: {row['count']} article(s)")
        
        print("\n" + "="*80 + "\n")
        
    except mysql.connector.Error as e:
        print(f"❌ Database error: {e}")
    finally:
        cursor.close()
        connection.close()

def insert_test_articles():
    """Insert test articles directly"""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        print("\n" + "="*80)
        print("INSERTING TEST ARTICLES INTO DATABASE")
        print("="*80 + "\n")
        
        # Get existing author
        cursor.execute("SELECT author_id FROM authors LIMIT 1")
        author = cursor.fetchone()
        
        if not author:
            print("❌ No authors found. Please run seed_articles.py first.")
            return
        
        author_id = author['author_id']
        
        # Test articles for direct approval/rejection testing
        test_articles = [
            {
                'title': 'Direct Update Test Article 1 - For Approval',
                'abstract': 'This article will be approved during testing to verify status update in articles table.',
                'keywords': 'test, approval, status-update',
                'article_type': 'Research Article',
                'subject_area': 'Software Engineering'
            },
            {
                'title': 'Direct Update Test Article 2 - For Rejection',
                'abstract': 'This article will be rejected during testing to verify status update in articles table.',
                'keywords': 'test, rejection, status-update',
                'article_type': 'Research Article',
                'subject_area': 'Data Science'
            },
            {
                'title': 'Direct Update Test Article 3 - Control',
                'abstract': 'This article will remain unscreened as a control to verify no unintended changes.',
                'keywords': 'test, control, unchanged',
                'article_type': 'Review Article',
                'subject_area': 'Information Technology'
            }
        ]
        
        insert_query = """
            INSERT INTO articles (author_id, title, abstract, keywords, article_type, subject_area, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        inserted_ids = []
        for article in test_articles:
            try:
                cursor.execute(insert_query, (
                    author_id,
                    article['title'],
                    article['abstract'],
                    article['keywords'],
                    article['article_type'],
                    article['subject_area'],
                    'Submitted'
                ))
                connection.commit()
                article_id = cursor.lastrowid
                inserted_ids.append(article_id)
                print(f"✓ Inserted: {article['title']} (ID: {article_id})")
            except mysql.connector.Error as e:
                print(f"❌ Error: {e}")
        
        print(f"\n✓ Total articles inserted: {len(inserted_ids)}")
        print(f"✓ Article IDs: {inserted_ids}")
        print("\n" + "="*80 + "\n")
        
        return inserted_ids
        
    except mysql.connector.Error as e:
        print(f"❌ Database error: {e}")
        return []
    finally:
        cursor.close()
        connection.close()

def check_before_after():
    """Show before and after comparison"""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        print("\n" + "="*80)
        print("BEFORE & AFTER COMPARISON")
        print("="*80 + "\n")
        
        # Get the test articles
        cursor.execute("""
            SELECT article_id, title, status 
            FROM articles 
            WHERE title LIKE '%Direct Update Test%'
            ORDER BY article_id
        """)
        
        articles = cursor.fetchall()
        
        print("📌 Test Articles in Database:\n")
        for article in articles:
            print(f"  ID: {article['article_id']}")
            print(f"  Title: {article['title']}")
            print(f"  Current Status: {article['status']}")
            print()
        
        # Check if any have been screened
        cursor.execute("""
            SELECT 
                a.article_id,
                a.title,
                a.status,
                a_s.decision,
                a_s.screened_at
            FROM articles a
            LEFT JOIN admin_screening a_s ON a.article_id = a_s.article_id
            WHERE a.title LIKE '%Direct Update Test%'
            ORDER BY a.article_id
        """)
        
        articles_with_screening = cursor.fetchall()
        
        print("📊 Screening Status:\n")
        for article in articles_with_screening:
            if article['decision']:
                print(f"  Article {article['article_id']}: {article['decision']} ✓")
                print(f"    → Article Status: {article['status']}")
                print(f"    → Screened At: {article['screened_at']}")
            else:
                print(f"  Article {article['article_id']}: Not Screened")
                print(f"    → Status: {article['status']}")
            print()
        
        print("="*80 + "\n")
        
    except mysql.connector.Error as e:
        print(f"❌ Database error: {e}")
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    print(f"\n🔗 Connecting to: {MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}\n")
    
    # Step 1: Insert test articles
    print("STEP 1: INSERT TEST ARTICLES")
    inserted_ids = insert_test_articles()
    
    if inserted_ids:
        print(f"✓ Successfully inserted test articles: {inserted_ids}")
        print("\n📌 Next Steps:")
        print("   1. Run test_screening_api.py to approve/reject articles")
        print(f"   2. Use article IDs: {inserted_ids} for testing")
        print("   3. After testing, run this script again to verify status updates")
    
    # Step 2: Check before/after
    print("\nSTEP 2: CHECKING DATABASE STATUS")
    check_before_after()
    
    # Step 3: Verify status
    print("STEP 3: COMPLETE STATUS VERIFICATION")
    verify_status_updates()
