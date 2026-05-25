import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "commodity_monitor")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

def main():
    conn_params = {
        "host": DB_HOST,
        "port": DB_PORT,
        "database": DB_NAME,
        "user": DB_USER,
        "password": DB_PASSWORD
    }
    
    print(f"Connecting to database {DB_NAME} at {DB_HOST}...")
    try:
        conn = psycopg2.connect(**conn_params)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM provinces;")
            p_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM regencies;")
            r_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM markets;")
            m_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM commodities;")
            c_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM price_history;")
            price_count = cur.fetchone()[0]
            
            print(f"Database statistics:")
            print(f"  Provinces: {p_count}")
            print(f"  Regencies: {r_count}")
            print(f"  Markets: {m_count}")
            print(f"  Commodities: {c_count}")
            print(f"  Price History Records: {price_count}")
            
            # Print a few samples if they exist
            if c_count > 0:
                cur.execute("SELECT id, name FROM commodities LIMIT 5;")
                print("\nSample Commodities:")
                for cid, name in cur.fetchall():
                    print(f"  {cid}: {name}")
                    
            if m_count > 0:
                cur.execute("SELECT id, name, regency_id FROM markets LIMIT 5;")
                print("\nSample Markets:")
                for mid, name, regency_id in cur.fetchall():
                    print(f"  {mid}: {name} (Regency: {regency_id})")
                    
        conn.close()
    except Exception as e:
        print("Error checking DB:", str(e))

if __name__ == "__main__":
    main()
