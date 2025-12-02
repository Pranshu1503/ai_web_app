import sqlite3

conn = sqlite3.connect('popquiz.db')
cursor = conn.cursor()

print("=== Current Users ===")
cursor.execute('SELECT id, email, is_verified, role FROM users')
users = cursor.fetchall()

if not users:
    print("No users found in database")
else:
    for user in users:
        print(f"ID: {user[0]}, Email: {user[1]}, Verified: {user[2]}, Role: {user[3]}")

print("\n=== Options ===")
print("1. Delete specific user")
print("2. Delete all users")
print("3. Verify specific user")
print("4. Exit")

choice = input("\nEnter choice (1-4): ")

if choice == "1":
    email = input("Enter email to delete: ")
    cursor.execute('DELETE FROM users WHERE email = ?', (email,))
    conn.commit()
    print(f"Deleted user: {email}")
elif choice == "2":
    confirm = input("Are you sure you want to delete ALL users? (yes/no): ")
    if confirm.lower() == 'yes':
        cursor.execute('DELETE FROM users')
        cursor.execute('DELETE FROM verification_tokens')
        cursor.execute('DELETE FROM sessions')
        conn.commit()
        print("All users deleted")
elif choice == "3":
    email = input("Enter email to verify: ")
    cursor.execute('UPDATE users SET is_verified = 1 WHERE email = ?', (email,))
    conn.commit()
    print(f"Verified user: {email}")

conn.close()
