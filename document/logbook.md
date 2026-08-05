# Logbook Project Magang SPC Web App

## 20 Juli 2026
- Bersihin database dari data-data testing lama (factory reset via docker) biar rapi dan penghitung ID balik lagi dari 1.
- Ngapus fitur upload excel di halaman settings. Soalnya fitur ini cuma kepake pas awal setup, mending dihapus aja biar tampilan UI-nya ga keramean.

## 21 Juli 2026
- Diskusi soal rencana demo ke mentor nanti karena kita ga punya dokumen requirement (PRD) yang pasti. Jadi fokusnya lebih ke bikin aplikasinya keliatan "hidup".
- Bikin script python buat nyuntikin data dummy otomatis. Bikin sekitar 144 data palsu buat 7 hari ke belakang. Sengaja dikasih sedikit error (outlier) biar grafiknya naik turun persis kayak di pabrik beneran.
- Benerin logika data dummy biar satu mesin cuma ngerjain satu produk aja (sebelumnya sempet bug 1 mesin ngerjain banyak produk di jam yang sama).
- Ngapus tombol ganti "Bar Chart" di dashboard. Sekarang murni dilock pake "Line Chart" semua karena buat mantau quality control (SPC) emang wajib pake garis. Kebetulan ini juga otomatis ngeberesin bug grafik yang suka gepeng pas layarnya diganti.

## 22 Juli 2026
- Bikin file logbook ini buat nulis catetan progres harian.
- Diskusi awal soal keamanan dan alur aplikasi. Awalnya sempet kepikiran mau bikin sistem login, tapi setelah dipikir-pikir ditunda dulu nunggu arahan dari mentor biar aplikasinya ga keribetan.

## 23 Juli 2026
- Ngecek masalah layout dashboard yang agak kepotong di bawah kalau dibuka di laptop 16-inch. Ternyata itu karena zoom dari Windows. Kalau nanti dicolok ke TV 1080p pabrik ukurannya bakal pas kok.

## 24 Juli 2026
- Review ulang alur kerja aplikasi dari awal sampe akhir buat nyiapin bahan demo, mastiin ga ada error yang kelewat biar aplikasinya bener-bener solid pas dipresentasiin ke mentor.

## Senin, 27 Juli 2026
- Melakukan konsultasi usulan teknis secara intensif dengan Pembimbing Lapangan dan mempresentasikan hasil *stress-testing* aplikasi menggunakan injeksi data simulasi.

## Selasa, 28 Juli 2026
- Melakukan penyesuaian akhir (*minor revision*) pada antarmuka dan stabilitas sistem berdasarkan masukan dari Pembimbing Lapangan, serta merapikan dokumentasi arsitektur perangkat lunak.

## Rabu, 29 Juli 2026
- Mendemonstrasikan dan melakukan uji coba langsung aplikasi *QA Monitoring Dashboard* bersama staf *Quality Assurance* sebagai bentuk evaluasi akhir dan persiapan serah terima (*User Acceptance Testing*).

## Kamis, 30 Juli 2026
- Mengompilasi seluruh data pendukung, aset *screenshot* aplikasi, dan catatan *logbook* mingguan untuk memulai penyusunan kerangka Laporan Kerja Praktik (Bab I dan Bab II).

## Jumat, 31 Juli 2026
- Melanjutkan penyusunan draf Laporan Kerja Praktik (Bab III dan Bab IV) yang difokuskan pada analisis kritis kesesuaian rencana teknis dengan implementasi penyelesaian fitur di lapangan.
