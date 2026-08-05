from flask import Blueprint, render_template
import json
from database import get_db_connection

views = Blueprint('views', __name__)

@views.route('/')
def home():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, nama_produk FROM master_produk")
    daftar_produk = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index.html', daftar_produk=daftar_produk)

@views.route('/dashboard')
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, nama_produk FROM master_produk")
    daftar_produk = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('dashboard.html', daftar_produk=daftar_produk)

@views.route('/settings', methods=['GET'])
def settings():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM master_produk")
    daftar_produk = cursor.fetchall()
    
    for p in daftar_produk:
        try:
            p['param_list'] = json.loads(p['parameter_dinamis']) if p['parameter_dinamis'] else []
        except:
            p['param_list'] = []
            
    cursor.close()
    conn.close()
    return render_template('settings.html', daftar_produk=daftar_produk)

@views.route('/riwayat')
def riwayat_data():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT q.*, p.nama_produk 
        FROM qc_records q
        LEFT JOIN master_produk p ON q.id_produk = p.id
        ORDER BY q.id DESC LIMIT 100
    """
    cursor.execute(query)
    data_riwayat = cursor.fetchall()
    
    for row in data_riwayat:
        try:
            row['param_dict'] = json.loads(row['parameter_dinamis']) if row['parameter_dinamis'] else {}
        except:
            row['param_dict'] = {}
    
    cursor.close()
    conn.close()
    return render_template('riwayat.html', data_riwayat=data_riwayat)
