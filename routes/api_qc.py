from flask import Blueprint, request, redirect, jsonify
import json
import pandas as pd
import numpy as np
from datetime import datetime
from database import get_db_connection

api_qc = Blueprint('api_qc', __name__)

@api_qc.route('/api/qc-input', methods=['POST'])
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
        parameter_dinamis = json.dumps(data.get('parameter_dinamis', {}))

        sql = "INSERT INTO qc_records (id_produk, tanggal, shift, grup, mesin, waktu, parameter_dinamis) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        val = (id_produk, tanggal, data.get('shift'), data.get('grup'), data.get('mesin'), data.get('waktu'), parameter_dinamis)
        
        cursor.execute(sql, val)
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({"status": "success", "message": "Data berhasil masuk database!"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@api_qc.route('/api/qc-data', methods=['GET'])
def get_qc_data():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT q.mesin, q.id_produk 
            FROM qc_records q
            INNER JOIN (
                SELECT mesin, MAX(id) as max_id 
                FROM qc_records 
                WHERE mesin IS NOT NULL 
                GROUP BY mesin
            ) latest ON q.mesin = latest.mesin AND q.id = latest.max_id
        """)
        kombinasi_list = cursor.fetchall()
        dashboard_data = []

        for komb in kombinasi_list:
            msn_asli = komb['mesin']
            id_prod = komb['id_produk']
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
            primary_param_name = "N/A"
            primary_param_val = 0
            primary_param_lcl = None
            primary_param_ucl = None
            
            try:
                curr_param = json.loads(current['parameter_dinamis']) if current['parameter_dinamis'] else {}
                if curr_param:
                    primary_param_name = list(curr_param.keys())[0]
                    primary_param_val = curr_param[primary_param_name]
            except:
                pass
                
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

            try:
                val_check = float(primary_param_val)
                is_out = False
                if primary_param_lcl is not None and val_check < float(primary_param_lcl): is_out = True
                if primary_param_ucl is not None and val_check > float(primary_param_ucl): is_out = True
                status_primary = "OUT" if is_out else "NORMAL"
            except:
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

@api_qc.route('/api/hapus-qc/<int:id_qc>', methods=['POST'])
def hapus_qc(id_qc):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM qc_records WHERE id = %s", (id_qc,))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/riwayat')
    except Exception as e:
        return f"Terjadi kesalahan saat menghapus data: {str(e)}", 400

@api_qc.route('/api/hapus-qc-bulk', methods=['POST'])
def hapus_qc_bulk():
    try:
        data = request.form.getlist('qc_ids')
        if not data:
            return redirect('/riwayat')
            
        conn = get_db_connection()
        cursor = conn.cursor()
        format_strings = ','.join(['%s'] * len(data))
        cursor.execute(f"DELETE FROM qc_records WHERE id IN ({format_strings})", tuple(data))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/riwayat')
    except Exception as e:
        return f"Terjadi kesalahan saat menghapus data: {str(e)}", 400

@api_qc.route('/api/edit-qc', methods=['POST'])
def edit_qc():
    try:
        id_qc = request.form.get('id')
        param_dinamis = {}
        for key, value in request.form.items():
            if key.startswith('dyn_'):
                param_name = key[4:]
                try:
                    param_dinamis[param_name] = float(value)
                except:
                    param_dinamis[param_name] = value

        parameter_dinamis_json = json.dumps(param_dinamis)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE qc_records SET parameter_dinamis=%s WHERE id=%s", (parameter_dinamis_json, id_qc))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/riwayat')
    except Exception as e:
        return f"Terjadi kesalahan saat mengedit data: {str(e)}", 400

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

@api_qc.route('/api/upload-excel', methods=['POST'])
def upload_excel():
    try:
        id_produk = request.form.get('id_produk')
        if not id_produk: return jsonify({"status": "error", "message": "Pilih produk terlebih dahulu"}), 400
        if 'file' not in request.files: return jsonify({"status": "error", "message": "Tidak ada file yang diunggah"}), 400
        file = request.files['file']
        if file.filename == '': return jsonify({"status": "error", "message": "File kosong"}), 400
        
        if file.filename.endswith('.csv'): df_raw = pd.read_csv(file, header=None)
        elif file.filename.endswith('.xlsx'): df_raw = pd.read_excel(file, header=None)
        else: return jsonify({"status": "error", "message": "Format harus .csv atau .xlsx"}), 400

        header_row_idx = 0
        for i, row in df_raw.iterrows():
            row_str = ' '.join(str(val).lower() for val in row.values)
            if 'tanggal' in row_str and ('shift' in row_str or 'mesin' in row_str):
                header_row_idx = i
                break
        
        file.seek(0)
        if file.filename.endswith('.csv'): df = pd.read_csv(file, header=header_row_idx)
        else: df = pd.read_excel(file, header=header_row_idx)

        df = df.iloc[:, 0:11]
        df.columns = [str(c).strip().title() for c in df.columns]

        STANDARD_COLS = {'No', 'Tanggal', 'Shift', 'Grup', 'Mesin', 'Waktu'}
        dynamic_cols = [col for col in df.columns if col not in STANDARD_COLS and "Unnamed" not in col and str(col).strip() != ""]

        if dynamic_cols:
            df = df.dropna(subset=dynamic_cols, how='all')

        identitas_cols = ['Tanggal', 'Shift', 'Grup', 'Mesin']
        def clean_float_str(val):
            if pd.isna(val): return val
            val_str = str(val)
            if val_str.endswith('.0'): return val_str[:-2]
            return val

        for col in identitas_cols:
            if col in df.columns:
                df[col] = df[col].ffill()
                df[col] = df[col].apply(clean_float_str)

        df = df.where(pd.notnull(df), None)

        conn = get_db_connection()
        cursor = conn.cursor()
        sukses_count = 0
        sql = "INSERT INTO qc_records (id_produk, tanggal, shift, grup, mesin, waktu, parameter_dinamis) VALUES (%s, %s, %s, %s, %s, %s, %s)"

        for index, row in df.iterrows():
            param_dinamis = {}
            for col in dynamic_cols:
                val = row.get(col)
                if pd.notna(val):
                    try:
                        f_val = float(val)
                        if not pd.isna(f_val): param_dinamis[col] = f_val
                    except:
                        param_dinamis[col] = str(val)

            val = (
                id_produk, parse_tanggal_indo(row.get('Tanggal')),
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
