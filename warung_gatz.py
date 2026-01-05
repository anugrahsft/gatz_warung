import streamlit as st
import pandas as pd
from database_helper import get_connection

# 1. SETTING HALAMAN & HAPUS WATERMARK (CSS)
st.set_page_config(page_title="Gatz Warung Digital", layout="wide")
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    /* Menghilangkan padding berlebih di mobile */
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


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


# --- UI UTAMA ---
st.title("🛒 Gatz Warung Digital")

tab1, tab2, tab3, tab4 = st.tabs(
    ["🛍️ Kasir", "📦 Stok Barang", "📝 Laporan Keuangan", "🤖 AI Manager"]
)

# --- TAB 1: KASIR ---
with tab1:
    st.subheader("🛍️ Terminal Kasir")
    if "keranjang" not in st.session_state:
        st.session_state.keranjang = []

    df_kasir = ambil_stok()
    if not df_kasir.empty:
        col_k1, col_k2 = st.columns([2, 1])
        with col_k1:
            pilihan_id = st.selectbox(
                "Pilih Barang",
                options=df_kasir["id"].tolist(),
                format_func=lambda x: df_kasir[df_kasir["id"] == x][
                    "nama_barang"
                ].values[0],
            )
            data_p = df_kasir[df_kasir["id"] == pilihan_id].iloc[0]
            st.info(
                f"💰 Harga: Rp {int(data_p['harga_jual']):,} | 📦 Stok: {data_p['stok_sekarang']}".replace(
                    ",", "."
                )
            )

            c1, c2 = st.columns(2)
            qty = c1.number_input(
                "Jumlah", min_value=1, max_value=int(data_p["stok_sekarang"]), step=1
            )
            if c2.button("➕ Tambah ke Pesanan", use_container_width=True):
                item = {
                    "id": pilihan_id,
                    "nama": data_p["nama_barang"],
                    "harga": int(data_p["harga_jual"]),
                    "qty": qty,
                    "subtotal": int(data_p["harga_jual"]) * qty,
                }
                st.session_state.keranjang.append(item)
                st.toast(f"{data_p['nama_barang']} masuk keranjang!")

        with col_k2:
            st.write("### 📝 Daftar Pesanan")
            if st.session_state.keranjang:
                total_belanja = 0
                for i, item in enumerate(st.session_state.keranjang):
                    st.write(
                        f"{i+1}. **{item['nama']}** x{item['qty']} = Rp {item['subtotal']:,}".replace(
                            ",", "."
                        )
                    )
                    total_belanja += item["subtotal"]
                st.divider()
                st.metric("Total Bayar", f"Rp {total_belanja:,}".replace(",", "."))

                if st.button(
                    "🚀 PROSES BAYAR SEKARANG", type="primary", use_container_width=True
                ):
                    from database_helper import proses_transaksi

                    sukses_semua = True
                    for item in st.session_state.keranjang:
                        berhasil, pesan = proses_transaksi(item["id"], item["qty"])
                        if not berhasil:
                            sukses_semua = False
                            st.error(f"Gagal di {item['nama']}: {pesan}")
                    if sukses_semua:
                        st.balloons()
                        st.success("Semua pesanan berhasil diproses!")
                        st.session_state.keranjang = []
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

    df_stok = ambil_stok()
    if not df_stok.empty:
        df_tampilan = df_stok.copy()
        df_tampilan.insert(0, "No", range(1, 1 + len(df_tampilan)))
        st.dataframe(df_tampilan, use_container_width=True, hide_index=True)

        st.divider()
        col_edit, col_hapus = st.columns(2)
        with col_edit:
            st.write("📝 **Edit Data Barang**")
            id_edit = st.selectbox("Pilih ID Barang untuk Diedit", df_stok["id"])
            data_lama = df_stok[df_stok["id"] == id_edit].iloc[0]
            with st.popover("Buka Form Edit"):
                n_upd = st.text_input("Ubah Nama", value=data_lama["nama_barang"])
                m_upd = st.number_input(
                    "Ubah Modal", value=int(data_lama["harga_modal"])
                )
                j_upd = st.number_input("Ubah Jual", value=int(data_lama["harga_jual"]))
                s_upd = st.number_input(
                    "Ubah Stok", value=int(data_lama["stok_sekarang"])
                )
                if st.button("Update Sekarang"):
                    from database_helper import update_barang

                    if update_barang(id_edit, n_upd, m_upd, j_upd, s_upd):
                        st.success("Data diupdate!")
                        st.rerun()
        with col_hapus:
            st.write("🗑️ **Hapus Barang**")
            id_del = st.selectbox("Pilih ID Barang untuk Dihapus", df_stok["id"])
            if st.button("🔥 HAPUS PERMANEN", type="primary"):
                from database_helper import hapus_barang

                if hapus_barang(id_del):
                    st.warning(f"ID {id_del} dihapus.")
                    st.rerun()

