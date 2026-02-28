import sqlite3

def init_db():
    # 連接到 database.db (如果不存在會自動建立)
    connection = sqlite3.connect('database.db')
    
    with open('schema.sql', 'r') as f:
        schema = f.read()
    
    # 執行 SQL 腳本建立資料表
    connection.executescript(schema)
    connection.commit()
    connection.close()
    print("資料庫初始化成功！已建立 users, sessions, messages 資料表。")

if __name__ == '__main__':
    init_db()