import mysql.connector
import os
from datetime import datetime
import pytz
import streamlit as st


def get_connection():
    # Mengambil data koneksi dari "Secrets" (Brankas Aman)
    return mysql.connector.connect(
        host=st.secrets["db_host"],
        user=st.secrets["db_user"],
        password=st.secrets["db_password"],
        database=st.secrets["db_name"],
        port=st.secrets["db_port"],
    )




def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Tabel Produk (Stok)
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS produk (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nama_barang VARCHAR(255) NOT NULL,
        harga_modal DECIMAL(10, 2) NOT NULL,
        harga_jual DECIMAL(10, 2) NOT NULL,
        stok_sekarang INT DEFAULT 0
    )
    """
    )

    # 2. Tabel Penjualan (Transaksi)
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS penjualan (
        id INT AUTO_INCREMENT PRIMARY KEY,
        produk_id INT,
        jumlah INT,
        total_harga DECIMAL(10, 2),
        untung DECIMAL(10, 2),
        metode_bayar ENUM('Tunai', 'Hutang'),
        tanggal TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (produk_id) REFERENCES produk(id)
    )
    """
    )

    # 3. Tabel Hutang Pelanggan
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS hutang_pelanggan (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nama_pelanggan VARCHAR(255) NOT NULL,
        jumlah_hutang DECIMAL(10, 2) DEFAULT 0,
        keterangan TEXT,
        tanggal_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    """
    )

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Database Warung Gatz Berhasil Diinisialisasi!")

from datetime import datetime
import pytz

def proses_transaksi(id_barang, jumlah_beli):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Ambil waktu sekarang khusus WIB (Asia/Jakarta)
        # Ini supaya jam di database sama persis dengan jam di laptop kamu
        zona_waktu = pytz.timezone('Asia/Jakarta')
        waktu_sekarang = datetime.now(zona_waktu).strftime('%Y-%m-%d %H:%M:%S')
        
        # 2. Ambil data stok dan harga
        cursor.execute("SELECT stok_sekarang, nama_barang, harga_jual, harga_modal FROM produk WHERE id = %s", (id_barang,))
        result = cursor.fetchone()
        
        if result and result[0] >= jumlah_beli:
            stok_skrg, nama, harga_j, harga_m = result
            total_jual = harga_j * jumlah_beli
            total_modal = harga_m * jumlah_beli
            untung = total_jual - total_modal
            
            # 3. Potong Stok
            cursor.execute("UPDATE produk SET stok_sekarang = %s WHERE id = %s", (stok_skrg - jumlah_beli, id_barang))
            
            # 4. Simpan ke Laporan (Kunci perbaikannya ada di kolom 'tanggal' dan '%s' terakhir)
            query_log = """
                INSERT INTO penjualan (id_barang, nama_barang, jumlah, harga_jual, harga_modal, total_harga, untung, tanggal)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query_log, (id_barang, nama, jumlah_beli, harga_j, harga_m, total_jual, untung, waktu_sekarang))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True, f"{nama} Terjual!"
            
        return False, "Stok tidak mencukupi atau barang tidak ditemukan."
        
    except Exception as e:
        return False, f"Error Database: {str(e)}"

# Tambahkan fungsi baru untuk menarik laporan
def ambil_laporan():
    import pandas as pd
    try:
        conn = get_connection()
        # Ambil 'id' (id transaksi untuk hapus) dan 'id_barang' (id sistem produk)
        query = """
            SELECT id, tanggal, nama_barang, jumlah, total_harga, untung, id_barang 
            FROM penjualan 
            ORDER BY tanggal DESC
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"Error: {e}")
        return pd.DataFrame()

def hapus_satu_laporan(id_transaksi):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = "DELETE FROM penjualan WHERE id = %s"
        cursor.execute(query, (id_transaksi,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error Hapus Laporan: {e}")
        return False

def reset_laporan():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM penjualan")
        # Reset juga urutan ID-nya biar mulai dari 1 lagi
        cursor.execute("ALTER TABLE penjualan AUTO_INCREMENT = 1")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error Reset Laporan: {e}")
        return False    

def update_barang(id_barang, nama, modal, jual, stok):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = """
            UPDATE produk 
            SET nama_barang = %s, harga_modal = %s, harga_jual = %s, stok_sekarang = %s 
            WHERE id = %s
        """
        cursor.execute(query, (nama, modal, jual, stok, id_barang))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error Update: {e}")
        return False
def hapus_barang(id_barang):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = "DELETE FROM produk WHERE id = %s"
        cursor.execute(query, (id_barang,))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error Hapus: {e}")
        return False


if __name__ == "__main__":
    init_db()
