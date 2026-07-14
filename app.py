from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from flask_cors import CORS
import mysql.connector
import os
import io
import json
from datetime import datetime, timedelta
import random
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
import pandas as pd
from functools import wraps

app = Flask(__name__)
CORS(app) 
app.secret_key = 'rahasia_spc_pabrik_123'


# --- KONFIGURASI DATABASE ---
db_config = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER', 'spc_user'),
    'password': os.environ.get('DB_PASSWORD', 'spc_password'),
    'database': os.environ.get('DB_NAME', 'spc_database')
}

def get_db_connection():
    return mysql.connector.connect(**db_config)


@app.route('/settings', methods=['GET'])
def settings():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM master_produk")
    daftar_produk = cursor.fetchall()
    
    # PARSING JSON DI BACKEND BIAR FRONTEND NGGAK ERROR/HILANG
    for p in daftar_produk:
        try:
            p['param_list'] = json.loads(p['parameter_dinamis']) if p['parameter_dinamis'] else []
        except:
            p['param_list'] = []
            
    cursor.close()
    conn.close()
    return render_template('settings.html', daftar_produk=daftar_produk)
                           
# =============================================================
# FITUR TAMBAH PRODUK BARU
# =============================================================
@app.route('/api/tambah-produk', methods=['POST'])
def tambah_produk():
    nama_produk = request.form.get('nama_produk')
    raw_params = request.form.get('parameter_dinamis')
    
    import json
    if not raw_params or raw_params.strip() == '':
        parameters_json = json.dumps([])
    else:
        try:
            parameters_data = json.loads(raw_params)
            parameters_json = json.dumps(parameters_data)
        except:
            parameters_json = json.dumps([])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """INSERT INTO master_produk (nama_produk, parameter_dinamis) 
               VALUES (%s, %s)"""
    cursor.execute(query, (nama_produk, parameters_json))
    
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/settings')

# =============================================================
# FITUR EDIT PARAMETER PRODUK
# =============================================================
@app.route('/api/edit-produk', methods=['POST'])
def edit_produk():
    id_produk = request.form.get('id')
    nama_produk = request.form.get('nama_produk')
    raw_params = request.form.get('parameter_dinamis')
    
    import json
    if not raw_params or raw_params.strip() == '':
        parameters_json = json.dumps([])
    else:
        try:
            parameters_data = json.loads(raw_params)
            parameters_json = json.dumps(parameters_data)
        except:
            parameters_json = json.dumps([])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """UPDATE master_produk 
               SET nama_produk=%s, parameter_dinamis=%s 
               WHERE id=%s"""
    cursor.execute(query, (nama_produk, parameters_json, id_produk))
    
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/settings')

