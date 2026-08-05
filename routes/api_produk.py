from flask import Blueprint, request, redirect, jsonify
import json
import pandas as pd
import numpy as np
from datetime import datetime
from database import get_db_connection

api_produk = Blueprint('api_produk', __name__)

@api_produk.route('/api/tambah-produk', methods=['POST'])
def tambah_produk():
    nama_produk = request.form.get('nama_produk')
    raw_params = request.form.get('parameter_dinamis')
    
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
    query = "INSERT INTO master_produk (nama_produk, parameter_dinamis) VALUES (%s, %s)"
    cursor.execute(query, (nama_produk, parameters_json))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/settings')

@api_produk.route('/api/edit-produk', methods=['POST'])
def edit_produk():
    id_produk = request.form.get('id')
    nama_produk = request.form.get('nama_produk')
    raw_params = request.form.get('parameter_dinamis')
    
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
    query = "UPDATE master_produk SET nama_produk=%s, parameter_dinamis=%s WHERE id=%s"
    cursor.execute(query, (nama_produk, parameters_json, id_produk))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/settings')

@api_produk.route('/api/hapus-produk/<int:id_produk>', methods=['POST'])
def hapus_produk(id_produk):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM master_produk WHERE id = %s", (id_produk,))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/settings')
    except Exception as e:
        return f"Terjadi kesalahan saat menghapus data: {str(e)}", 400

@api_produk.route('/api/get-produk/<int:id_produk>')
def get_produk(id_produk):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT parameter_dinamis FROM master_produk WHERE id = %s", (id_produk,))
    data = cursor.fetchone()
    cursor.close()
    conn.close()

    if not data:
        return jsonify({"parameter_dinamis": "[]"}), 404

    if not data.get('parameter_dinamis'):
        data['parameter_dinamis'] = "[]"

    return jsonify(data)

@api_produk.route('/api/upload-produk', methods=['POST'])
def upload_produk():
    if 'excel_file' not in request.files:
        return "Tidak ada file Excel yang diunggah", 400
        
    file = request.files['excel_file']
    id_produk = request.form.get('id_produk')
    
    if file.filename == '':
        return "Pilih file Excel terlebih dahulu", 400
    if not id_produk:
        return "Pilih produk tujuan terlebih dahulu", 400

    try:
        df_raw = pd.read_excel(file, header=None)
        header_idx = 0
        for i in range(min(10, len(df_raw))):
            row_vals = [str(x).strip().lower() for x in df_raw.iloc[i].values]
            if 'tanggal' in row_vals and 'shift' in row_vals:
                header_idx = i
                break
                
        df_raw.columns = df_raw.iloc[header_idx].astype(str).str.strip().str.lower()
        df = df_raw.iloc[header_idx+1:].reset_index(drop=True)
        
        wajib = ['tanggal', 'shift', 'mesin', 'waktu']
        for w in wajib:
            if w not in df.columns:
                return f"Gagal: Kolom wajib '{w}' tidak ditemukan di Excel. Pastikan ejaannya benar.", 400
                
        kolom_dibuang = ['no']
        for col in df.columns:
            if str(col).startswith('status') or str(col) == 'kesimpulan proses':
                kolom_dibuang.append(col)
        df = df.drop(columns=[c for c in kolom_dibuang if c in df.columns])
        
        df[['tanggal', 'shift', 'mesin']] = df[['tanggal', 'shift', 'mesin']].replace(r'^\s*$', np.nan, regex=True).ffill()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for _, row in df.iterrows():
            if pd.isna(row['waktu']) or str(row['waktu']).strip() == '':
                continue
                
            raw_tanggal = row['tanggal']
            try:
                tgl_str = raw_tanggal.strftime('%Y-%m-%d') if hasattr(raw_tanggal, 'strftime') else str(raw_tanggal).split(' ')[0]
            except:
                tgl_str = datetime.now().strftime('%Y-%m-%d')
                
            shift = str(row['shift']).strip() if not pd.isna(row['shift']) else "-"
            grup = shift[-1] if len(shift) > 1 and shift[-1].isalpha() else "-"
            shift_num = shift[:-1] if len(shift) > 1 and shift[-1].isalpha() else shift
            
            mesin = str(row['mesin']).strip() if not pd.isna(row['mesin']) else "1"
            waktu = str(row['waktu']).strip() if not pd.isna(row['waktu']) else "AWAL"
            
            param_dinamis = {}
            for col in df.columns:
                if col not in wajib:
                    val = row[col]
                    if not pd.isna(val):
                        param_dinamis[col.title()] = val
                        
            param_json = json.dumps(param_dinamis)
            sql = "INSERT INTO qc_records (id_produk, tanggal, shift, grup, mesin, waktu, parameter_dinamis) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(sql, (id_produk, tgl_str, shift_num, grup, mesin, waktu, param_json))
            
        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/settings')
    except Exception as e:
        return f"Terjadi kesalahan saat memproses Excel: {str(e)}", 500
