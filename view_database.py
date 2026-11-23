"""
Simple script to view database contents
Run: python view_database.py
"""
import sqlite3

DB_FILE = 'users.db'

def view_table(conn, table_name):
    """View a table's contents"""
    c = conn.cursor()
    try:
        c.execute(f"SELECT * FROM {table_name}")
        columns = [description[0] for description in c.description]
        rows = c.fetchall()
        
        if rows:
            print(f"\n{'='*80}")
            print(f"Table: {table_name.upper()}")
            print(f"{'='*80}")
            
            # Print headers
            header = " | ".join(f"{col:15}" for col in columns)
            print(header)
            print("-" * len(header))
            
            # Print rows
            for row in rows:
                row_str = " | ".join(f"{str(val):15}" for val in row)
                print(row_str)
            
            print(f"\nTotal rows: {len(rows)}")
        else:
            print(f"\nTable '{table_name}' is empty.")
    except Exception as e:
        print(f"Error viewing {table_name}: {e}")

def main():
    try:
        conn = sqlite3.connect(DB_FILE)
        
        print("\n" + "="*80)
        print("DATABASE VIEWER - Healthcare Prediction System")
        print("="*80)
        
        # Get all table names
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in c.fetchall()]
        
        if not tables:
            print("\nNo tables found in database.")
            return
        
        print(f"\nFound {len(tables)} table(s): {', '.join(tables)}\n")
        
        # View each table
        for table in tables:
            view_table(conn, table)
        
        # Summary statistics
        print("\n" + "="*80)
        print("SUMMARY STATISTICS")
        print("="*80)
        
        for table in tables:
            c.execute(f"SELECT COUNT(*) FROM {table}")
            count = c.fetchone()[0]
            print(f"{table}: {count} row(s)")
        
        conn.close()
        print("\n" + "="*80)
        print("Database viewing complete!")
        print("="*80 + "\n")
        
    except FileNotFoundError:
        print(f"\n❌ Database file '{DB_FILE}' not found!")
        print("Please run 'backend.py' first to create the database.\n")
    except Exception as e:
        print(f"\n❌ Error: {e}\n")

if __name__ == "__main__":
    main()

