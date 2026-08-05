# SPC Web App - Security & Deployment Checklist

Dokumen ini berisi daftar periksa (checklist) terkait keamanan dan praktik terbaik (*best practices*) sebelum aplikasi web SPC ini dirilis untuk digunakan secara penuh di pabrik (*Production*).

## 1. Hapus Fitur Auto-Login di phpMyAdmin
Saat ini, phpMyAdmin bisa diakses secara langsung tanpa perlu memasukkan username dan password. Hal ini sangat berbahaya untuk lingkungan produksi karena siapa pun di jaringan WiFi bisa mengakses database secara penuh.

**Tindakan yang harus dilakukan:**
- Buka file `docker-compose.yml`.
- Cari bagian konfigurasi `phpmyadmin`.
- Hapus atau beri komentar (`#`) pada dua baris berikut:
  ```yaml
  # - PMA_USER=root
  # - PMA_PASSWORD=rootpassword
  ```
- *Restart* docker dengan perintah `docker-compose down` dan `docker-compose up -d`.

## 2. Pindahkan Password ke File `.env` (Environment Variables)
Saat ini, kata sandi (password) database tertulis secara langsung (*hardcoded*) di dalam file `docker-compose.yml` dan `app.py`. Jika kode ini bocor atau disalin orang lain, akses ke database bisa disalahgunakan.

**Tindakan yang harus dilakukan:**
- Buat file baru bernama `.env` di folder utama aplikasi (sejajar dengan `docker-compose.yml`).
- Masukkan semua variabel rahasia ke file `.env` tersebut:
  ```env
  MYSQL_ROOT_PASSWORD=password_rahasia_baru
  MYSQL_USER=spc_user
  MYSQL_PASSWORD=password_spc_baru
  MYSQL_DATABASE=spc_database
  FLASK_SECRET_KEY=kunci_rahasia_flask_yang_rumit
  ```
- Ubah pengaturan di `docker-compose.yml` agar mengambil nilai dari file `.env` tersebut.
- Pastikan file `.env` **TIDAK** pernah diunggah ke GitHub atau dibagikan sembarangan (masukkan ke dalam file `.gitignore`).

## 3. Keamanan Jaringan Lokal (WiFi/LAN)
Aplikasi ini berjalan di satu komputer *Server/Host*. Siapa pun yang terhubung ke jaringan (WiFi/Kabel) yang sama bisa membuka aplikasi (Port 5000) dan database (Port 8080).

**Tindakan yang harus dilakukan:**
- Pastikan hanya karyawan berwenang yang memiliki akses ke WiFi/Jaringan lokal tempat server berada.
- Konfigurasi *Windows Defender Firewall* (atau *Firewall* sistem operasi server) agar hanya membuka Port `5000` (untuk aplikasi web) dan Port `8080` (untuk phpMyAdmin) secara terbatas, atau matikan Port `8080` jika phpMyAdmin tidak sedang digunakan.

## 4. Refactoring Kode (Pembersihan Struktur File)
Saat ini, semua logika aplikasi (koneksi database, pengaturan rute URL, pemrosesan data, dll) menumpuk di dalam satu file `app.py` yang ukurannya sangat besar (>700 baris).

**Tindakan yang disarankan:**
- Pecah file `app.py` menjadi struktur MVC (*Model-View-Controller*) atau modul yang lebih rapi:
  - `database.py`: Khusus untuk koneksi MySQL.
  - `routes/`: Folder untuk memisahkan jalur halaman (dashboard, settings, riwayat).
  - `utils.py`: Khusus untuk fungsi tambahan seperti ekspor Excel.
- Manfaat: Kode jauh lebih mudah dirawat, minim *bug* saat ada pembaruan fitur, dan risiko celah keamanan akibat kode yang berantakan akan menurun drastis.

## 5. Solusi Jaringan Alternatif (Jika WiFi Pabrik Berbeda Jaringan)
Jika router di pabrik dan kantor tidak berada dalam satu jaringan (berbeda segmen IP) dan tim IT tidak bisa membantu menyatukannya, Anda memiliki dua solusi mudah tanpa harus mengubah kabel fisik:

**Opsi A: Menggunakan "Tunneling" (Cloudflare Tunnel / Ngrok) - Paling Mudah**
- **Konsep:** Membuat link website publik sementara/permanen (contoh: `https://pabrik.trycloudflare.com`) yang menembus langsung ke server lokal Anda.
- **Kelebihan:** Tablet cukup menggunakan koneksi internet apa saja (WiFi pabrik atau SIM Card) untuk membuka link tersebut. Sangat mudah dan gratis.
- **Syarat:** Komputer Server di kantor harus memiliki koneksi internet.

**Opsi B: Menggunakan Jaringan LAN Virtual (Tailscale / ZeroTier) - Sangat Aman**
- **Konsep:** Menginstal aplikasi Tailscale di Komputer Server dan di Tablet. Aplikasi ini akan membuat "kabel jaringan gaib" melalui internet sehingga Server dan Tablet merasa berada di ruangan dan WiFi yang sama persis.
- **Kelebihan:** Sangat aman karena tertutup untuk publik (hanya device yang login Tailscale yang bisa akses). Gratis untuk penggunaan skala kecil.
- **Syarat:** Komputer dan Tablet harus memiliki koneksi internet.