# =============================================================
# 1. ROUTE PENERIMA DATA MANUAL
# =============================================================
@app.route('/api/qc-input', methods=['POST'])
def input_qc():
    try:
        data = request.json
        
        id_produk = data.get('id_produk')
        
        if not id_produk:
            return jsonify({"status": "error", "message": "Pilih produk terlebih dahulu!"}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id FROM master_produk WHERE id = %s", (id_produk,))
        produk = cursor.fetchone()
        
        if not produk:
            return jsonify({"status": "error", "message": "Produk tidak ditemukan di database!"}), 400

        tanggal = data.get('tanggal', datetime.now().strftime('%Y-%m-%d'))
        
        sql = """INSERT INTO qc_records 
                 (id_produk, tanggal, shift, grup, mesin, waktu, parameter_dinamis) 
                 VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        
        import json
        parameter_dinamis = json.dumps(data.get('parameter_dinamis', {}))

        val = (
            id_produk,
            tanggal, data.get('shift'), data.get('grup'), data.get('mesin'), data.get('waktu'), 
            parameter_dinamis
        )
        
        cursor.execute(sql, val)
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"status": "success", "message": "Data berhasil masuk database!"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# =============================================================
# 2. ROUTE PENGIRIM DATA (DIPISAH PER MESIN & PER PRODUK)
# =============================================================
@app.route('/api/qc-data', methods=['GET'])
def get_qc_data():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # SQL UPDATE: Ambil kombinasi unik antara Mesin dan Produk
        cursor.execute("SELECT DISTINCT mesin, id_produk FROM qc_records WHERE mesin IS NOT NULL AND id_produk IS NOT NULL")
        kombinasi_list = cursor.fetchall()
        
        dashboard_data = []

        for komb in kombinasi_list:
            msn_asli = komb['mesin']
            id_prod = komb['id_produk']
            
            # Bikin ID Unik buat Frontend (Contoh: "14-1" artinya Mesin 14, Produk ID 1)
            unique_msn = f"{msn_asli}-{id_prod}"

            query_line = """
                SELECT q.*, p.nama_produk, p.parameter_dinamis as standar_parameter
                FROM (
                    SELECT * FROM qc_records WHERE mesin = %s AND id_produk = %s ORDER BY id DESC LIMIT 30
                ) q
                LEFT JOIN master_produk p ON q.id_produk = p.id
                ORDER BY q.id ASC
            """
            cursor.execute(query_line, (msn_asli, id_prod))
            history = cursor.fetchall()

            if not history:
                continue
                
            current = history[-1] 
            
            # Ekstrak primary parameter (parameter pertama di JSON)
            primary_param_name = "N/A"
            primary_param_val = 0
            # PENTING: default-nya None (bukan 0!). Kalau default-nya 0, chart.js
            # akan memaksa sumbu-Y mulai dari 0 hanya gara-gara garis LSL/USL,
            # bikin data aktual keliatan gepeng/aneh proporsinya di grafik.
            primary_param_lcl = None
            primary_param_ucl = None
            
            try:
                curr_param = json.loads(current['parameter_dinamis']) if current['parameter_dinamis'] else {}
                if curr_param:
                    primary_param_name = list(curr_param.keys())[0]
                    primary_param_val = curr_param[primary_param_name]
            except:
                pass
                
            # Ambil batas dari master_produk (standar_parameter)
            try:
                if 'standar_parameter' in current and current['standar_parameter']:
                    std_params = json.loads(current['standar_parameter'])
                    for p in std_params:
                        if p['name'] == primary_param_name:
                            primary_param_lcl = p.get('lcl')
                            primary_param_ucl = p.get('ucl')
                            break
            except:
                pass

            # Hitung shift stats manual karena JSON susah di-AVG lewat SQL
            shift_dict = {}
            for h in history:
                try:
                    p_val = 0
                    p_json = json.loads(h['parameter_dinamis']) if h['parameter_dinamis'] else {}
                    if primary_param_name in p_json:
                        p_val = float(p_json[primary_param_name])
                    
                    s_name = h['shift']
                    if s_name not in shift_dict:
                        shift_dict[s_name] = []
                    shift_dict[s_name].append(p_val)
                except:
                    pass
                    
            shift_stats = []
            for s_name, vals in shift_dict.items():
                avg = sum(vals) / len(vals) if vals else 0
                shift_stats.append({"shift": s_name, "avg_tebal": avg})

            # Status NORMAL/OUT yang aman terhadap LSL/USL yang belum diset (None)
            try:
                val_check = float(primary_param_val)
                is_out = False
                if primary_param_lcl is not None and val_check < float(primary_param_lcl):
                    is_out = True
                if primary_param_ucl is not None and val_check > float(primary_param_ucl):
                    is_out = True
                status_primary = "OUT" if is_out else "NORMAL"
            except (TypeError, ValueError):
                status_primary = "NORMAL"

            dashboard_data.append({
                "mesin": unique_msn,
                "primary_param_name": primary_param_name,
                "current": {
                    "nama_produk": current.get('nama_produk', 'Produk Tidak Diketahui'),
                    "waktu_update": current.get('created_at').strftime("%d %b %Y, %H:%M:%S") if current.get('created_at') else current.get('tanggal', '-'),
                    "tebal_aktual": primary_param_val,
                    "tebal_max": "-",
                    "shift_aktif": current['shift'],
                    "grup_aktif": current['grup'],
                    "status": status_primary,
                    "lsl": primary_param_lcl,
                    "usl": primary_param_ucl,
                    "parameter_dinamis": current.get('parameter_dinamis', '{}'),
                    "standar_parameter": current.get('standar_parameter', '[]')
                },
                "shift_stats": shift_stats,
                "history": history
            })

        cursor.close()
        conn.close()
        
        return jsonify({"status": "success", "data": dashboard_data}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    
# =============================================================
# ROUTE UNTUK AMBIL DAFTAR MESIN (DINAMIS)
# =============================================================
@app.route('/api/list-mesin', methods=['GET'])
def get_list_mesin():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Ambil daftar mesin unik yang pernah diinput ke database
        cursor.execute("SELECT DISTINCT mesin FROM qc_records WHERE mesin IS NOT NULL ORDER BY mesin ASC")
        mesin_list = [row['mesin'] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        # Kalau database masih kosong banget, kasih default mesin 14
        if not mesin_list:
            mesin_list = ['14']
            
        return jsonify({"status": "success", "data": mesin_list}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# =============================================================
# 3. ROUTE EXPORT EXCEL (LAPORAN QC DINAMIS)
# =============================================================
@app.route('/api/export-excel', methods=['GET'])
def export_excel():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. Trik SQL JOIN: Kita gabungin data operator (qc_records) dengan standar SPV (master_produk)
    query = """
        SELECT q.*, p.nama_produk, p.parameter_dinamis as standar_parameter 
        FROM qc_records q
        LEFT JOIN master_produk p ON q.id_produk = p.id
        WHERE q.tanggal BETWEEN %s AND %s 
        ORDER BY q.tanggal ASC, q.waktu ASC
    """
    cursor.execute(query, (start_date, end_date))
    data = cursor.fetchall()
    
    if not data:
        cursor.close()
        conn.close()
        return "TIDAK ADA DATA DI RENTANG TANGGAL TERSEBUT.", 404

    df = pd.DataFrame(data)

    # ==========================================
    # BAGIAN 1: TRANSFORMASI DATA (LOGIKA DINAMIS)
    # ==========================================
    
    df['Shift_Gabung'] = df['shift'].astype(str) + df['grup']

    # (Baris df['Status Tebal Std'] KITA HAPUS TOTAL DARI SINI)
    
    dynamic_cols = []
    if 'parameter_dinamis' in df.columns:
        parsed_params = df['parameter_dinamis'].apply(lambda val: json.loads(val) if pd.notnull(val) and val != '' else {})
        df_params = pd.json_normalize(parsed_params)
        df = pd.concat([df.drop('parameter_dinamis', axis=1), df_params], axis=1)
        dynamic_cols = list(df_params.columns)
        
    # ==========================================
    # SPC SUMMARY CALCULATION
    # ==========================================
    summary_data = []
    for nama_prod in df['nama_produk'].dropna().unique():
        df_prod = df[df['nama_produk'] == nama_prod]
        
        # 2. Dynamic Params Summary
        if 'standar_parameter' in df_prod.columns:
            standar_str = df_prod['standar_parameter'].iloc[-1] if not df_prod.empty and not pd.isna(df_prod['standar_parameter'].iloc[-1]) else '[]'
            try:
                standar_json = json.loads(standar_str)
            except:
                standar_json = []
                
            for std_param in standar_json:
                p_name = std_param.get('name')
                if p_name and p_name in df_prod.columns:
                    df_prod_param = pd.to_numeric(df_prod[p_name], errors='coerce')
                    p_mean = df_prod_param.mean()
                    p_std = df_prod_param.std()
                    if pd.isna(p_std): p_std = 0
                    
                    lsl_dyn = std_param.get('lcl')
                    if lsl_dyn is None: lsl_dyn = 0
                    usl_dyn = std_param.get('ucl')
                    if usl_dyn is None: usl_dyn = 0
                    
                    p_calc_lcl = p_mean - (3 * p_std)
                    p_calc_ucl = p_mean + (3 * p_std)
                    
                    p_status = "Capable" if (p_calc_lcl >= lsl_dyn and p_calc_ucl <= usl_dyn) else "Out of Control"
                    
                    summary_data.append({
                        "Product Name": nama_prod,
                        "Parameter Name": p_name,
                        "Mean (Rata-rata)": round(p_mean, 3) if not pd.isna(p_mean) else "-",
                        "Std Dev (Sigma)": round(p_std, 3),
                        "LSL (Spec Limit Bawah)": lsl_dyn,
                        "USL (Spec Limit Atas)": usl_dyn,
                        "Calculated LCL (Control Limit Bawah)": round(p_calc_lcl, 3) if not pd.isna(p_calc_lcl) else "-",
                        "Calculated UCL (Control Limit Atas)": round(p_calc_ucl, 3) if not pd.isna(p_calc_ucl) else "-",
                        "Status": p_status
                    })
    
    df_summary = pd.DataFrame(summary_data)

    if 'standar_parameter' in df.columns:
        df = df.drop('standar_parameter', axis=1)
    
    df['Kesimpulan Proses'] = 'Proses Stabil'

    # Filter dan Ubah Nama Kolom (Tambahin 'Produk' biar jelas)
    kolom_baru = {
        'tanggal': 'Tanggal',
        'nama_produk': 'Produk',
        'Shift_Gabung': 'Shift',
        'mesin': 'Mesin',
        'waktu': 'Waktu'
    }
    
    df_renamed = df.rename(columns=kolom_baru)
    urutan_kolom = list(kolom_baru.values()) + dynamic_cols + ['Kesimpulan Proses']    
    # Pastikan hanya kolom yang ada di dataframe yang diambil
    kolom_tersedia = [col for col in urutan_kolom if col in df_renamed.columns]
    df_final = df_renamed[kolom_tersedia]
    
    df_final.insert(0, 'No', range(1, len(df_final) + 1))
    df_final['Tanggal'] = pd.to_datetime(df_final['Tanggal']).dt.strftime('%d %b %Y')

    # ==========================================
    # BAGIAN 2: STYLING EXCEL (MULTI-SHEET OTOMATIS)
    # ==========================================
    output_file = io.BytesIO()
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        
        # --- FUNGSI PEMBANTU UNTUK DESAIN TABEL ---
        def styling_sheet(worksheet, nama_sheet):
            font_header = Font(bold=True, color="FFFFFF")
            align_center = Alignment(horizontal="center", vertical="center")
            border_thin = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
            
            warna_biru = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
            warna_merah = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")
            warna_hijau = PatternFill(start_color="548235", end_color="548235", fill_type="solid")

            for col_num, column_cells in enumerate(worksheet.columns, 1):
                nama_kolom = column_cells[0].value 
                panjang_maksimal = max((len(str(cell.value)) for cell in column_cells if cell.value is not None), default=10)
                worksheet.column_dimensions[column_cells[0].column_letter].width = panjang_maksimal + 2
                
                for cell in column_cells:
                    if cell.row == 1:
                        cell.font = font_header
                        cell.alignment = align_center
                        cell.border = border_thin
                        
                        if nama_kolom in ['Status Tebal', 'Kesimpulan Proses']:
                            cell.fill = warna_merah
                        elif nama_kolom and 'Std' in str(nama_kolom):
                            cell.fill = warna_hijau
                        else:
                            cell.fill = warna_biru
                            
                    elif cell.row > 1:
                        cell.border = border_thin
                        cell.alignment = align_center

        # ---------------- SHEET 0: SUMMARY (SPC CALCULATION) ----------------
        if not df_summary.empty:
            df_summary.to_excel(writer, index=False, sheet_name='Summary')
            styling_sheet(writer.sheets['Summary'], 'Summary')

        # ---------------- SHEET 1: MASTER LOG (SEMUA DATA NYATU) ----------------
        df_final.to_excel(writer, index=False, sheet_name='Master_Log')
        styling_sheet(writer.sheets['Master_Log'], 'Master_Log')

        # ---------------- SHEET DINAMIS: DIPISAH PER NAMA PRODUK ----------------
        # Ambil daftar nama produk unik yang ada di rentang tanggal ini
        daftar_produk_unik = df_final['Produk'].dropna().unique()
        
        for idx, nama_prod in enumerate(daftar_produk_unik):
            # Filter data khusus produk ini saja
            df_filter = df_final[df_final['Produk'] == nama_prod]
            
            # Excel punya aturan: Nama sheet max 31 karakter & dilarang pakai simbol tertentu
            sheet_name = str(nama_prod)[:31]
            import re
            sheet_name = re.sub(r'[\\/*?:\[\]]', '', sheet_name)
            
            # Kalau namanya kosong atau kembar gara-gara dipotong, kasih nama default
            if not sheet_name: sheet_name = f"Produk_{idx}"
            
            df_filter.to_excel(writer, index=False, sheet_name=sheet_name)
            styling_sheet(writer.sheets[sheet_name], sheet_name)

    cursor.close()
    conn.close()

    output_file.seek(0)
    nama_file = f"Laporan_QC_{start_date}_sd_{end_date}.xlsx"

    return send_file(
        output_file,
        as_attachment=True,
        download_name=nama_file,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# =============================================================
# 4. ROUTE UPLOAD EXCEL/CSV (BULK INSERT)
# =============================================================
def parse_tanggal_indo(tanggal_input):
    if pd.isnull(tanggal_input) or str(tanggal_input).strip() == '':
        return datetime.now().strftime('%Y-%m-%d')
        
    if isinstance(tanggal_input, (datetime, pd.Timestamp)):
        return tanggal_input.strftime('%Y-%m-%d')
        
    tgl_str = str(tanggal_input).strip().lower()
    
    bulan_map = {
        'januari': '01', 'februari': '02', 'maret': '03', 'april': '04',
        'mei': '05', 'juni': '06', 'juli': '07', 'agustus': '08',
        'september': '09', 'oktober': '10', 'november': '11', 'desember': '12',
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'agu': '08',
        'sep': '09', 'okt': '10', 'nov': '11', 'des': '12'
    }
    
    for text_indo, angka in bulan_map.items():
        if text_indo in tgl_str:
            tgl_str = tgl_str.replace(text_indo, angka)
            break
            
    try:
        return pd.to_datetime(tgl_str, dayfirst=True).strftime('%Y-%m-%d')
    except:
        return datetime.now().strftime('%Y-%m-%d')

@app.route('/api/upload-excel', methods=['POST'])
def upload_excel():
    try:
        id_produk = request.form.get('id_produk')
        if not id_produk:
            return jsonify({"status": "error", "message": "Pilih produk terlebih dahulu dari dropdown"}), 400

        if 'file' not in request.files:
            return jsonify({"status": "error", "message": "Tidak ada file yang diunggah"}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({"status": "error", "message": "File kosong"}), 400
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.filename.endswith('.xlsx'):
            df = pd.read_excel(file)
        else:
            return jsonify({"status": "error", "message": "Format harus .csv atau .xlsx"}), 400
        df = df.where(pd.notnull(df), None)

        STANDARD_COLS = {'Tanggal', 'Shift', 'Grup', 'Mesin', 'Waktu'}
        dynamic_cols = [col for col in df.columns if col not in STANDARD_COLS]

        conn = get_db_connection()
        cursor = conn.cursor()

        sukses_count = 0
        sql = """INSERT INTO qc_records 
                 (id_produk, tanggal, shift, grup, mesin, waktu, parameter_dinamis) 
                 VALUES (%s, %s, %s, %s, %s, %s, %s)"""

        for index, row in df.iterrows():

            param_dinamis = {}
            for col in dynamic_cols:
                val = row.get(col)
                if val is not None:
                    try:
                        param_dinamis[col] = float(val)
                    except (ValueError, TypeError):
                        param_dinamis[col] = str(val)

            val = (
                id_produk,
                parse_tanggal_indo(row.get('Tanggal')),
                str(row.get('Shift', '')), str(row.get('Grup', 'A')), str(row.get('Mesin', '14')), str(row.get('Waktu', '')),
                json.dumps(param_dinamis) if param_dinamis else None
            )
            cursor.execute(sql, val)
            sukses_count += 1

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"status": "success", "message": f"{sukses_count} baris data berhasil diunggah!"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/')
def home():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Tarik daftar produk untuk ditampilkan di dropdown form
    cursor.execute("SELECT id, nama_produk FROM master_produk")
    daftar_produk = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('index.html', daftar_produk=daftar_produk)

# =============================================================
# FITUR RIWAYAT & HAPUS DATA (KHUSUS SPV)
# =============================================================
@app.route('/riwayat')
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
    
    # PARSING JSON DI BACKEND UNTUK DITAMPILKAN SEBAGAI FORM DI RIWAYAT
    for row in data_riwayat:
        try:
            row['param_dict'] = json.loads(row['parameter_dinamis']) if row['parameter_dinamis'] else {}
        except:
            row['param_dict'] = {}
    
    cursor.close()
    conn.close()
    return render_template('riwayat.html', data_riwayat=data_riwayat)

@app.route('/api/hapus-qc/<int:id_qc>', methods=['POST'])
def hapus_qc(id_qc):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Eksekusi penghapusan data berdasarkan ID
        cursor.execute("DELETE FROM qc_records WHERE id = %s", (id_qc,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        # Balik lagi ke halaman riwayat setelah sukses ngehapus
        return redirect('/riwayat')
    except Exception as e:
        return f"Terjadi kesalahan saat menghapus data: {str(e)}", 400

# =============================================================
# FITUR EDIT DATA QC DARI RIWAYAT
# =============================================================
@app.route('/api/edit-qc', methods=['POST'])
def edit_qc():
    try:
        id_qc = request.form.get('id')
        
        # REKONSTRUKSI JSON DARI INPUT FORM DINAMIS (yang prefix-nya 'dyn_')
        param_dinamis = {}
        for key, value in request.form.items():
            if key.startswith('dyn_'):
                param_name = key[4:] # Potong tulisan 'dyn_' biar nama parameternya asli
                try:
                    param_dinamis[param_name] = float(value) # Simpan sebagai angka
                except:
                    param_dinamis[param_name] = value # Simpan sebagai teks kalau gagal

        parameter_dinamis_json = json.dumps(param_dinamis)

        conn = get_db_connection()
        cursor = conn.cursor()
        
        update_query = "UPDATE qc_records SET parameter_dinamis=%s WHERE id=%s"
        cursor.execute(update_query, (parameter_dinamis_json, id_qc))
        conn.commit()
        
        cursor.close()
        conn.close()
        return redirect('/riwayat')
    except Exception as e:
        return f"Terjadi kesalahan saat mengedit data: {str(e)}", 400
    
@app.route('/dashboard')
def form_input():
    return render_template('dashboard.html')



@app.route('/api/get-produk/<int:id_produk>')
def get_produk(id_produk):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT parameter_dinamis FROM master_produk WHERE id = %s", (id_produk,))
    data = cursor.fetchone()
    cursor.close()
    conn.close()

    if not data:
        # Produk tidak ditemukan di database
        return jsonify({"parameter_dinamis": "[]"}), 404

    # PENTING: produk lama (sebelum ada kolom parameter_dinamis / belum pernah
    # diedit lewat halaman Settings) bisa punya nilai NULL di database.
    # Kalau ini tidak dijaga, frontend akan gagal parse dan parameter tidak
    # pernah muncul di Form Input. Kita pastikan selalu balikin JSON array valid.
    if not data.get('parameter_dinamis'):
        data['parameter_dinamis'] = "[]"

    return jsonify(data)

# =============================================================
# ROUTE RAHASIA UNTUK GENERATE DATA DUMMY (VERSI URUT & RAPI)
# =============================================================
@app.route('/api/generate-dummy')
def generate_dummy():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # KITA BERSIHKAN DULU DATA LAMA BIAR GRAFIKNYA NGGAK NUMPUK BERANTAKAN
    cursor.execute("DELETE FROM qc_records")
    
    # Mulai dari 3 hari yang lalu
    base_date = datetime.now() - timedelta(days=3)
    
    # Skenario Logis: 3 Hari beruntun. Tiap hari ada 3 Shift. Tiap shift ada 3 Pengecekan.
    # Total = 27 Data yang sangat berurutan.
    for day in range(4): 
        tanggal_berjalan = base_date + timedelta(days=day)
        tanggal_str = tanggal_berjalan.strftime('%Y-%m-%d')
        
        # Jadwal Shift Pabrik (Urut dari pagi sampai malam)
        urutan_shift = [
            {"shift": 1, "grup": "A"},
            {"shift": 2, "grup": "B"},
            {"shift": 3, "grup": "C"}
        ]
        
        for s in urutan_shift:
            urutan_waktu = ["AWAL", "TENGAH", "AKHIR"]
            
            for wkt in urutan_waktu:
                # Bikin skenario 3 titik error (merah) natural
                if day == 1 and s['shift'] == 2 and wkt == "TENGAH":
                    tebal_val = round(random.uniform(3.10, 3.15), 2)
                elif day == 2 and s['shift'] == 1 and wkt == "AKHIR":
                    tebal_val = round(random.uniform(3.30, 3.35), 2)
                elif day == 3 and s['shift'] == 3 and wkt == "AWAL":
                    tebal_val = round(random.uniform(3.30, 3.35), 2)
                else:
                    tebal_val = round(random.uniform(3.19, 3.27), 2)
                    
                param_dinamis = {
                    "Tebal Min": tebal_val,
                    "Output": round(random.uniform(100, 110), 1),
                    "Dosing": round(random.uniform(15, 20), 1)
                }
                
                query = """
                    INSERT INTO qc_records 
                    (id_produk, tanggal, shift, grup, mesin, waktu, parameter_dinamis) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (1, tanggal_str, s['shift'], s['grup'], "14", wkt, json.dumps(param_dinamis)))
                
    conn.commit()
    cursor.close()
    conn.close()
    
    return "<h1>✅ Data Lama Dihapus & Data Dummy URUT Berhasil Disuntikkan!</h1> <p>Silakan buka layar TV Dashboard lu.</p>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)