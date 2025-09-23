import streamlit as st
import pandas as pd
from collections import Counter
from datetime import datetime
from packaging import version
import plotly.express as px
import plotly.graph_objects as go
import io
import os
import json
import re
import logging

# Logging ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def compare_versions(v1, v2):
    """İki versiyonu karşılaştır - v1 <= v2 ise True"""
    try:
        return version.parse(str(v1)) <= version.parse(str(v2))
    except:
        # Version parsing başarısız olursa string karşılaştırması
        return str(v1) <= str(v2)

def is_version_higher(v1, v2):
    """v1 > v2 ise True döndür"""
    try:
        return version.parse(str(v1)) > version.parse(str(v2))
    except:
        return str(v1) > str(v2)

def format_date(date_str):
    """
    Tarihi 2025-08-06 11:35:41 formatından 2025-08-06 formatına çevirir
    """
    if not date_str or pd.isna(date_str):
        return ""
    
    # Sadece tarih kısmını al (saat kısmını kes)
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', str(date_str))
    return date_match.group(1) if date_match else str(date_str)

def scan_csv_files():
    """Mevcut CSV dosyalarını tara"""
    csv_files = []
    
    # Mevcut dizindeki CSV dosyları
    for file in os.listdir('.'):
        if file.endswith('.csv'):
            csv_files.append(file)
    
    return csv_files

