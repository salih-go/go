import streamlit as st
import json
from streamlit_option_menu import option_menu
import pandas as pd
import plotly.express as px
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from concurrent.futures import ThreadPoolExecutor
import random

def load_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.error("CSS file not found.")

# Add custom CSS for button styling and edit form
st.markdown("""
    <style>
        .stButton button {
            display: inline-block;
            padding: 0.5rem 1rem;
            font-size: 1rem;
            font-weight: bold;
            color: #fff;
            background-color: #007bff;
            border: none;
            border-radius: 150px;
            cursor: pointer;
            transition: background-color 0.3s ease;
            width: 100%;
        }
        
        .stButton button:hover {
            background-color: #007bff;
        }

        .edit-container {
            border-radius: 8px;
            padding: 20px;
            background-color: #f8f9fa;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            margin-top: 10px;
        }

        .edit-container input, .edit-container select, .edit-container textarea {
            width: 100%;
            padding: 100px;
            margin-top: 5px;
            margin-bottom: 200px;
            border: 1px solid #ced4da;
            border-radius: 4px;
        }

        .edit-container button {
            width: 100%;
            padding: 10px;
            font-size: 16px;
            font-weight: bold;
            color: #fff;
            background-color: #28a745;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }

        .edit-container button:hover {
            background-color: #007bff;
        }

    </style>
""", unsafe_allow_html=True)

load_css("custom.css")

def get_gspread_client():
    try:
        # استخدم st.secrets للحصول على المعلومات مباشرة من إعدادات التطبيق
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"])
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Failed to authenticate with Google Sheets: {e}")
        return None

def get_sheet():
    client = get_gspread_client()
    if client:
        try:
            return client.open("MyTestSheet").sheet1
        except Exception as e:
            st.error(f"Failed to open Google Sheet: {e}")
    return None

@st.cache_data(ttl=600)
def load_data():
    sheet = get_sheet()
    if sheet:
        try:
            data = sheet.get_all_records()
            return data if isinstance(data, list) else []
        except Exception as e:
            st.error(f"Failed to load data from Google Sheet: {e}")
    return []

def save_data_to_gsheet(data):
    sheet = get_sheet()
    if sheet:
        try:
            if isinstance(data, list):
                sheet.clear()
                sheet.append_row(list(data[0].keys()))
                for row in data:
                    sheet.append_row(list(row.values()))
        except Exception as e:
            st.error(f"Failed to save data to Google Sheet: {e}")

executor = ThreadPoolExecutor(max_workers=5)

def save_data(new_data):
    if 'all_data' not in st.session_state:
        st.session_state.all_data = load_data()
    st.session_state.all_data.insert(0, new_data)
    executor.submit(save_data_to_gsheet, st.session_state.all_data)
    st.session_state.update_key = random.random()
    st.session_state.save_success = True
    st.rerun()

def update_order_status(index, new_status):
    st.session_state.all_data[index]['status'] = new_status
    executor.submit(save_data_to_gsheet, st.session_state.all_data)
    st.session_state.update_key = random.random()
    st.rerun()

def delete_order(index):
    del st.session_state.all_data[index]
    executor.submit(save_data_to_gsheet, st.session_state.all_data)
    st.session_state.update_key = random.random()
    st.rerun()

def move_to_notifications(index):
    st.session_state.all_data[index]['status'] = 'Notification'
    executor.submit(save_data_to_gsheet, st.session_state.all_data)
    st.session_state.update_key = random.random()
    st.rerun()

def edit_order(index, updated_data):
    st.session_state.all_data[index].update(updated_data)
    executor.submit(save_data_to_gsheet, st.session_state.all_data)
    st.session_state.update_key = random.random()
    st.session_state.edit_mode = False  # Set edit mode to False after saving changes
    st.rerun()

def format_order(data, index):
    formatted_number = "{:,.0f}".format(float(data.get('number', 0) or 0)).replace(',', '.')
    background_color = {"Completed": "#d4edda", "Delivered": "#cce5ff", "Notification": "#ffebcc"}.get(data.get('status'), "#f8d7da")
    status_color = {"Completed": "green", "Delivered": "blue", "Notification": "orange"}.get(data.get('status'), "red")
    return f"""
    <div style="border-radius: 30px; padding: 16px; margin-bottom: 3px; background-color: #fff; box-shadow: 0 30px 8px rgba(0, 0, 0, 0.1); position: relative;">
        <div style="display: flex; flex-direction: column; align-items: flex-start;">
            <div style="font-weight: bold; font-size: 1.3em;">{data.get('hello', 'N/A')}
                <a href="javascript:void(0);" onclick="document.getElementById('edit_form_{index}').style.display='block';" style="float: right; margin-left: 10px;"></a>
            </div>
            <div style="color: gray;">{data.get('region', 'N/A')}</div>
            <div style="margin: 8px 0;">
                <span style="background-color: {background_color}; padding: 4px 8px; border-radius: 50px; color: {status_color};"><strong>{data.get('status', 'N/A')}</strong></span>
                <span style="background-color: #f0f0f0; padding: 4px 8px; border-radius: 50px; margin-left: 8px;">Order  {index+1}</span>
            </div>
            <div style="color: black; font-weight: bold; letter-spacing: 1px;">{data.get('phone', 'N/A')}</div>
        </div>
    </div>
    """

