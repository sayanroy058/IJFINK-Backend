#!/usr/bin/env python3
"""
Script to seed dummy articles for testing
"""

import os
from dotenv import load_dotenv
import mysql.connector

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

def seed_articles():
    """Insert dummy articles"""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        # First, check if we have any authors
        cursor.execute("SELECT author_id FROM authors LIMIT 1")
        author = cursor.fetchone()
        
        if not author:
            print("❌ No authors found. Creating test author first...")
            
            # Create a test user first
            user_query = "INSERT INTO users (email, password_hash, role, status) VALUES (%s, %s, %s, %s)"
            cursor.execute(user_query, (
                'testauthor@example.com',
                'scrypt:32768:8:1$testpass',
                'Author',
                'Active'
            ))
            connection.commit()
            user_id = cursor.lastrowid
            
            # Create author profile
            author_query = """
                INSERT INTO authors (user_id, first_name, last_name, institution, bio, profile_image)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(author_query, (
                user_id,
                'John',
                'Doe',
                'University of Example',
                'Test author for dummy articles',
                'https://example.com/profile.jpg'
            ))
            connection.commit()
            author_id = cursor.lastrowid
            print(f"✓ Created test author with ID: {author_id}")
        else:
            author_id = author['author_id']
            print(f"✓ Using existing author with ID: {author_id}")
        
        # Dummy articles data
        articles_data = [
            {
                'title': 'Machine Learning Approaches in Healthcare',
                'abstract': 'This paper explores the application of advanced machine learning techniques in healthcare diagnostics and treatment planning.',
                'keywords': 'machine learning, healthcare, AI, deep learning',
                'article_type': 'Research Article',
                'subject_area': 'Artificial Intelligence & Medicine'
            },
            {
                'title': 'Quantum Computing: Future Applications',
                'abstract': 'A comprehensive review of quantum computing applications in solving complex optimization problems across various industries.',
                'keywords': 'quantum computing, optimization, algorithms, technology',
                'article_type': 'Review Article',
                'subject_area': 'Quantum Computing'
            },
            {
                'title': 'Sustainable Energy Solutions for Urban Development',
                'abstract': 'This research investigates innovative renewable energy solutions for sustainable urban development in developing nations.',
                'keywords': 'sustainable energy, renewable energy, urban development, climate',
                'article_type': 'Research Article',
                'subject_area': 'Renewable Energy'
            },
            {
                'title': 'Blockchain Technology in Supply Chain Management',
                'abstract': 'Analysis of blockchain implementation in supply chain transparency and security across global manufacturing networks.',
                'keywords': 'blockchain, supply chain, distributed ledger, transparency',
                'article_type': 'Case Study',
                'subject_area': 'Business Technology'
            },
            {
                'title': 'Climate Change Impact on Marine Ecosystems',
                'abstract': 'Study on the effects of rising ocean temperatures and acidification on marine biodiversity and fish populations.',
                'keywords': 'climate change, marine ecosystems, biodiversity, ocean',
                'article_type': 'Research Article',
                'subject_area': 'Environmental Science'
            },
            {
                'title': 'Neural Networks for Natural Language Processing',
                'abstract': 'Exploration of advanced neural network architectures for improved natural language understanding and generation.',
                'keywords': 'neural networks, NLP, deep learning, transformers',
                'article_type': 'Technical Paper',
                'subject_area': 'Artificial Intelligence'
            },
            {
                'title': 'Nanotechnology in Drug Delivery Systems',
                'abstract': 'Novel approaches using nanotechnology to improve drug delivery efficiency and reduce side effects in cancer treatment.',
                'keywords': 'nanotechnology, drug delivery, cancer, medical',
                'article_type': 'Research Article',
                'subject_area': 'Nanotechnology & Medicine'
            }
        ]
        
        # Insert articles
        article_query = """
            INSERT INTO articles (author_id, title, abstract, keywords, article_type, subject_area, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        inserted_articles = []
        for article in articles_data:
            try:
                cursor.execute(article_query, (
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
                inserted_articles.append(article_id)
                print(f"✓ Created article: {article['title']} (ID: {article_id})")
            except mysql.connector.Error as e:
                if "Duplicate" in str(e):
                    print(f"⚠ Article already exists: {article['title']}")
                else:
                    print(f"❌ Error inserting article: {e}")
        
        # Get total articles
        cursor.execute("SELECT COUNT(*) as count FROM articles WHERE status = 'Submitted'")
        result = cursor.fetchone()
        total = result['count']
        
        print(f"\n✓ Total pending articles: {total}")
        print(f"✓ Article IDs: {inserted_articles}")
        
        return inserted_articles
        
    except mysql.connector.Error as e:
        print(f"❌ Database error: {e}")
        return []
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("SEEDING DUMMY ARTICLES FOR TESTING")
    print("="*60 + "\n")
    
    print(f"🔗 Connecting to: {MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}\n")
    
    article_ids = seed_articles()
    
    print("\n" + "="*60)
    print("✓ Seeding completed!")
    print("="*60 + "\n")
