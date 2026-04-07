import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# 1. إعداد الصفحة
st.set_page_config(page_title="مركز سيرفس - إدارة النظام", layout="wide")

# 2. الاتصال بقاعدة البيانات
conn = sqlite3.connect('service_center_v3.db', check_same_thread=False)
c = conn.cursor()

# 3. إنشاء الجداول الأساسية (مع توحيد أسماء الأعمدة لتجنب الأخطاء السابقة)
c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY, item_name TEXT, quantity INTEGER, price REAL)''')
c.execute('''CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY, item_name TEXT, quantity INTEGER, amount REAL, seller TEXT, date TEXT)''')
conn.commit()

# 4. إضافة الحساب الأساسي (أدمن) إذا كان الجدول فارغاً تماماً فقط
c.execute("SELECT COUNT(*) FROM users")
if c.fetchone()[0] == 0:
    c.execute("INSERT INTO users VALUES ('admin', '1234', 'مدير')")
    conn.commit()

# --- دالة تسجيل الدخول ---
if 'logged_in' not in st.session_state:
    st.title("🚗 تسجيل الدخول للمنظومة")
    with st.form("login_gate"):
        u = st.text_input("اسم المستخدم")
        p = st.text_input("كلمة المرور", type="password")
        if st.form_submit_button("دخول"):
            c.execute("SELECT role FROM users WHERE username=? AND password=?", (u, p))
            res = c.fetchone()
            if res:
                st.session_state['logged_in'] = True
                st.session_state['role'] = res[0]
                st.session_state['user'] = u
                st.rerun()
            else:
                st.error("اسم المستخدم أو كلمة المرور غير صحيحة")
else:
    st.sidebar.title(f"👤 مرحباً: {st.session_state['user']}")
    st.sidebar.info(f"الرتبة: {st.session_state['role']}")
    
    # تحديد القائمة بناءً على الصلاحيات (المدير يرى كل شيء)
    if st.session_state['role'] == 'مدير':
        menu = ["نقطة البيع", "إدارة المخزون", "التقارير المالية", "إدارة المستخدمين"]
    else:
        menu = ["نقطة البيع"] # الموظف يرى فقط البيع
    
    choice = st.sidebar.selectbox("القائمة الرئيسية", menu)

    # --- القسم 1: نقطة البيع ---
    if choice == "نقطة البيع":
        st.header("🛒 تسجيل مبيعات")
        inv_data = pd.read_sql("SELECT item_name, price, quantity FROM inventory WHERE quantity > 0", conn)
        if not inv_data.empty:
            item = st.selectbox("اختر المادة", inv_data['item_name'])
            q = st.number_input("الكمية", min_value=1, step=1)
            if st.button("تأكيد البيع"):
                price = inv_data[inv_data['item_name'] == item]['price'].values[0]
                total = q * price
                c.execute("INSERT INTO sales (item_name, quantity, amount, seller, date) VALUES (?, ?, ?, ?, ?)",
                          (item, q, total, st.session_state['user'], datetime.now().strftime("%Y-%m-%d %H:%M")))
                c.execute("UPDATE inventory SET quantity = quantity - ? WHERE item_name = ?", (q, item))
                conn.commit()
                st.success(f"تمت العملية بنجاح. المبلغ الإجمالي: {total} دينار")
        else:
            st.warning("المخزن فارغ حالياً، يرجى إضافة مواد من قبل المدير.")

    # --- القسم 2: إدارة المخزون (للمدير فقط) ---
    elif choice == "إدارة المخزون":
        st.header("📦 إضافة وتعديل المواد")
        with st.form("add_inv"):
            n = st.text_input("اسم المادة (مثال: زيت محرك)")
            qty = st.number_input("الكمية المتوفرة", min_value=1)
            pr = st.number_input("سعر البيع للقطعة", min_value=0.0)
            if st.form_submit_button("حفظ في المخزن"):
                c.execute("INSERT INTO inventory (item_name, quantity, price) VALUES (?, ?, ?)", (n, qty, pr))
                conn.commit()
                st.success(f"تم إضافة {n} للمخزن")
        
        st.subheader("جدول المواد المتوفرة")
        st.table(pd.read_sql("SELECT * FROM inventory", conn))

    # --- القسم 3: التقارير المالية (للمدير فقط) ---
    elif choice == "التقارير المالية":
        st.header("📊 كشف المبيعات الكلي")
        df_s = pd.read_sql("SELECT * FROM sales", conn)
        st.dataframe(df_s)
        if not df_s.empty:
            st.metric("إجمالي الدخل (دينار)", f"{df_s['amount'].sum()}")

    # --- القسم 4: إدارة المستخدمين (للمدير فقط) ---
    elif choice == "إدارة المستخدمين":
        st.header("👥 التحكم في حسابات الموظفين")
        with st.form("add_user"):
            new_u = st.text_input("اسم المستخدم للموظف الجديد")
            new_p = st.text_input("تعيين كلمة مرور")
            new_r = st.selectbox("تحديد الرتبة", ["موظف", "مدير"])
            if st.form_submit_button("إضافة الحساب"):
                try:
                    c.execute("INSERT INTO users VALUES (?, ?, ?)", (new_u, new_p, new_r))
                    conn.commit()
                    st.success(f"تم إنشاء حساب {new_u} برتبة {new_r}")
                except:
                    st.error("هذا الاسم مستخدم بالفعل، اختر اسماً آخر.")
        
        st.subheader("قائمة الحسابات المسجلة")
        st.table(pd.read_sql("SELECT username, role FROM users", conn))

    # زر تسجيل الخروج
    if st.sidebar.button("تسجيل الخروج"):
        del st.session_state['logged_in']
        st.rerun()