def process_version_fixing(df, show_progress=True):
    """Versiyon düzenleme işlemini yap - YENİ MANTIK"""
    
    if df is None or df.empty:
        return df, {"error": "Boş DataFrame"}
    
    # Gerekli sütunları kontrol et
    if 'app_version' not in df.columns:
        return df, {"error": "app_version sütunu bulunamadı"}
    
    if 'date' not in df.columns:
        return df, {"error": "date sütunu bulunamadı"}
    
    if show_progress:
        progress_bar = st.progress(0)
        status_text = st.empty()
    
    results = {}
    
    # DataFrame'i kopyala
    df = df.copy()
    
    # İlk durum analizi
    if show_progress:
        status_text.text("📊 Başlangıç durumu analiz ediliyor...")
        progress_bar.progress(10)
    
    # app_version sütununu string'e çevir ve boş değerleri tespit et
    df['app_version'] = df['app_version'].astype(str)
    missing_versions = (df['app_version'].isna()) | (df['app_version'] == '') | (df['app_version'] == 'nan')
    
    results['total_records'] = len(df)
    results['missing_versions_count'] = missing_versions.sum()
    
    if show_progress:
        status_text.text(f"📊 {results['missing_versions_count']} boş versiyon tespit edildi...")
    
    # Eğer hiç boş versiyon yoksa
    if results['missing_versions_count'] == 0:
        results['final_missing_count'] = 0
        results['updated_count'] = 0
        results['valid_versions'] = []
        results['user_error_versions'] = []
        results['version_ranges'] = []
        return df, results
    
    # Tarih sütununu datetime'a çevir
    try:
        df['date'] = pd.to_datetime(df['date'])
    except Exception as e:
        return df, {"error": f"Tarih sütunu çevrilemedi: {e}"}
    
    if show_progress:
        status_text.text("📅 Versiyon tarihleri analiz ediliyor...")
        progress_bar.progress(30)
    
    # Her versiyonun ilk görüldüğü tarihi bul
    version_first_dates = {}
    non_empty_data = df[df['app_version'].notna() & (df['app_version'] != '') & (df['app_version'] != 'nan')]
    
    for version_name in non_empty_data['app_version'].unique():
        version_data = non_empty_data[non_empty_data['app_version'] == version_name]
        first_date = version_data['date'].min().date()
        version_first_dates[version_name] = first_date
    
    # Versiyonları ilk görülme tarihine göre sırala
    sorted_versions = sorted(version_first_dates.items(), key=lambda x: x[1])
    results['original_versions'] = sorted_versions
    
    if show_progress:
        status_text.text("🔍 Versiyon mantığı analiz ediliyor...")
        progress_bar.progress(50)
    
    # YENİ MANTIK: Geçerli ve kullanıcı hatası versiyonları ayır
    valid_versions = []  # Mantıklı progression
    user_error_versions = []  # Kullanıcı hataları (atlanacak ama etkisiz)
    
    for i, (current_version, current_date) in enumerate(sorted_versions):
        if i == 0:
            # İlk versiyon her zaman geçerli
            valid_versions.append((current_version, current_date))
        else:
            # Son geçerli versiyonla karşılaştır
            last_valid_version = valid_versions[-1][0]
            
            if is_version_higher(current_version, last_valid_version):
                # Versiyon numarası büyükse geçerli
                valid_versions.append((current_version, current_date))
            else:
                # Versiyon numarası küçük/eşitse kullanıcı hatası
                user_error_versions.append((current_version, current_date))
    
    results['valid_versions'] = valid_versions
    results['user_error_versions'] = user_error_versions
    
    if show_progress:
        status_text.text("📊 Versiyon aralıkları belirleniyor...")
        progress_bar.progress(70)
    
    # YENİ MANTIK: Sadece geçerli versiyonlar için aralık belirleme
    version_ranges = []
    
    for i in range(len(valid_versions)):
        current_version, current_date = valid_versions[i]
        
        if i == len(valid_versions) - 1:
            # Son geçerli versiyon - veri sonuna kadar
            end_date = df['date'].max().date()
        else:
            # Sonraki geçerli versiyonun tarihine kadar
            next_version, next_date = valid_versions[i + 1]
            end_date = next_date
        
        version_ranges.append({
            'version': current_version,
            'start_date': current_date,
            'end_date': end_date
        })
    
    results['version_ranges'] = version_ranges
    
    if show_progress:
        status_text.text("🔄 Akıllı versiyon doldurma başlıyor...")
        progress_bar.progress(90)
    
    # YENİ MANTIK: Akıllı versiyon doldurma
    def fill_version_smart(row):
        """Sadece boş versiyonları doldur, kullanıcı hatalarına dokunma"""
        
        # Eğer versiyon dolu ise (kullanıcı hatası dahil), dokunma
        if not (pd.isna(row['app_version']) or row['app_version'] == '' or row['app_version'] == 'nan'):
            return row['app_version']
        
        # Boş versiyon - hangi aralığa düşüyor?
        row_date = row['date']
        
        # row_date'i date formatına çevir
        if isinstance(row_date, pd.Timestamp):
            row_date = row_date.date()
        elif isinstance(row_date, str):
            try:
                row_date = pd.to_datetime(row_date).date()
            except:
                row_date = datetime.now().date()
        
        # Geçerli versiyon aralıklarında ara
        for version_info in version_ranges:
            version_name = version_info['version']
            start_date = version_info['start_date']
            end_date = version_info['end_date']
            
            # Tarih tiplerini kontrol et
            if isinstance(start_date, str):
                try:
                    start_date = pd.to_datetime(start_date).date()
                except:
                    continue
            
            if isinstance(end_date, str):
                try:
                    end_date = pd.to_datetime(end_date).date()
                except:
                    continue
            
            # Bu tarih aralığında mı?
            if start_date <= row_date < end_date:
                return version_name
        
        # Hiçbir aralığa uymuyorsa en yakın geçerli versiyonu ver
        if version_ranges:
            # En yakın versiyonu bul
            closest_version = version_ranges[0]['version']  # Fallback
            min_distance = float('inf')
            
            for version_info in version_ranges:
                version_name = version_info['version']
                start_date = version_info['start_date']
                
                if isinstance(start_date, str):
                    try:
                        start_date = pd.to_datetime(start_date).date()
                    except:
                        continue
                
                distance = abs((row_date - start_date).days)
                if distance < min_distance:
                    min_distance = distance
                    closest_version = version_name
            
            return closest_version
        else:
            return 'Unknown'
    
    # Versiyonları doldur
    if show_progress:
        st.info("🔄 Akıllı versiyon doldurma uygulanıyor...")
    
    try:
        df['app_version'] = df.apply(fill_version_smart, axis=1)
    except Exception as e:
        if show_progress:
            st.error(f"❌ Versiyon doldurma hatası: {e}")
        return df, {"error": f"Versiyon doldurma hatası: {e}"}
    
    # Final sonuçları hesapla
    final_missing_count = (df['app_version'].isna()) | (df['app_version'] == '') | (df['app_version'] == 'nan')
    results['final_missing_count'] = final_missing_count.sum()
    results['updated_count'] = results['missing_versions_count'] - results['final_missing_count']
    
    if show_progress:
        progress_bar.progress(100)
        st.success(f"✅ İşlem tamamlandı! {results['updated_count']} versiyon güncellendi.")
        st.info(f"📊 Kalan boş versiyon: {results['final_missing_count']}")
    
    return df, results

