import sqlite3

def remove_duplicate_submissions():
    conn = sqlite3.connect('popquiz.db')
    cursor = conn.cursor()
    
    try:
        # Find and delete duplicate submissions, keeping only the latest one for each student-quiz pair
        cursor.execute('''
            DELETE FROM quiz_submissions
            WHERE id NOT IN (
                SELECT MAX(id)
                FROM quiz_submissions
                GROUP BY quiz_id, student_id
            )
        ''')
        
        deleted_count = cursor.rowcount
        conn.commit()
        print(f"Removed {deleted_count} duplicate submissions")
        
        # Show remaining submissions
        cursor.execute('SELECT COUNT(*) FROM quiz_submissions')
        total = cursor.fetchone()[0]
        print(f"Total submissions remaining: {total}")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    remove_duplicate_submissions()
