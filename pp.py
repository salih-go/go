import streamlit as st
import json
from streamlit_option_menu import option_menu
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
from concurrent.futures import ThreadPoolExecutor

# إعداد Google Sheets API باستخدام Streamlit Secrets
def get_gspread_client():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    return client

def get_sheet():
    client = get_gspread_client()
    spreadsheet = client.open("MyTestSheet")
    sheet = spreadsheet.sheet1
    return sheet

# تحميل البيانات مع التخزين المؤقت
@st.cache_data(ttl=600)  # التخزين المؤقت لمدة 10 دقائق
def load_data():
    sheet = get_sheet()
    data = sheet.get_all_records()
    return data if isinstance(data, list) else []

def save_data_to_gsheet(data):
    sheet = get_sheet()
    if isinstance(data, list):
        sheet.clear()
        sheet.insert_row(list(data[0].keys()), 1)  # Add header
        for i, row in enumerate(data, start=2):
            sheet.insert_row(list(row.values()), i)

executor = ThreadPoolExecutor(max_workers=5)

def save_data(new_data):
    if 'all_data' not in st.session_state:
        st.session_state.all_data = load_data()
    st.session_state.all_data.insert(0, new_data)
    executor.submit(save_data_to_gsheet, st.session_state.all_data)

def update_order_status(index, new_status):
    st.session_state.all_data[index]['status'] = new_status
    executor.submit(save_data_to_gsheet, st.session_state.all_data)

def delete_order(index):
    del st.session_state.all_data[index]
    executor.submit(save_data_to_gsheet, st.session_state.all_data)

# تنسيق الطلبات باستخدام HTML و CSS
def format_order(data, index):
    formatted_number = "{:,.0f}".format(float(data.get('number', 0))).replace(',', '.')
    background_color = "#d4edda" if data.get('status') == 'Completed' else "#f8d7da"
    if data.get('status') == 'Delivered':
        background_color = "#cce5ff"
    status_color = "green" if data.get('status') == 'Completed' else "red"
    if data.get('status') == 'Delivered':
        status_color = "blue"
    return f"""
    <div style="border-radius: 8px; padding: 16px; margin-bottom: 10px; background-color: #fff; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">
        <div style="display: flex; flex-direction: column; align-items: flex-start;">
            <div style="font-weight: bold; font-size: 1.2em;">{data.get('hello', 'N/A')}</div>
            <div style="color: gray;">{data.get('region', 'N/A')}</div>
            <div style="margin: 8px 0;">
                <span style="background-color: {background_color}; padding: 4px 8px; border-radius: 4px; color: {status_color};"><strong>{data.get('status', 'N/A')}</strong></span>
                <span style="background-color: #f0f0f0; padding: 4px 8px; border-radius: 4px; margin-left: 8px;">Order #: {index+1}</span>
            </div>
            <div style="color: gray;">{data.get('phone', 'N/A')}</div>
        </div>
    </div>
    """

def format_order_details(data):
    formatted_number = "{:,.0f}".format(float(data.get('number', 0))).replace(',', '.')
    return f"""
    <div style="border-radius: 8px; padding: 16px; background-color: #fff; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">
        <p><strong>Name:</strong> {data.get('hello', 'N/A')}</p>
        <p><strong>Phone Number:</strong> {data.get('phone', 'N/A')}</p>
        <p><strong>City:</strong> {data.get('city', 'N/A')}</p>
        <p><strong>Region:</strong> {data.get('region', 'N/A')}</p>
        <p><strong>Price:</strong> {formatted_number}</p>
        <p><strong>Type:</strong> {data.get('kind', 'N/A')}</p>
        <p><strong>Total:</strong> {data.get('total', 'N/A')}</p>
        <p><strong>More Information:</strong> {data.get('more', 'N/A')}</p>
        <p><strong>Status:</strong> {data.get('status', 'N/A')}</p>
    </div>
    """