def process_data(df, selected_columns):
    """
    DataFrame'i işle ve istenen sütunları seç
    """
    try:
        # Gerekli sütunların varlığını kontrol et
        missing_columns = [col for col in selected_columns if col not in df.columns]
        if missing_columns:
            st.error(f"❌ Eksik sütunlar: {missing_columns}")
            return None
        
        # Sadece istenen sütunları seç
        specific_df = df[selected_columns].copy()
        
        # Eğer date sütunu varsa formatla
        if 'date' in specific_df.columns:
            specific_df['date'] = specific_df['date'].apply(format_date)
        
        return specific_df
        
    except Exception as e:
        st.error(f"❌ Veri işleme hatası: {e}")
        return None

def create_txt_content(df):
    """
    DataFrame'den TXT içeriği oluştur
    """
    txt_content = ""
    for _, row in df.iterrows():
        txt_content += f"Yorum: {row.get('translated_text', row.get('content', 'N/A'))}\n"
        txt_content += f"Puan: {row.get('rating', 'N/A')}\n"
        txt_content += f"Versiyon: {row.get('app_version', 'N/A')}\n"
        txt_content += f"Yararlı: {row.get('helpful_count', 'N/A')}\n"
        txt_content += f"Tarih: {row.get('date', 'N/A')}\n"
        txt_content += "---\n"
    return txt_content

def process_and_save_data(df):
    """Ana koordinasyon uygulaması için versiyon düzeltme + sütun seçimi - İYİLEŞTİRİLMİŞ"""
    if df is None or df.empty:
        return df
    
    try:
        # 1. Önce versiyon düzeltme (sadece gerekli sütunlar varsa)
        df_fixed = df.copy()
        
        if 'app_version' in df.columns and 'date' in df.columns:
            try:
                df_fixed, results = process_version_fixing(df, show_progress=False)
                
                if 'error' in results:
                    try:
                        import streamlit as st
                        st.warning(f"⚠️ Versiyon düzeltme atlandı: {results['error']}")
                    except:
                        pass
                    df_fixed = df.copy()
            except Exception as e:
                try:
                    import streamlit as st
                    st.warning(f"⚠️ Versiyon düzeltme hatası: {e}")
                except:
                    pass
                df_fixed = df.copy()
        
        # 2. Sütun standardizasyonu - daha esnek
        # Temel sütunları garanti et
        if 'rating' not in df_fixed.columns:
            df_fixed['rating'] = 0
        
        if 'app_version' not in df_fixed.columns and 'version' in df_fixed.columns:
            df_fixed['app_version'] = df_fixed['version']
        elif 'app_version' not in df_fixed.columns:
            df_fixed['app_version'] = 'Unknown'
        
        if 'date' not in df_fixed.columns:
            df_fixed['date'] = ''
        
        # Content sütununu garanti et
        if 'content' not in df_fixed.columns:
            if 'translated_text' in df_fixed.columns:
                df_fixed['content'] = df_fixed['translated_text']
            else:
                df_fixed['content'] = ''
        
        # Gerekli sütunları seç
        essential_columns = []
        possible_columns = ['content', 'translated_text', 'rating', 'app_version', 'helpful_count', 'date', 'author_name', 'version', 'platform']
        
        for col in possible_columns:
            if col in df_fixed.columns:
                essential_columns.append(col)
        
        if essential_columns:
            df_result = df_fixed[essential_columns].copy()
        else:
            df_result = df_fixed.copy()
        
        # Tarih formatlaması
        if 'date' in df_result.columns:
            df_result['date'] = df_result['date'].apply(format_date)
        
        return df_result
        
    except Exception as e:
        try:
            import streamlit as st
            st.error(f"❌ İşlem hatası: {e}")
        except:
            pass
        return df

