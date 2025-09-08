import sqlite3, time, random

def main():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS ticks(symbol TEXT, epoch INTEGER, price REAL)")
    now = int(time.time())
    for i in range(300):
        c.execute("INSERT INTO ticks VALUES(?,?,?)", ("R_100", now + i, 100 + random.random()))
    conn.commit()
    conn.close()
    print("seeded")

if __name__ == "__main__":
    main()
