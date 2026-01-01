import streamlit as st
import pandas as pd
from database_helper import get_connection

st.set_page_config(page_title="Gatz Warung Digital", layout="wide")

# --- FUNGSI DATABASE ---
def simpan_barang(nama, modal, jual, stok):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = "INSERT INTO produk (nama_barang, harga_modal, harga_jual, stok_sekarang) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (nama, modal, jual, stok))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error Simpan: {e}")
        return False

def ambil_stok():
    conn = get_connection()
    query = "SELECT id, nama_barang, harga_modal, harga_jual, stok_sekarang FROM produk"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# --- UI STREAMLIT ---
st.title("🛒 Gatz Warung Digital")

tab1, tab2, tab3, tab4 = st.tabs(["🛍️ Kasir", "📦 Stok Barang", "📝 Laporan Keuangan", "🤖 AI Manager"])

# --- TAB 1: KASIR ---
with tab1:
    st.subheader("🛍️ Terminal Kasir")
    
    # Inisialisasi Keranjang Belanja di Session State jika belum ada
    if 'keranjang' not in st.session_state:
        st.session_state.keranjang = []

    df_kasir = ambil_stok()
    if not df_kasir.empty:
        col_k1, col_k2 = st.columns([2, 1])
        
        with col_k1:
            # 1. PILIH BARANG
            pilihan_id = st.selectbox(
                "Pilih Barang", 
                options=df_kasir['id'].tolist(),
                format_func=lambda x: df_kasir[df_kasir['id'] == x]['nama_barang'].values[0]
            )
            data_p = df_kasir[df_kasir['id'] == pilihan_id].iloc[0]
            
            st.info(f"💰 Harga: Rp {int(data_p['harga_jual']):,} | 📦 Stok: {data_p['stok_sekarang']}".replace(",", "."))
            
            # 2. INPUT JUMLAH & TOMBOL TAMBAH
            c1, c2 = st.columns(2)
            qty = c1.number_input("Jumlah", min_value=1, max_value=int(data_p['stok_sekarang']), step=1)
            
            if c2.button("➕ Tambah ke Pesanan", use_container_width=True):
                # Masukkan ke list keranjang
                item = {
                    "id": pilihan_id,
                    "nama": data_p['nama_barang'],
                    "harga": int(data_p['harga_jual']),
                    "qty": qty,
                    "subtotal": int(data_p['harga_jual']) * qty
                }
                st.session_state.keranjang.append(item)
                st.toast(f"{data_p['nama_barang']} masuk keranjang!")

        with col_k2:
            st.write("### 📝 Daftar Pesanan")
            if st.session_state.keranjang:
                total_belanja = 0
                for i, item in enumerate(st.session_state.keranjang):
                    st.write(f"{i+1}. **{item['nama']}** x{item['qty']} = Rp {item['subtotal']:,}".replace(",", "."))
                    total_belanja += item['subtotal']
                
                st.divider()
                st.metric("Total Bayar", f"Rp {total_belanja:,}".replace(",", "."))
                
                # TOMBOL PROSES SEMUA
                if st.button("🚀 PROSES BAYAR SEKARANG", type="primary", use_container_width=True):
                    from database_helper import proses_transaksi
                    sukses_semua = True
                    for item in st.session_state.keranjang:
                        berhasil, pesan = proses_transaksi(item['id'], item['qty'])
                        if not berhasil:
                            sukses_semua = False
                            st.error(f"Gagal di {item['nama']}: {pesan}")
                    
                    if sukses_semua:
                        st.balloons()
                        st.success("Semua pesanan berhasil diproses!")
                        st.session_state.keranjang = [] # Kosongkan keranjang
                        st.rerun()
                
                if st.button("🗑️ Kosongkan Keranjang"):
                    st.session_state.keranjang = []
                    st.rerun()
            else:
                st.write("Keranjang masih kosong.")
    else:
        st.warning("Stok kosong!")

