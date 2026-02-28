import sqlite3
import secrets

# 資料庫檔案路徑
DATABASE = 'database.db'

def get_db():
    """ 建立資料庫連線 """
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row  # 讓結果可以像字典一樣存取 [cite: 40]
    return db

# ==========================================
# 使用者管理 (User Management)
# ==========================================

def insert_user(email, password, firstname, familyname, gender, city, country):
    """ 註冊新使用者 """
    try:
        db = get_db()
        db.execute("INSERT INTO users (email, password, firstname, familyname, gender, city, country) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (email, password, firstname, familyname, gender, city, country))
        db.commit()
        db.close()
        return True
    except Exception as e:
        print(f"註冊失敗: {e}")
        return False

def get_user_by_email(email):
    """ 根據 Email 獲取使用者完整資料 """
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    db.close()
    return dict(user) if user else None

def verify_user(email, password):
    """ 驗證登入帳號密碼 """
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password)).fetchone()
    db.close()
    return user is not None

def change_password(email, new_password):
    """ 修改密碼 """
    try:
        db = get_db()
        db.execute("UPDATE users SET password = ? WHERE email = ?", (new_password, email))
        db.commit()
        db.close()
        return True
    except Exception as e:
        print(f"修改密碼失敗: {e}")
        return False

# ==========================================
# 會話管理 (Session Management)
# 符合 Lab 03 要求：一個帳號只能有一個有效 Session [cite: 16, 17]
# ==========================================

def create_session(email):
    """ 建立新 Session 前先刪除該用戶舊有的所有 session"""
    remove_all_sessions_by_email(email)
    
    # 產生安全 Token，安全模組(隨機產生無法預測的亂碼)，產生十六進位字串，括弧裡面16代表token長度
    token = secrets.token_hex(16)
    try:
        db = get_db()
        db.execute("INSERT INTO sessions (token, email) VALUES (?, ?)", (token, email))
        db.commit()
        db.close()
        return token
    except Exception as e:
        print(f"建立 Session 失敗: {e}")
        return None

def remove_session(token):
    """ 登出：移除指定 Token """
    db = get_db()
    cursor = db.execute("DELETE FROM sessions WHERE token = ?", (token,))
    db.commit()
    #如果token是過期的，那麼success會是none，function回傳就會是None(false)
    success = cursor.rowcount > 0
    db.close()
    return success

def remove_all_sessions_by_email(email):
    """ 強制移除該使用者的所有會話"""
    db = get_db()
    db.execute("DELETE FROM sessions WHERE email = ?", (email,))
    db.commit()
    db.close()

def get_user_data_by_token(token):
    """ 根據 Token 找到使用者資料"""
    #打開資料庫
    db = get_db()
    # 透過 JOIN 取得使用者詳細資訊(執行SQL語法)
    user = db.execute("SELECT users.* FROM users INNER JOIN sessions ON users.email = sessions.email WHERE sessions.token = ?", (token,)).fetchone()
    db.close()
    #dict(user)是將user的資料轉翻譯成python字典格式，server.py才能轉成 JSON 格式傳給前端
    return dict(user) if user else None

# ==========================================
# 訊息管理 (Message Management)
# ==========================================

def post_message(sender_email, recipient_email, message):
    """ 在牆上留言，確保欄位名稱符合 schema.sql """
    # 如果 recipient_email 是 None，代表發在自己的牆上
    if recipient_email is None:
        recipient_email = sender_email
        
    try:
        db = get_db()
        # 欄位必須與您的資料庫 init_db.py 內容一致
        db.execute("INSERT INTO messages (sender, recipient, content) VALUES (?, ?, ?)",
                   (sender_email, recipient_email, message))
        db.commit()
        db.close()
        return True
    except Exception as e:
        print(f"張貼訊息 SQL 錯誤: {e}")
        return False

def get_user_messages_by_token(token):
    """ 獲取目前登入使用者的牆上訊息"""
    #先獲取目標人的基本資料，目的在拿到目標人的電子信箱
    user_data = get_user_data_by_token(token)
    if user_data:
        #有了目標人的電子信箱，就可以呼叫函式來獲取訊息
        return get_user_messages_by_email(user_data['email'])
    return None

def get_user_messages_by_email(email):
    """ 根據 Email 獲取該使用者的所有牆上訊息 """
    db = get_db()
    # 這裡回傳的清單，每一項都會包含 sender 欄位供前端 renderWall 使用
    messages = db.execute("SELECT * FROM messages WHERE recipient = ?", (email,)).fetchall()
    db.close()
    #把資料庫所有訊息都轉成字典格式再回傳回去，因為JSON只看得懂字典等格式
    return [dict(m) for m in messages]