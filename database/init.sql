-- 1. TABEL MASTER PRODUK
CREATE TABLE IF NOT EXISTS master_produk (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nama_produk VARCHAR(100) NOT NULL,
    parameter_dinamis JSON,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Masukkan 2 data awal sebagai contoh (Bisa dihapus nanti di web)
INSERT INTO master_produk (nama_produk, parameter_dinamis) 
VALUES 
('Pipa PVC AW 3', '[{"name": "Tebal", "lcl": 3.18, "ucl": 3.28, "chartType": "Line"}, {"name": "Output Mesin", "lcl": 590, "ucl": 610, "chartType": "Line"}]'),
('Pipa Conduit 20mm', '[{"name": "Tebal", "lcl": 1.40, "ucl": 1.60, "chartType": "Line"}]');

-- 2. TABEL QC RECORDS (Murni pakai JSON)
CREATE TABLE IF NOT EXISTS qc_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_produk INT NOT NULL,
    tanggal DATE NOT NULL,
    shift VARCHAR(10) NOT NULL,
    grup VARCHAR(10) NOT NULL,
    mesin VARCHAR(10) NOT NULL,
    waktu VARCHAR(20) NOT NULL,
    parameter_dinamis JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_produk) REFERENCES master_produk(id) ON DELETE CASCADE
);

-- 3. TABEL USERS (Buat jaga-jaga kalau nanti butuh login lagi)
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nama_lengkap VARCHAR(100)
);