def format_order_details(data):
    formatted_number = "{:,.0f}".format(float(data.get('number', 0) or 0)).replace(',', '.')
    return f"""
    <div style="border-radius: 150px; padding: 16px; background-color: #fff; box-shadow: 100 4px 8px rgba(0, 0, 0, 0.1);">
        <p><strong>Name:</strong> {data.get('hello', 'N/A')}</p>
        <p><strong>Phone Number:</strong> {data.get('phone', 'N/A')}</p>
        <p><strong>City:</strong> {data.get('city', 'N/A')}</p>
        <p><strong>Region:</strong> {data.get('region', 'N/A')}</p>
        <p><strong>Price:</strong> {formatted_number}</p>
        <p><strong>Type:</strong> {data.get('kind', 'N/A')}</p>
        <p><strong>Total:</strong> {data.get('total', 'N/A')}</p>
        <p><strong>More Information:</strong> {data.get('more', 'N/A')}</p>
    </div>
    """

def load_employees():
    try:
        with open('employees.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_employees(employees):
    with open('employees.json', 'w') as f:
        json.dump(employees, f)

employees = load_employees()

if 'admin' not in employees:
    employees['admin'] = {'code': 'admin123', 'is_manager': True, 'devices': [], 'permissions': {'Settings': True, 'Home': True, 'Orders': True, 'Search': True, 'Dashboard': True}}
    save_employees(employees)
    st.info("Default admin account created. Username: 'admin', Password: 'admin123'")

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

current_user_permissions = employees[st.session_state.current_user].get('permissions', {})
check_permission = lambda page: current_user_permissions.get(page, False)

# تأكد من تعريف المتغير available_pages قبل استخدامه
available_pages = ["Home", "Orders", "Search", "Dashboard", "Settings"]

# قائمة التنقل الجانبية
with st.sidebar:
    selected = option_menu(
        menu_title="Main Menu",
        options=[page for page in available_pages if check_permission(page)],
        icons=["house", "clipboard", "search", "graph-up", "gear"],
        menu_icon="cast",
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

if selected == "Home" and check_permission('Home'):
    hello, phone = st.text_input("THE NAME"), st.text_input("Phone Number")
    city = st.selectbox("Select City", ["بغداد", "البصرة", "نينوى", "الانبار", "ديالى", "كربلاء", "بابل", "واسط", "صلاح الدين", "القادسيه", "ذي قار", "المثنى", "ميسان", "السليمانية", "دهوك", "اربيل", "كركوك", "النجف", "الموصل", "حلبجة"])
    region, kind = st.text_input("Enter the Region"), st.selectbox("type of prodact", ["smart watch", "airtag"])
    number, total = st.number_input('price', min_value=0.0, max_value=500000.0, value=25000.0, step=5000.0, format='%0.0f'), st.number_input('total', min_value=0, max_value=100, value=1, step=1)
    more = st.text_area("Type here for more information")

    if st.button("Save Data"):
        with st.spinner("Saving data..."):
            new_data = {'hello': hello, 'phone': phone, 'city': city, 'region': region, 'more': more, 'number': number, 'kind': kind, 'total': total, 'status': 'Pending', 'date': datetime.today().strftime('%Y-%m-%d')}
            save_data(new_data)
            st.session_state.save_success = True

if 'save_success' in st.session_state and st.session_state.save_success:
    st.success("Data saved successfully!")
    st.session_state.save_success = False

if "all_data" not in st.session_state:
    st.session_state.all_data = load_data()

if selected == "Orders" and check_permission('Orders'):
    order_tabs = st.tabs(["Pending Orders", "Completed Orders", "Delivered Orders", "Notifications"])

    with order_tabs[0]:
        for i, data in enumerate(st.session_state.all_data):
            if data.get('status') == 'Pending':
                st.markdown(format_order(data, i), unsafe_allow_html=True)
                with st.expander(f"View Details for Order {i+1}"):
                    st.markdown(format_order_details(data), unsafe_allow_html=True)
                    col1, col2, col3, col4 = st.columns(4)
                    if col1.button(f"Completed", key=f"toggle_button_pending_{i}"):
                        update_order_status(i, 'Completed' if data.get('status') == 'Pending' else 'Pending')
                    if col2.button(f"Delivered", key=f"deliver_button_pending_{i}"):
                        update_order_status(i, 'Delivered')
                    if col3.button(f"Delete", key=f"delete_button_pending_{i}"):
                        delete_order(i)
                    if col4.button(f"Notifications", key=f"move_to_notifications_{i}"):
                        move_to_notifications(i)
                    st.write("---")

    with order_tabs[1]:
        for i, data in enumerate(st.session_state.all_data):
            if data.get('status') == 'Completed':
                st.markdown(format_order(data, i), unsafe_allow_html=True)
                with st.expander(f"View Details for Order {i+1}"):
                    st.markdown(format_order_details(data), unsafe_allow_html=True)
                    col1, col2, col3, col4 = st.columns(4)
                    if col1.button(f"Pending", key=f"toggle_button_completed_{i}"):
                        update_order_status(i, 'Pending' if data.get('status') == 'Completed' else 'Completed')
                    if col2.button(f"Delivered", key=f"deliver_button_completed_{i}"):
                        update_order_status(i, 'Delivered')
                    if col3.button(f"Delete", key=f"delete_button_completed_{i}"):
                        delete_order(i)
                    if col4.button(f"Notifications", key=f"move_to_notifications_{i}"):
                        move_to_notifications(i)
                    st.write("---")

    with order_tabs[2]:
        for i, data in enumerate(st.session_state.all_data):
            if data.get('status') == 'Delivered':
                st.markdown(format_order(data, i), unsafe_allow_html=True)
                with st.expander(f"View Details for Order {i+1}"):
                    st.markdown(format_order_details(data), unsafe_allow_html=True)
                    col1, col3, col4 = st.columns(3)
                    if col1.button(f"Pending", key=f"toggle_button_delivered_{i}"):
                        update_order_status(i, 'Pending' if data.get('status') == 'Delivered' else 'Completed')
                    if col3.button(f"Delete", key=f"delete_button_delivered_{i}"):
                        delete_order(i)
                    if col4.button(f"Notifications", key=f"move_to_notifications_{i}"):
                        move_to_notifications(i)
                    st.write("---")

    with order_tabs[3]:
        for i, data in enumerate(st.session_state.all_data):
            if data.get('status') == 'Notification':
                st.markdown(format_order(data, i), unsafe_allow_html=True)
                with st.expander(f"View Details for Order {i+1}"):
                    st.markdown(format_order_details(data), unsafe_allow_html=True)
                    col1, col3, col2, col4 = st.columns(4)
                    if col1.button(f"Pending", key=f"toggle_button_notification_{i}"):
                        update_order_status(i, 'Pending' if data.get('status') == 'Notification' else 'Completed')
                    if col2.button(f"Delete", key=f"delete_button_notification_{i}"):
                        delete_order(i)
                    if col3.button(f"Edit", key=f"edit_button_notification_{i}"):
                        st.session_state.edit_mode = True
                        st.session_state.edit_index = i
                    st.write("---")

        if 'edit_mode' in st.session_state and st.session_state.edit_mode:
            index = st.session_state.edit_index
            data = st.session_state.all_data[index]
            # Displaying the expander form for editing
            with st.expander("Edit Order Details", expanded=True):
                name = st.text_input("Name", value=data['hello'])
                phone = st.text_input("Phone Number", value=data['phone'])
                city = st.selectbox("Select City", ["بغداد", "البصرة", "نينوى", "الانبار", "ديالى", "كربلاء", "بابل", "واسط", "صلاح الدين", "القادسيه", "ذي قار", "المثنى", "ميسان", "السليمانية", "دهوك", "اربيل", "كركوك", "النجف", "الموصل", "حلبجة"], index=["بغداد", "البصرة", "نينوى", "الانبار", "ديالى", "كربلاء", "بابل", "واسط", "صلاح الدين", "القادسيه", "ذي قار", "المثنى", "ميسان", "السليمانية", "دهوك", "اربيل", "كركوك", "النجف", "الموصل", "حلبجة"].index(data['city']))
                region = st.text_input("Enter the Region", value=data['region'])
                kind = st.selectbox("Type of Product", ["smart watch", "airtag"], index=["smart watch", "airtag"].index(data['kind']))
                number = st.number_input('Price', min_value=0.0, max_value=500000.0, value=float(data['number']), step=5000.0, format='%0.0f')
                total = st.number_input('Total', min_value=0, max_value=100, value=int(data['total']), step=1)
                more = st.text_area("Type here for more information", value=data['more'])

                if st.button("Save Changes"):
                    updated_data = {'hello': name, 'phone': phone, 'city': city, 'region': region, 'more': more, 'number': number, 'kind': kind, 'total': total}
                    edit_order(index, updated_data)
                    st.session_state.edit_mode = False
                    st.success("Order updated successfully!")
elif selected == "Search" and check_permission('Search'):
    if "search_query" not in st.session_state:
        st.session_state.search_query = ""
    search_query = st.text_input("Search by phone number or name", key="search_input")
    col1, = st.columns([1])
    if col1.button("Search"):
        st.session_state.search_query = search_query.lower()

    if st.session_state.search_query:
        filtered_data = [entry for entry in st.session_state.all_data if st.session_state.search_query in str(entry.get('phone', '')).lower() or st.session_state.search_query in str(entry.get('hello', '')).lower()]
        if filtered_data:
            for i, data in enumerate(filtered_data):
                st.markdown(format_order(data, i), unsafe_allow_html=True)
                with st.expander(f"View Details for Order {i+1}"):
                    st.markdown(format_order_details(data), unsafe_allow_html=True)
                    col1, col2, col3 = st.columns([1, 1, 1])
                    if col1.button(f"Toggle Status", key=f"toggle_button_search_{i}"):
                        update_order_status(i, 'Pending' if data.get('status') == 'Completed' else 'Completed')
                    if col2.button(f"Mark as Delivered", key=f"deliver_button_search_{i}"):
                        update_order_status(i, 'Delivered')
                    if col3.button(f"Delete Entry", key=f"delete_button_search_{i}"):
                        delete_order(i)
        else:
            st.write("No entries found with your search criteria.")

elif selected == "Dashboard" and check_permission('Dashboard'):
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

    def analyze_data(data):
        total_orders = len(data)
        pending_orders = sum(1 for item in data if item.get('status') == 'Pending')
        completed_orders = sum(1 for item in data if item.get('status') == 'Completed')
        delivered_orders = sum(1 for item in data if item.get('status') == 'Delivered')
        total_revenue = sum(float(item.get('number', 0)) for item in data if item.get('status') == 'Delivered')
        orders_by_city, revenue_by_city, orders_by_date, revenue_by_date = {}, {}, {}, {}

        for item in data:
            city = item.get('city', 'Unknown')
            date_str = item.get('date', 'Unknown')
            date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str != 'Unknown' else 'Unknown'
            orders_by_city[city] = orders_by_city.get(city, 0) + 1
            revenue_by_city[city] = revenue_by_city.get(city, 0) + float(item.get('number', 0) or 0)
            if date != 'Unknown':
                orders_by_date[date] = orders_by_date.get(date, 0) + 1
                if item.get('status') == 'Delivered':
                    revenue_by_date[date] = revenue_by_date.get(date, 0) + float(item['number'])

        return total_orders, pending_orders, completed_orders, delivered_orders, total_revenue, orders_by_city, revenue_by_city, orders_by_date, revenue_by_date

    data = st.session_state.all_data
    total_orders, pending_orders, completed_orders, delivered_orders, total_revenue, orders_by_city, revenue_by_city, orders_by_date, revenue_by_date = analyze_data(data)

    df_orders = pd.DataFrame(list(orders_by_date.items()), columns=['Date', 'Orders']).sort_values('Date')
    df_revenue = pd.DataFrame(list(revenue_by_date.items()), columns=['Date', 'Revenue']).sort_values('Date')

    max_total_orders = 1500
    max_pending_completed_orders = 150
    max_delivered_orders = 1000
    max_pending_orders_orders = 150

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

    with st.expander("عرض الإيرادات اليومية"):
        st.markdown("## Daily Revenue")

        daily_revenue = {date: revenue for date, revenue in revenue_by_date.items()}
        dates, revenues = list(daily_revenue.keys()), list(daily_revenue.values())

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
        selected_user = st.selectbox("Select User", list(employees.keys()))
        if selected_user:
            user_permissions = st.multiselect("Select Permissions", ["Home", "Orders", "Search", "Dashboard", "Settings"], default=list(employees[selected_user].get('permissions', {}).keys()))
            if st.button("Update Permissions"):
                employees[selected_user]['permissions'] = {perm: True for perm in user_permissions}
                save_employees(employees)
                st.success(f"Permissions updated for {selected_user}")

    elif setting_menu == "Connected Devices":
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
                        st.session_state.update_key = random.random()

    elif setting_menu == "Change Password":
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
        delete_user = st.selectbox("Select User to Delete", list(employees.keys()))
        if st.button("Delete User"):
            if delete_user:
                del employees[delete_user]
                save_employees(employees)
                st.success(f"User {delete_user} deleted successfully!")
                if delete_user == st.session_state.current_user:
                    st.session_state.is_authenticated = False
                    st.session_state.current_user = None
                    st.session_state.update_key = random.random()

    st.markdown('</div>', unsafe_allow_html=True)