# --- TAB 3: LAPORAN (SUDAH FIX KEYERROR) ---
with tab3:
    st.subheader("📊 Laporan Keuangan")
    from database_helper import ambil_laporan, hapus_satu_laporan, reset_laporan

    df_lap = ambil_laporan()

    if not df_lap.empty:
        total_omzet = df_lap["total_harga"].sum()
        total_untung = df_lap["untung"].sum()
        c1, c2 = st.columns(2)
        c1.metric("Total Omzet", f"Rp {total_omzet:,}".replace(",", "."))
        c2.metric(
            "Untung Bersih", f"Rp {total_untung:,}".replace(",", "."), delta="Cuan!"
        )

        df_lap_tampil = df_lap.copy()
        df_lap_tampil.insert(0, "No", range(1, 1 + len(df_lap_tampil)))

        st.write("### Detail Transaksi Terakhir")
        st.dataframe(
            df_lap_tampil,
            column_order=(
                "No",
                "tanggal",
                "nama_barang",
                "jumlah",
                "total_harga",
                "untung",
            ),
            column_config={
                "No": st.column_config.NumberColumn("No", width="small"),
                "tanggal": st.column_config.DatetimeColumn(
                    "Waktu", format="DD/MM/YY HH:mm"
                ),
                "total_harga": st.column_config.NumberColumn(
                    "Total Jual", format="Rp %d"
                ),
                "untung": st.column_config.NumberColumn("Untung", format="Rp %d"),
            },
            use_container_width=True,
            hide_index=True,
        )

        st.divider()
        col_h1, col_h2 = st.columns(2)
        with col_h1:
            st.write("🗑️ **Hapus Satu Transaksi**")
            pilihan_label = []
            map_id = {}
            for i, row in df_lap.iterrows():
                nomor_tabel = i + 1
                # DISINI FIX-NYA: Kita pake row['tanggal'] bukan row['Waktu']
                label = f"{nomor_tabel}. {row['nama_barang']} ({row['tanggal']})"
                pilihan_label.append(label)
                map_id[label] = row["id"]

            pilihan_user = st.selectbox(
                "Pilih Nomor untuk Dihapus", options=pilihan_label
            )
            if st.button("Hapus Transaksi Ini"):
                id_asli = map_id[pilihan_user]
                if hapus_satu_laporan(id_asli):
                    st.success("Berhasil dihapus!")
                    st.rerun()

        with col_h2:
            st.write("⚠️ **Zona Bahaya**")
            if st.button("🔥 RESET SEMUA LAPORAN", type="primary"):
                if reset_laporan():
                    st.warning("Data dikosongkan!")
                    st.rerun()
    else:
        st.info("Belum ada data penjualan.")

# --- TAB 4: AI MANAGER ---
with tab4:
    st.header("🤖 AI Business Manager")
    st.write("Tanya AI tentang strategi stok atau keuntungan!")
    user_ask = st.chat_input("Tanya sesuatu ke AI Manager...")
    if user_ask:
        with st.chat_message("user"):
            st.write(user_ask)
        df_laporan = ambil_laporan()
        konteks_data = df_laporan.to_string(index=False)
        with st.chat_message("assistant"):
            with st.spinner("AI lagi mikir..."):
                from database_helper import tanya_ai_manager

                jawaban = tanya_ai_manager(user_ask, konteks_data)
                st.write(jawaban)