# إدارة الموظفين
def load_employees():
    try:
        with open('employees.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_employees(employees):
    with open('employees.json', 'w') as f:
        json.dump(employees, f)

def get_current_device():
    import socket
    return socket.gethostname()

employees = load_employees()

# إعادة تعيين حساب المدير إذا تم حذفه
if 'admin' not in employees:
    employees['admin'] = {'code': 'admin123', 'is_manager': True, 'devices': [], 'permissions': {'Settings': True, 'Home': True, 'Orders': True, 'Search': True, 'Dashboard': True}}
    save_employees(employees)
    st.info("Default admin account created. Username: 'admin', Password: 'admin123'")

# إضافة صفحة جديدة للموظفين
if 'is_authenticated' not in st.session_state:
    st.session_state.is_authenticated = False
    st.session_state.is_manager = False
    st.session_state.current_user = None

if not st.session_state.is_authenticated:
    username = st.text_input("Enter your username")
    code = st.text_input("Enter your access code", type='password')
    if st.button("Login"):
        if username in employees and employees[username]['code'] == code:
            st.session_state.is_authenticated = True
            st.session_state.is_manager = employees[username].get('is_manager', False)
            st.session_state.current_user = username
            st.success("Login successful")
        else:
            st.error("Invalid username or code")
    st.stop()

# التحقق من الصلاحيات
current_user_permissions = employees[st.session_state.current_user].get('permissions', {})

def check_permission(page):
    return current_user_permissions.get(page, False)  # Assume False if permission key is missing

# عرض القائمة بعد التحقق
available_pages = ["Home", "Orders", "Search", "Dashboard", "Settings"]
selected = option_menu(
    menu_title="Menu",
    options=[page for page in available_pages if check_permission(page)],
    icons=["house", "clipboard", "search", "graph-up", "gear"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal"
)

if selected == "Home" and check_permission('Home'):
    hello, phone = st.text_input("THE NAME"), st.text_input("Phone Number")
    city = st.selectbox("Select City", ["بغداد", "البصرة", "نينوى", "الانبار", "ديالى", "كربلاء", "بابل", "واسط", "صلاح الدين", "القادسيه", "ذي قار", "المثنى", "ميسان", "السليمانية", "دهوك", "اربيل", "كركوك", "النجف", "الموصل", "حلبجة"])
    region, kind = st.text_input("Enter the Region"), st.selectbox("type of prodact", ["smart watch", "airtag"])
    number, total = st.number_input('price', min_value=0.0, max_value=500000.0, value=25000.0, step=5000.0, format='%0.0f'), st.number_input('total', min_value=0, max_value=100, value=1, step=1)
    more = st.text_area("Type here for more information")

    if st.button("Save Data"):
        with st.spinner("Saving data..."):
            # إعداد Google Sheets API فقط عند الضغط على زر "Save Data"
            new_data = {'hello': hello, 'phone': phone, 'city': city, 'region': region, 'more': more, 'number': number, 'kind': kind, 'total': total, 'status': 'Pending', 'date': datetime.today().strftime('%Y-%m-%d')}
            save_data(new_data)
            st.success("Data saved successfully!")

# تحميل البيانات من session_state إذا كانت متاحة
if "all_data" not in st.session_state:
    st.session_state.all_data = load_data()

if selected == "Orders" and check_permission('Orders'):
    st.write("Loading orders...")
    all_data = st.session_state.all_data

    for i, data in enumerate(all_data):
        st.markdown(format_order(data, i), unsafe_allow_html=True)
        with st.expander(f"View Details for Order {i+1}"):
            st.markdown(format_order_details(data), unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 1, 1])
            if col1.button(f"Toggle Status {i+1}", key=f"toggle_button_{i}"):
                new_status = 'Pending' if data.get('status') == 'Completed' else 'Completed'
                update_order_status(i, new_status)
                st.session_state.all_data[i]['status'] = new_status
                st.experimental_rerun()
            if col2.button(f"Mark as Delivered {i+1}", key=f"deliver_button_{i}"):
                update_order_status(i, 'Delivered')
                st.session_state.all_data[i]['status'] = 'Delivered'
                st.experimental_rerun()
            if col3.button(f"Delete Entry {i+1}", key=f"delete_button_{i}"):
                delete_order(i)
                st.experimental_rerun()
            st.write("---")

elif selected == "Search" and check_permission('Search'):
    st.title("Search")
    if "search_query" not in st.session_state:
        st.session_state.search_query = ""
    search_query = st.text_input("Search by phone number or name", key="search_input")
    col1, col2 = st.columns([1, 1])
    if col1.button("Search"):
        st.session_state.search_query = search_query.lower()
    if col2.button("Clear Search"):
        st.session_state.search_query = ""

    if st.session_state.search_query:
        all_data = st.session_state.all_data
        filtered_data = [entry for entry in all_data if st.session_state.search_query in str(entry.get('phone', '')).lower() or st.session_state.search_query in str(entry.get('hello', '')).lower()]
        if filtered_data:
            for i, data in enumerate(filtered_data):
                st.markdown(format_order(data, i), unsafe_allow_html=True)
                with st.expander(f"View Details for Order {i+1}"):
                    st.markdown(format_order_details(data), unsafe_allow_html=True)
                    col1, col2, col3 = st.columns([1, 1, 1])
                    if col1.button(f"Toggle Status {i+1}", key=f"toggle_button_search_{i}"):
                        new_status = 'Pending' if data.get('status') == 'Completed' else 'Completed'
                        update_order_status(i, new_status)
                        st.session_state.all_data[i]['status'] = new_status
                        st.experimental_rerun()
                    if col2.button(f"Mark as Delivered {i+1}", key=f"deliver_button_search_{i}"):
                        update_order_status(i, 'Delivered')
                        st.session_state.all_data[i]['status'] = 'Delivered'
                        st.experimental_rerun()
                    if col3.button(f"Delete Entry {i+1}", key=f"delete_button_search_{i}"):
                        delete_order(i)
                        st.experimental_rerun()
        else:
            st.write("No entries found with your search criteria.")

elif selected == "Dashboard" and check_permission('Dashboard'):
    # وظيفة لرسم دائرة مع خلفية بيضاء
    def draw_circle(value, label, color="#1E90FF", max_value=100):
        percentage = min(100, max(0, (value / max_value) * 100))
        angle = (percentage / 100) * 360
        with st.container():
            st.markdown(f"""
            <div style="display: flex; flex-direction: column; align-items: center; background-color: white; padding: 5px; border-radius: 40px; box-shadow: 0 0 100px rgba(0,0,0,0.1); margin-bottom: 50px;">
                <svg viewBox="0 0 36 36" width="150" height="150">
                    <path d="M18 2.0845
                             a 15.9155 15.9155 0 0 1 0 31.831
                             a 15.9155 15.9155 0 0 1 0 -31.831"
                          fill="none"
                          stroke="#eeeeee"
                          stroke-width="3"
                          stroke-linecap="round"></path>
                    <path d="M18 2.0845
                             a 15.9155 15.9155 0 0 1 0 31.831"
                          fill="none"
                          stroke="{color}"
                          stroke-width="4"
                          stroke-linecap="round"
                          stroke-dasharray="{angle}, 100"></path>
                    <text x="18" y="20.35" font-size="8" text-anchor="middle" fill="#333">{value}</text>
                </svg>
                <div style="margin-top: 10px;">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    # تحليل البيانات
    def analyze_data(data):
        total_orders = len(data)
        pending_orders = sum(1 for item in data if item.get('status') == 'Pending')
        completed_orders = sum(1 for item in data if item.get('status') == 'Completed')
        delivered_orders = sum(1 for item in data if item.get('status') == 'Delivered')
        total_revenue = sum(float(item.get('number', 0)) for item in data if item.get('status') == 'Delivered')
        orders_by_city = {}
        revenue_by_city = {}
        orders_by_date = {}
        revenue_by_date = {}

        for item in data:
            city = item.get('city', 'Unknown')
            date_str = item.get('date', 'Unknown')
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                date = 'Unknown'
            
            orders_by_city[city] = orders_by_city.get(city, 0) + 1
            revenue_by_city[city] = revenue_by_city.get(city, 0) + float(item.get('number', 0))
            if date != 'Unknown':
                orders_by_date[date] = orders_by_date.get(date, 0) + 1
                if item.get('status') in ['Pending', 'Completed', 'Delivered']:
                    revenue_by_date[date] = revenue_by_date.get(date, 0) + (float(item['number']) if item['status'] == 'Delivered' else 0)

        return total_orders, pending_orders, completed_orders, delivered_orders, total_revenue, orders_by_city, revenue_by_city, orders_by_date, revenue_by_date

    data = st.session_state.all_data
    total_orders, pending_orders, completed_orders, delivered_orders, total_revenue, orders_by_city, revenue_by_city, orders_by_date, revenue_by_date = analyze_data(data)

    # تحويل البيانات إلى إطار بيانات بانداس
    df_orders = pd.DataFrame(list(orders_by_date.items()), columns=['Date', 'Orders'])
    df_orders['Date'] = pd.to_datetime(df_orders['Date'], format='%Y-%m-%d')
    df_orders = df_orders.sort_values('Date')

    df_revenue = pd.DataFrame(list(revenue_by_date.items()), columns=['Date', 'Revenue'])
    df_revenue['Date'] = pd.to_datetime(df_revenue['Date'], format='%Y-%m-%d')
    df_revenue = df_revenue.sort_values('Date')

    # واجهة المستخدم
    st.title("Dashboard: Order Analysis")

    # تحديد القيم القصوى لكل دائرة
    max_total_orders = 1500
    max_pending_completed_orders = 150
    max_delivered_orders = 1000
    max_pending_orders_orders = 150

    # تعديل التنسيق لجعل الدوائر تظهر كل دائرتين في سطر
    col1, col2 = st.columns(2)
    with col1:
        draw_circle(total_orders, "الطلبات الكلية", max_value=max_total_orders)
    with col2:
        draw_circle(pending_orders, "عدد الطلبات", max_value=max_pending_orders_orders)

    col3, col4 = st.columns(2)
    with col3:
        draw_circle(completed_orders, "الطلبات المسجلة", max_value=max_pending_completed_orders)
    with col4:
        draw_circle(delivered_orders, "الطلبات المستلمة", max_value=max_delivered_orders)

    # عرض الإيرادات اليومية بطريقة احترافية باستخدام بطاقات متعددة الأعمدة داخل expander
    with st.expander("عرض الإيرادات اليومية"):
        st.markdown("## Daily Revenue")

    # حساب الإيرادات اليومية فقط للطلبات المستلمة
        daily_revenue = {}
        for date, revenue in revenue_by_date.items():
            if date in revenue_by_date:
                daily_revenue[date] = revenue_by_date[date]

        dates = list(daily_revenue.keys())
        revenues = list(daily_revenue.values())

        num_cols = 3
        rows = len(dates) // num_cols + (len(dates) % num_cols > 0)

        for row in range(rows):
            cols = st.columns(num_cols)
            for col_index in range(num_cols):
                index = row * num_cols + col_index
                if index < len(dates):
                    with cols[col_index]:
                        formatted_revenue = "{:,.0f}".format(revenues[index]).replace(',', '.')
                        st.markdown(f"""
                        <div style="display: flex; flex-direction: column; align-items: center; background-color: white; padding: 10px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); margin: 10px 0;">
                            <h4>{dates[index].strftime('%Y-%m-%d')}</h4>
                            <p style="font-size: 20px; color: #1E90FF;"><strong>{formatted_revenue} دينار عراقي</strong></p>
                        </div>
                        """, unsafe_allow_html=True)

if selected == "Settings" and check_permission('Settings'):
    st.title("Settings")
    
    st.markdown("""
        <style>
            .sidebar-content {
                animation: slide-in-left 0.5s ease-out;
            }
            @keyframes slide-in-left {
                from {
                    transform: translateX(-100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
        </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        setting_menu = option_menu(
            menu_title="Settings Menu",
            options=["User Management", "Permissions", "Connected Devices", "Change Password", "Delete User"],
            icons=["person", "key", "devices", "lock", "trash"],
            menu_icon="gear",
            default_index=0,
            orientation="vertical",
            styles={
                "nav-link": {
                    "padding": "0.5rem 1rem",
                    "margin": "0.5rem 0",
                    "border-radius": "8px",
                    "transition": "all 0.3s ease",
                },
                "nav-link-selected": {
                    "background-color": "#FF4B4B",
                    "color": "white"
                }
            }
        )

    st.markdown('<div class="sidebar-content">', unsafe_allow_html=True)

    if setting_menu == "User Management":
        st.subheader("User Management")
        new_user = st.text_input("New User Name")
        new_user_code = st.text_input("New User Access Code", type="password")
        is_manager = st.checkbox("Is Manager")
        user_permissions = st.multiselect("Select User Permissions", ["Home", "Orders", "Search", "Dashboard", "Settings"], default=["Home", "Orders", "Search", "Dashboard"])
        if st.button("Add User"):
            if new_user and new_user_code:
                employees[new_user] = {'code': new_user_code, 'is_manager': is_manager, 'devices': [], 'permissions': {perm: True for perm in user_permissions}}
                save_employees(employees)
                st.success(f"User {new_user} added successfully!")
            else:
                st.error("Please enter a username and access code.")

    elif setting_menu == "Permissions":
        st.subheader("Permissions")
        selected_user = st.selectbox("Select User", list(employees.keys()))
        if selected_user:
            user_permissions = st.multiselect("Select Permissions", ["Home", "Orders", "Search", "Dashboard", "Settings"], default=list(employees[selected_user].get('permissions', {}).keys()))
            if st.button("Update Permissions"):
                employees[selected_user]['permissions'] = {perm: True for perm in user_permissions}
                save_employees(employees)
                st.success(f"Permissions updated for {selected_user}")

    elif setting_menu == "Connected Devices":
        st.subheader("Connected Devices")
        for employee, details in employees.items():
            if 'devices' in details:
                st.write(f"**{employee}** is connected from:")
                for device in details['devices']:
                    st.write(f"- {device}")
                if st.button(f"Logout {employee}", key=f"logout_{employee}"):
                    details['devices'] = []
                    save_employees(employees)
                    st.success(f"{employee} has been logged out from all devices.")
                    if employee == st.session_state.current_user:
                        st.session_state.is_authenticated = False
                        st.session_state.current_user = None
                        st.experimental_rerun()

    elif setting_menu == "Change Password":
        st.subheader("Change Password")
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        if st.button("Change Password"):
            if employees[st.session_state.current_user]['code'] == current_password:
                if new_password == confirm_password:
                    employees[st.session_state.current_user]['code'] = new_password
                    save_employees(employees)
                    st.success("Password changed successfully!")
                else:
                    st.error("New passwords do not match.")
            else:
                st.error("Current password is incorrect.")

    elif setting_menu == "Delete User":
        st.subheader("Delete User")
        delete_user = st.selectbox("Select User to Delete", list(employees.keys()))
        if st.button("Delete User"):
            if delete_user:
                del employees[delete_user]
                save_employees(employees)
                st.success(f"User {delete_user} deleted successfully!")
                if delete_user == st.session_state.current_user:
                    st.session_state.is_authenticated = False
                    st.session_state.current_user = None
                    st.experimental_rerun()

    st.markdown('</div>', unsafe_allow_html=True)
