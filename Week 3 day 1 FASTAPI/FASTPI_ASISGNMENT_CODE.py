# Exercise — PostgreSQL CRUD from PyCharm
# Create a PostgreSQL database: CREATE DATABASE library_store;
# Connect to library_store and create this table:
# CREATE TABLE books (
# book_id INT PRIMARY KEY,
# title VARCHAR(100),
# author VARCHAR(100),
# category VARCHAR(50),
# price DECIMAL(10,2),
# stock INT
# );
# That is the only preparation to do in PostgreSQL.
# Everything else should be done from PyCharm.
# Create a project: # library_crud_project
# Install: python -m pip install psycopg2-binary
# Create: main.py
# Tasks
# 1. Connect Python to PostgreSQL using psycopg2 .
import psycopg2
def get_connection():
    conn = psycopg2.connect(
        host="localhost",
        database="library_store",
        user="postgres",
        password="Admin@123"
    )
    # 2. Print: Connected to PostgreSQL successfully after the connection is established.
    print("Connected to PostgreSQL successfully")
    return conn
# Create connection
conn = get_connection()
cursor = conn.cursor()

# 3. Insert these 4 books from Python:
# 201 | Atomic Habits | James Clear | Self Help | 650 | 12
# 202 | Clean Code | Robert Martin | Technology | 900 | 8
# 203 | The Alchemist | Paulo Coelho | Fiction | 500 | 15
# 204 | Deep Work | Cal Newport | Productivity| 700 | 10
books = [
    (201, "Atomic Habits", "James Clear", "Self Help", 650, 12),
    (202, "Clean Code", "Robert Martin", "Technology", 900, 8),
    (203, "The Alchemist", "Paulo Coelho", "Fiction", 500, 15),
    (204, "Deep Work", "Cal Newport", "Productivity", 700, 10)
]

for book in books:
    cursor.execute(
        """
        INSERT INTO books
        (book_id, title, author, category, price, stock)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        book
    )

conn.commit()

print("Q3. Books inserted successfully")


# 4. Read and display all books.
print("\nQ4. All Books")
cursor.execute("SELECT * FROM books")
for row in cursor.fetchall():
    print(row)

# 5. Display only books from the Technology category.
print("\nQ5. Technology Books")
cursor.execute("""
SELECT *
FROM books
WHERE category = 'Technology'
""")
for row in cursor.fetchall():
    print(row)

# 6. Display books whose price is greater than 600 .
print("\nQ6. Books with Price > 600")

cursor.execute("""
SELECT *
FROM books
WHERE price > 600
""")

for row in cursor.fetchall():
    print(row)

# 7. Update the price of book 202 to 950 .
cursor.execute("""
UPDATE books
SET price = 950
WHERE book_id = 202
""")

conn.commit()
print("\nQ7. Price updated successfully")

# 8. Update the stock of book 204 to 14 .
cursor.execute("""
UPDATE books
SET stock = 14
WHERE book_id = 204
""")

conn.commit()
print("Q8. Stock updated successfully")

# 9. Display the updated records.
print("\nQ9. Updated Records")
cursor.execute("""
SELECT *
FROM books
""")
for row in cursor.fetchall():
    print(row)

# 10. Delete book 203 .
cursor.execute("""
DELETE FROM books
WHERE book_id = 203
""")

conn.commit()
print("\nQ10. Book 203 deleted successfully")

# 11. Display all remaining books.
print("\nQ11. Remaining Books")
cursor.execute("""
SELECT *
FROM books
""")
for row in cursor.fetchall():
    print(row)

# 12. Add one new book of your own choice.
cursor.execute(
    """
    INSERT INTO books
    (book_id, title, author, category, price, stock)
    VALUES (%s, %s, %s, %s, %s, %s)
    """,
    (
        205,
        "Rich Dad Poor Dad",
        "Robert Kiyosaki",
        "Finance",
        800,
        20
    )
)

conn.commit()
print("\nQ12. New book added successfully")

# 13. Find the book with the highest price.
print("\nQ13. Highest Price Book")

cursor.execute("""
SELECT *
FROM books
ORDER BY price DESC
LIMIT 1
""")

print(cursor.fetchone())

# 14. Find the total stock available across all books.
print("\nQ14. Total Stock")

cursor.execute("""
SELECT SUM(stock)
FROM books
""")

total_stock = cursor.fetchone()
print("Total Stock =", total_stock[0])

# 15. Count how many books exist in each category.
print("\nQ15. Books Count By Category")

cursor.execute("""
SELECT category, COUNT(*)
FROM books
GROUP BY category
""")

for row in cursor.fetchall():
    print(row)

cursor.close()
conn.close()

print("\nDatabase connection closed")