if __name__ == "__main__":
    # Sayfa konfigürasyonu
    st.set_page_config(
        page_title="Play Store Versiyon & Sütun İşleyici",
        page_icon="🔧",
        layout="wide"
    )

    # Ana başlık
    st.title("🔧 Play Store Versiyon & Sütun İşleyici")
    st.markdown("---")

    # Tab sistemi
    tab1, tab2 = st.tabs(["🔧 Versiyon Düzenleyici", "🎯 Sütun Seçici"])

    # Sidebar - Dosya seçimi
    with st.sidebar:
        st.header("📁 Dosya Seçimi")
        
        # Dosya seçim yöntemi
        file_source = st.radio(
            "Dosya kaynağını seçin:",
            ["📂 Mevcut CSV dosyalarından seç", "📤 Dosya yükle"],
            help="Mevcut dosyalardan seçin veya yeni dosya yükleyin"
        )
        
        uploaded_file = None
        selected_file_path = None
        
        if file_source == "📂 Mevcut CSV dosyalarından seç":
            csv_files = scan_csv_files()
            
            if csv_files:
                # Play Store dosyalarını filtrele
                play_files = [f for f in csv_files if 'play' in f.lower() or 'edited' in f.lower() or 'version' in f.lower()]
                
                if play_files:
                    selected_file = st.selectbox(
                        "Play Store CSV dosyasını seçin:",
                        play_files,
                        help="app_version sütunu içeren Play Store verisi"
                    )
                    selected_file_path = selected_file
                    
                    # Dosya bilgileri
                    if selected_file:
                        try:
                            file_size = os.path.getsize(selected_file) / 1024  # KB
                            file_modified = datetime.fromtimestamp(os.path.getmtime(selected_file))
                            
                            st.info(f"""
                            **📊 Dosya Bilgileri:**
                            - Dosya: {selected_file}
                            - Boyut: {file_size:.1f} KB
                            - Değiştirme: {file_modified.strftime('%Y-%m-%d %H:%M')}
                            """)
                        except Exception as e:
                            st.warning(f"Dosya bilgisi alınamadı: {e}")
                else:
                    st.warning("❌ Play Store CSV dosyası bulunamadı!")
                    st.info("Dosya adında 'play', 'edited' veya 'version' kelimesi bulunmalı.")
            else:
                st.warning("❌ CSV dosyası bulunamadı!")
        
        else:
            uploaded_file = st.file_uploader(
                "CSV dosyasını yükleyin:",
                type=['csv'],
                help="Play Store verisi içeren CSV dosyası"
            )
        
        st.markdown("---")
        
        # İşlem ayarları
        st.header("⚙️ İşlem Ayarları")
        
        show_details = st.checkbox("🔍 Detaylı analiz göster", value=True)
        show_charts = st.checkbox("📈 Grafikleri göster", value=True)
        auto_download = st.checkbox("📥 Otomatik dosya indirme", value=False)

    # Dosya yükleme/seçme işlemi
    df = None

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.success(f"✅ Dosya yüklendi: {len(df)} satır, {len(df.columns)} sütun")
        except Exception as e:
            st.error(f"❌ Dosya yükleme hatası: {e}")
    elif selected_file_path:
        try:
            df = pd.read_csv(selected_file_path)
            st.success(f"✅ Dosya seçildi: {selected_file_path} - {len(df)} satır, {len(df.columns)} sütun")
        except Exception as e:
            st.error(f"❌ Dosya okuma hatası: {e}")

    # TAB 1: VERSİYON DÜZENLEYİCİ
    with tab1:
        if df is not None:
            # Gerekli sütunların varlığını kontrol et
            required_columns = ['app_version', 'date']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                st.error(f"❌ Versiyon düzenleme için eksik sütunlar: {missing_columns}")
                st.info("Versiyon düzenleme için 'app_version' ve 'date' sütunları gereklidir.")
                
                # Mevcut sütunları göster
                st.write("**📋 Mevcut sütunlar:**")
                cols = st.columns(3)
                for i, col in enumerate(df.columns):
                    with cols[i % 3]:
                        st.write(f"• {col}")
            else:
                # Başlangıç durumu
                st.subheader("📊 Başlangıç Durumu Analizi")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Toplam Kayıt", len(df))
                
                with col2:
                    missing_count = (df['app_version'].isna() | (df['app_version'] == '') | (df['app_version'] == 'nan')).sum()
                    st.metric("Boş Versiyon", missing_count)
                
                with col3:
                    valid_count = len(df) - missing_count
                    st.metric("Geçerli Versiyon", valid_count)
                
                with col4:
                    missing_percentage = (missing_count / len(df)) * 100 if len(df) > 0 else 0
                    st.metric("Boş Versiyon %", f"{missing_percentage:.1f}%")
                
                # Mevcut versiyon dağılımı
                if show_details:
                    st.subheader("📋 Mevcut Versiyon Dağılımı")
                    
                    version_counts = df['app_version'].value_counts().head(10)
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        if show_charts and len(version_counts) > 0:
                            try:
                                fig_pie = px.pie(
                                    values=version_counts.values,
                                    names=version_counts.index,
                                    title='En Çok Kullanılan Versiyonlar (Top 10)'
                                )
                                st.plotly_chart(fig_pie, use_container_width=True)
                            except Exception as e:
                                st.warning(f"Grafik çizilemedi: {e}")
                    
                    with col2:
                        st.write("**🔢 Versiyon Sayıları:**")
                        for ver, count in version_counts.items():
                            percentage = (count / len(df)) * 100
                            st.write(f"• {ver}: {count} ({percentage:.1f}%)")
                
                # İşleme butonu
                st.markdown("---")
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    process_button = st.button(
                        "🚀 Versiyon Düzenlemeyi Başlat", 
                        type="primary",
                        use_container_width=True
                    )
                
                if process_button:
                    st.subheader("🔧 Versiyon Düzenleme İşlemi")
                    
                    # İşlemi yap
                    try:
                        df_fixed, results = process_version_fixing(df, show_progress=True)
                        
                        # Hata kontrolü
                        if 'error' in results:
                            st.error(f"❌ İşlem hatası: {results['error']}")
                        else:
                            # Sonuçları göster
                            st.success("✅ Versiyon düzenleme tamamlandı!")
                            
                            # Session state'e kaydet
                            st.session_state.version_fixed_df = df_fixed
                            
                            # Sonuç metrikleri
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.metric(
                                    "Güncellenen Kayıt", 
                                    results['updated_count'],
                                    delta=f"-{results['updated_count']}"
                                )
                            
                            with col2:
                                st.metric(
                                    "Kalan Boş Versiyon", 
                                    results['final_missing_count']
                                )
                            
                            with col3:
                                st.metric(
                                    "Geçerli Versiyon", 
                                    len(results['valid_versions'])
                                )
                            
                            with col4:
                                st.metric(
                                    "Kullanıcı Hatası", 
                                    len(results['user_error_versions'])
                                )
                            
                            # Detaylı analiz (kısaltılmış)
                            if show_details:
                                with st.expander("📈 Detaylı Versiyon Analizi"):
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        st.write("**✅ Geçerli Versiyon Progression:**")
                                        for i, (ver, date) in enumerate(results['valid_versions'][:5]):  # İlk 5'i göster
                                            arrow = "→" if i < len(results['valid_versions']) - 1 else "🏁"
                                            st.write(f"{arrow} **{ver}** ({date})")
                                        
                                        if len(results['valid_versions']) > 5:
                                            st.write(f"... ve {len(results['valid_versions'])-5} versiyon daha")
                                    
                                    with col2:
                                        if results['user_error_versions']:
                                            st.write("**⚠️ Kullanıcı Hataları:**")
                                            for ver, date in results['user_error_versions'][:3]:  # İlk 3'ü göster
                                                st.write(f"🔒 **{ver}** ({date})")
                                            
                                            if len(results['user_error_versions']) > 3:
                                                st.write(f"... ve {len(results['user_error_versions'])-3} hata daha")
                                        else:
                                            st.success("🎉 Hiç kullanıcı hatası yok!")
                            
                            # Hızlı indirme
                            st.markdown("---")
                            col1, col2, col3 = st.columns(3)
                            
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            
                            with col1:
                                csv_buffer = io.StringIO()
                                df_fixed.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                                csv_data = csv_buffer.getvalue()
                                
                                st.download_button(
                                    label="📄 Düzeltilmiş CSV İndir",
                                    data=csv_data.encode('utf-8-sig'),
                                    file_name=f"version_fixed_{timestamp}.csv",
                                    mime="text/csv",
                                    use_container_width=True
                                )
                            
                            with col2:
                                st.info("✅ Versiyon düzeltme tamamlandı!\n👉 Sütun seçimi için 2. tab'a geçin")
                            
                            with col3:
                                if st.button("➡️ Sütun Seçimine Geç", use_container_width=True):
                                    st.session_state.active_tab = 1  # 2. tab'ı aktif yap
                                    st.rerun()
                    
                    except Exception as e:
                        st.error(f"❌ Versiyon düzenleme işlemi başarısız: {e}")
                        st.write("**🔍 Hata Detayları:**")
                        st.code(str(e))
        
        else:
            # Versiyon düzenleyici talimatları
            st.info("""
            ### 🔧 Akıllı Play Store Versiyon Düzenleyici
            
            #### 🧠 Akıllı Mantık:
            
            **🎯 Geçerli Versiyon Progression:**
            - Versiyonları tarih sırasına göre inceler
            - Sayıca büyüyen versiyonları "geçerli" olarak işaretler
            - Sadece geçerli versiyonlar boş tarihleri doldurmak için kullanılır
            
            **🔒 Kullanıcı Hatası Koruması:**
            - Geriye giden versiyonları tespit eder
            - Orijinal halinde korur ama boş tarihleri etkilemez
            
            **📅 Akıllı Tarih Doldurma:**
            - Boş tarihler sadece geçerli versiyon aralıklarına göre doldurulur
            
            #### 📋 Gerekli Sütunlar:
            - `app_version` - Uygulama versiyon numarası
            - `date` - Yorum tarihi
            """)

    # TAB 2: SÜTUN SEÇİCİ
    with tab2:
        # Versiyon düzeltilmiş veri var mı kontrol et
        current_df = None
        
        if 'version_fixed_df' in st.session_state:
            current_df = st.session_state.version_fixed_df
            st.info("✅ Versiyon düzeltilmiş veri kullanılıyor")
        elif df is not None:
            current_df = df
            st.warning("⚠️ Orijinal veri kullanılıyor (versiyon düzeltilmemiş)")
        
        if current_df is not None:
            # Veri önizlemesi
            st.subheader("👀 Veri Önizlemesi")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Toplam Satır", len(current_df))
            with col2:
                st.metric("Toplam Sütun", len(current_df.columns))
            with col3:
                if 'rating' in current_df.columns:
                    avg_rating = current_df['rating'].mean()
                    st.metric("Ort. Rating", f"{avg_rating:.1f}")
                else:
                    st.metric("Ort. Rating", "N/A")
            with col4:
                if 'app_version' in current_df.columns:
                    unique_versions = current_df['app_version'].nunique()
                    st.metric("Farklı Versiyon", unique_versions)
                else:
                    st.metric("Farklı Versiyon", "N/A")
            
            # Mevcut sütunları göster
            st.subheader("📑 Mevcut Sütunlar")
            st.write("Dosyanızdaki sütunlar:")
            
            # Sütunları 3'lü gruplarda göster
            columns = current_df.columns.tolist()
            cols = st.columns(3)
            for i, col in enumerate(columns):
                with cols[i % 3]:
                    st.write(f"• {col}")
            
            # Sütun seçimi
            st.subheader("🎯 İşlenecek Sütunları Seçin")
            
            # Varsayılan sütunlar - GÜNCELLENMIŞ
            default_columns = ['translated_text', 'content', 'rating', 'app_version', 'helpful_count', 'date', 'author_name']
            available_defaults = [col for col in default_columns if col in current_df.columns]
            
            # Eğer translated_text yoksa content'i varsayılan yap
            if 'translated_text' not in available_defaults and 'content' in current_df.columns:
                if 'content' not in available_defaults:
                    available_defaults = ['content'] + available_defaults
            
            # Sütun seçimi widget'ı
            selected_columns = st.multiselect(
                "Seçilecek sütunlar:",
                options=current_df.columns.tolist(),
                default=available_defaults,
                help="İşlemek istediğiniz sütunları seçin"
            )
            
            if selected_columns:
                # Seçilen sütunların önizlemesi
                st.write(f"**Seçilen {len(selected_columns)} sütun:**")
                preview_df = current_df[selected_columns].head(5)
                st.dataframe(preview_df, use_container_width=True)
                
                # İşleme butonu
                st.markdown("---")
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    process_column_button = st.button(
                        "🚀 Sütun Seçimi Uygula ve İndir", 
                        type="primary",
                        use_container_width=True,
                        key="column_process"
                    )
                
                if process_column_button:
                    # Sütun seçimi işlemi
                    processed_df = process_data(current_df, selected_columns)
                    
                    if processed_df is not None:
                        st.success(f"✅ Sütun seçimi başarıyla uygulandı: {len(processed_df)} satır")
                        
                        # İşlenmiş veri önizlemesi
                        st.subheader("📊 İşlenmiş Veri")
                        st.dataframe(processed_df.head(10), use_container_width=True)
                        
                        # İstatistikler
                        st.subheader("📈 İstatistikler")
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if 'rating' in processed_df.columns:
                                rating_dist = processed_df['rating'].value_counts().sort_index()
                                st.write("**Rating Dağılımı:**")
                                for rating, count in rating_dist.items():
                                    st.write(f"{rating}⭐: {count}")
                        
                        with col2:
                            if 'app_version' in processed_df.columns:
                                version_count = processed_df['app_version'].nunique()
                                st.metric("Farklı Versiyon", version_count)
                                
                                top_versions = processed_df['app_version'].value_counts().head(3)
                                st.write("**En Çok Yorum Alan Versiyonlar:**")
                                for version, count in top_versions.items():
                                    st.write(f"{version}: {count}")
                        
                        with col3:
                            if 'helpful_count' in processed_df.columns:
                                avg_helpful = processed_df['helpful_count'].mean()
                                st.metric("Ort. Yararlı", f"{avg_helpful:.1f}")
                                
                                total_helpful = processed_df['helpful_count'].sum()
                                st.metric("Toplam Yararlı", total_helpful)
                        
                        # İndirme butonları
                        st.markdown("---")
                        st.subheader("📥 Dosya İndir")
                        
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        # CSV İndir
                        with col1:
                            csv_buffer = io.StringIO()
                            processed_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                            csv_data = csv_buffer.getvalue()
                            
                            st.download_button(
                                label="📄 CSV İndir",
                                data=csv_data.encode('utf-8-sig'),
                                file_name=f"play_edited_{timestamp}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        
                        # JSON İndir
                        with col2:
                            json_data = processed_df.to_json(orient='records', force_ascii=False, indent=2)
                            
                            st.download_button(
                                label="📋 JSON İndir",
                                data=json_data,
                                file_name=f"play_edited_{timestamp}.json",
                                mime="application/json",
                                use_container_width=True
                            )
                        
                        # TXT İndir
                        with col3:
                            txt_content = create_txt_content(processed_df)
                            
                            st.download_button(
                                label="📝 TXT İndir",
                                data=txt_content,
                                file_name=f"play_edited_{timestamp}.txt",
                                mime="text/plain",
                                use_container_width=True
                            )
                        
                        # Özet bilgiler
                        st.markdown("---")
                        st.subheader("📋 İşlem Özeti")
                        
                        summary_col1, summary_col2 = st.columns(2)
                        
                        with summary_col1:
                            st.info(f"""
                            **📊 Veri Özeti:**
                            - Toplam satır: {len(processed_df):,}
                            - Seçilen sütun: {len(selected_columns)}
                            - İşlem tarihi: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                            """)
                        
                        with summary_col2:
                            st.success(f"""
                            **✅ Oluşturulan Dosyalar:**
                            - 📄 play_edited_{timestamp}.csv
                            - 📋 play_edited_{timestamp}.json  
                            - 📝 play_edited_{timestamp}.txt
                            """)
            else:
                st.warning("⚠️ Lütfen en az bir sütun seçin!")
        
        else:
            # Sütun seçici talimatları
            st.info("""
            ### 🎯 Play Store Sütun Seçici
            
            #### 🔄 İşlem Sırası:
            1. **🔧 1. Tab:** Versiyon düzenleme (isteğe bağlı)
            2. **🎯 2. Tab:** Sütun seçimi ve indirme
            
            #### 📋 Varsayılan Sütunlar:
            - `translated_text` veya `content` - Yorum metni
            - `rating` - Yıldız puanı
            - `app_version` - Uygulama versiyonu
            - `helpful_count` - Yararlı bulma sayısı
            - `date` - Tarih (otomatik formatlanır)
            - `author_name` - Yorum yazarı
            
            #### 🔧 Özellikler:
            - ✅ **Otomatik tarih formatlaması**
            - 📊 **Gerçek zamanlı istatistikler**
            - 📥 **3 format desteği** (CSV, JSON, TXT)
            - 🎯 **Esnek sütun seçimi**
            """)

    # Footer
    st.markdown("---")
    st.markdown("*🔧 Play Store Versiyon & Sütun İşleyici - Entegre Çözüm*")