# --- TAB 2: STOK BARANG ---
with tab2:
    st.subheader("Manajemen Stok")
    
    # 1. FORM TAMBAH BARANG
    with st.expander("➕ Tambah Barang Baru"):
        with st.form("form_tambah", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            n_baru = col_a.text_input("Nama Barang")
            s_baru = col_b.number_input("Stok Awal", min_value=0)
            m_baru = col_a.number_input("Harga Modal (Rp)", min_value=0, step=500)
            j_baru = col_b.number_input("Harga Jual (Rp)", min_value=0, step=500)
            if st.form_submit_button("Simpan Barang Baru"):
                if n_baru and simpan_barang(n_baru, m_baru, j_baru, s_baru):
                    st.success(f"{n_baru} berhasil ditambah!")
                    st.rerun()

    # 2. TABEL DAFTAR STOK
    st.write("### Daftar Stok Saat Ini")
    df_stok = ambil_stok()
    if not df_stok.empty:
        # 1. Kita buat kolom 'No' urut untuk tampilan cantik di depan
        df_tampilan = df_stok.copy()
        df_tampilan.insert(0, 'No', range(1, 1 + len(df_tampilan)))
        
        # 2. Kita susun urutan kolomnya: ID asli kita pindah ke paling belakang (ujung kanan)
        kolom_rapi = [c for c in df_tampilan.columns if c != 'id'] + ['id']
        df_tampilan = df_tampilan[kolom_rapi]
        
        st.dataframe(
            df_tampilan,
            column_config={
                "No": st.column_config.NumberColumn("No", width="small"),
                "nama_barang": "Nama Produk",
                "harga_modal": st.column_config.NumberColumn("Modal", format="Rp %d"),
                "harga_jual": st.column_config.NumberColumn("Jual", format="Rp %d"),
                "stok_sekarang": st.column_config.NumberColumn("Stok", format="%d unit"),
                "id": st.column_config.NumberColumn("ID Sistem", format="%d"), # ID ditaruh di ujung
            },
            use_container_width=True,
            hide_index=True
        )
        # 3. FITUR EDIT & HAPUS
        st.write("---")
        col_edit, col_hapus = st.columns(2)

        with col_edit:
            st.write("📝 **Edit Data Barang**")
            id_edit = st.selectbox("Pilih ID Barang untuk Diedit", df_stok['id'])
            # Ambil data lama untuk default value
            data_lama = df_stok[df_stok['id'] == id_edit].iloc[0]
            
            with st.popover("Buka Form Edit"):
                n_upd = st.text_input("Ubah Nama", value=data_lama['nama_barang'])
                m_upd = st.number_input("Ubah Modal", value=int(data_lama['harga_modal']))
                j_upd = st.number_input("Ubah Jual", value=int(data_lama['harga_jual']))
                s_upd = st.number_input("Ubah Stok", value=int(data_lama['stok_sekarang']))
                
                if st.button("Update Sekarang"):
                    from database_helper import update_barang
                    if update_barang(id_edit, n_upd, m_upd, j_upd, s_upd):
                        st.success("Data berhasil diupdate!")
                        st.rerun()

        with col_hapus:
            st.write("🗑️ **Hapus Barang**")
            id_del = st.selectbox("Pilih ID Barang untuk Dihapus", df_stok['id'])
            if st.button("🔥 HAPUS PERMANEN", type="primary"):
                from database_helper import hapus_barang
                if hapus_barang(id_del):
                    st.warning(f"ID {id_del} telah dihapus.")
                    st.rerun()
            else:
                st.info("Belum ada data barang.")
           
    # Tabel Tampilan Stok
    st.write("### Daftar Stok Saat Ini")
    data_stok = ambil_stok()
    if not data_stok.empty:
        st.dataframe(data_stok, use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada barang di database. Ayo input dulu!")

# --- TAB 3: LAPORAN ---
with tab3:
    st.subheader("📊 Laporan Keuangan")
    from database_helper import ambil_laporan, hapus_satu_laporan, reset_laporan

    df_lap = ambil_laporan()

    if not df_lap.empty:
        # Ringkasan Cuan
        total_omzet = df_lap['total_harga'].sum()
        total_untung = df_lap['untung'].sum()

        c1, c2 = st.columns(2)
        c1.metric("Total Omzet", f"Rp {total_omzet:,}".replace(",", "."))
        c2.metric("Untung Bersih", f"Rp {total_untung:,}".replace(",", "."), delta="Cuan!")

        # Tabel Laporan
        df_lap_tampil = df_lap.copy()
        df_lap_tampil.insert(0, 'No', range(1, 1 + len(df_lap_tampil)))

        st.write("### Detail Transaksi Terakhir")
        st.dataframe(
            df_lap_tampil,
            column_order=("No", "tanggal", "nama_barang", "jumlah", "total_harga", "untung", "id_barang"),
            column_config={
                "No": st.column_config.NumberColumn("No", width="small"),
               "tanggal": st.column_config.DatetimeColumn(
                    "Waktu",
                    format="DD/MM/YYYY HH:mm", # Ini format paling rapi
                    ),
                "total_harga": st.column_config.NumberColumn("Total Jual", format="Rp %d"),
                "untung": st.column_config.NumberColumn("Untung", format="Rp %d"),
            },
            use_container_width=True, 
            hide_index=True
        )

        st.divider()

        # FITUR HAPUS
        col_h1, col_h2 = st.columns(2)
        with col_h1:
            st.write("🗑️ **Hapus Satu Transaksi**")
            
            # 1. Bikin list label yang isinya cuma Nomor Urut (1, 2, 3...)
            # Kita mapping 'Nomor Urut' ini ke 'ID Database' yang asli
            pilihan_label = []
            map_id = {} 
            
            # Kita loop data laporan yang ada di tabel
            for i, row in df_lap.iterrows():
                nomor_tabel = i + 1 # Ini yang bikin jadi 1, 2, 3...
                label = f"Nomor: {nomor_tabel} - {row['nama_barang']}"
                pilihan_label.append(label)
                map_id[label] = row['id'] # Simpan ID database aslinya (misal 120001)
            
            # 2. Selectbox sekarang cuma nampilin nomor urut yang rapi
            pilihan_user = st.selectbox(
                "Pilih Nomor di Tabel untuk Dihapus", 
                options=pilihan_label
            )
            
            if st.button("Hapus Transaksi Ini"):
                from database_helper import hapus_satu_laporan
                
                # 3. Ambil ID asli (90004/120001) lewat label nomor urut yang dipilih
                id_asli = map_id[pilihan_user]
                
                if hapus_satu_laporan(id_asli):
                    st.success(f"Transaksi nomor {pilihan_user.split(' ')[1]} berhasil dihapus!")
                    st.rerun()

        with col_h2:
            st.write("⚠️ **Zona Bahaya**")
            if st.button("🔥 RESET SEMUA LAPORAN", type="primary"):
                # Kita kasih konfirmasi sederhana pakai popover atau langsung
                if reset_laporan():
                    st.warning("Semua data penjualan telah dikosongkan!")
                    st.rerun()
    else:
        st.info("Belum ada data penjualan.")

# --- TAB LAIN (Coming Soon) ---
# with tab1: st.info("Fitur Kasir akan nyambung ke Stok setelah kamu input barang.")
# with tab3: st.info("Fitur Hutang untuk mencatat bon pelanggan.")
# with tab4: st.info("AI Manager siap menganalisis keuntunganmu.")
