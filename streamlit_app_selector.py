import streamlit as st
import pandas as pd
from datetime import datetime
import logging
import json
import re
import os
import io

# Logging ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def format_date(date_str):
    """
    Tarihi 2025-07-26T02:50:16-07:00 formatından 2025-07-26 formatına çevirir
    """
    if not date_str or pd.isna(date_str):
        return ""
    
    # Sadece tarih kısmını al (T'den öncesi)
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', str(date_str))
    return date_match.group(1) if date_match else str(date_str)

def process_app_store_data(df, selected_columns):
    """
    App Store DataFrame'ini işle ve istenen sütunları seç - İYİLEŞTİRİLMİŞ
    """
    try:
        if df is None or df.empty:
            return df
        
        # Mevcut sütunları kontrol et
        available_columns = [col for col in selected_columns if col in df.columns]
        
        if not available_columns:
            # Hiç sütun bulunamadıysa tüm dataframe'i döndür
            try:
                import streamlit as st
                st.warning(f"⚠️ İstenen sütunlar bulunamadı, tüm sütunlar korunuyor")
            except:
                pass
            specific_df = df.copy()
        else:
            # Sadece mevcut sütunları seç
            specific_df = df[available_columns].copy()
        
        # Tarihleri formatla (sadece tarih kısmı)
        if 'date' in specific_df.columns:
            specific_df['date'] = specific_df['date'].apply(format_date)
        
        # Gerekli sütunları garanti et
        if 'rating' not in specific_df.columns:
            specific_df['rating'] = 0
        
        if 'version' not in specific_df.columns:
            specific_df['version'] = 'Unknown'
        
        return specific_df
        
    except Exception as e:
        try:
            import streamlit as st
            st.error(f"❌ Veri işleme hatası: {e}")
        except:
            pass
        return df

def create_txt_content(df):
    """
    DataFrame'den TXT içeriği oluştur
    """
    txt_content = ""
    for _, row in df.iterrows():
        txt_content += f"Başlık: {row.get('title', 'N/A')}\n"
        txt_content += f"İçerik: {row.get('content', 'N/A')}\n"
        txt_content += f"Puan: {row.get('rating', 'N/A')}\n"
        txt_content += f"Versiyon: {row.get('version', 'N/A')}\n"
        txt_content += f"Tarih: {row.get('date', 'N/A')}\n"
        txt_content += "---\n"
    return txt_content

def scan_app_reviews_folder():
    """
    app_reviews klasöründeki CSV dosyalarını tara
    """
    app_reviews_dir = "app_reviews"
    csv_files = []
    
    if os.path.exists(app_reviews_dir):
        for file in os.listdir(app_reviews_dir):
            if file.endswith('.csv'):
                csv_files.append(os.path.join(app_reviews_dir, file))
    
    return csv_files

def main():
    """Ana uygulama fonksiyonu"""
    # Sayfa konfigürasyonu
    st.set_page_config(
        page_title="App Store Veri Seçici",
        page_icon="📱",
        layout="wide"
    )

    # Ana başlık
    st.title("📱 App Store Veri Seçici ve Dönüştürücü")
    st.markdown("---")

    # Sidebar - Dosya seçimi ve ayarlar
    with st.sidebar:
        st.header("📁 Dosya Seçimi")
        
        # Dosya seçim yöntemi
        file_source = st.radio(
            "Dosya kaynağını seçin:",
            ["📂 app_reviews klasöründen seç", "📤 Dosya yükle"],
            help="Mevcut dosyalardan seçin veya yeni dosya yükleyin"
        )
        
        uploaded_file = None
        selected_file_path = None
        
        if file_source == "📂 app_reviews klasöründen seç":
            # app_reviews klasöründeki dosyaları listele
            csv_files = scan_app_reviews_folder()
            
            if csv_files:
                # Dosya seçimi
                selected_file = st.selectbox(
                    "CSV dosyasını seçin:",
                    csv_files,
                    format_func=lambda x: os.path.basename(x)
                )
                selected_file_path = selected_file
                
                # Dosya bilgileri
                if selected_file:
                    try:
                        file_size = os.path.getsize(selected_file) / 1024  # KB
                        file_modified = datetime.fromtimestamp(os.path.getmtime(selected_file))
                        
                        st.info(f"""
                        **📊 Dosya Bilgileri:**
                        - Dosya: {os.path.basename(selected_file)}
                        - Boyut: {file_size:.1f} KB
                        - Değiştirme: {file_modified.strftime('%Y-%m-%d %H:%M')}
                        """)
                    except Exception as e:
                        st.warning(f"Dosya bilgisi alınamadı: {e}")
            else:
                st.warning("❌ app_reviews klasöründe CSV dosyası bulunamadı!")
                st.info("RSS scraper ile önce veri çekin veya dosya yükleme seçeneğini kullanın.")
        
        else:
            # Dosya yükleme
            uploaded_file = st.file_uploader(
                "CSV dosyasını yükleyin:",
                type=['csv'],
                help="App Store RSS verisi içeren CSV dosyasını seçin"
            )
        
        st.markdown("---")
        
        # Varsayılan sütunlar
        st.header("📋 Sütun Seçimi")
        st.markdown("**App Store varsayılan sütunları:**")
        st.info("""
        - title (başlık)
        - content (içerik)
        - rating (puan)
        - version (versiyon)
        - date (tarih)
        """)

    # Ana içerik alanı
    df = None

    # Dosya yükleme veya seçme işlemi
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.success(f"✅ Dosya yüklendi: {len(df)} satır")
        except Exception as e:
            st.error(f"❌ Dosya yükleme hatası: {e}")
    elif selected_file_path:
        try:
            df = pd.read_csv(selected_file_path)
            st.success(f"✅ Dosya seçildi: {os.path.basename(selected_file_path)} - {len(df)} satır")
        except Exception as e:
            st.error(f"❌ Dosya okuma hatası: {e}")

    if df is not None:
        try:
            # Progress bar
            progress_bar = st.progress(0)
            progress_bar.progress(25)
            
            # Veri önizlemesi
            st.subheader("👀 Veri Önizlemesi")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Toplam Satır", len(df))
            with col2:
                st.metric("Toplam Sütun", len(df.columns))
            with col3:
                if 'rating' in df.columns:
                    avg_rating = df['rating'].mean()
                    st.metric("Ort. Rating", f"{avg_rating:.1f}⭐")
                else:
                    st.metric("Ort. Rating", "N/A")
            with col4:
                if 'date' in df.columns:
                    unique_dates = df['date'].nunique()
                    st.metric("Farklı Tarih", unique_dates)
                else:
                    st.metric("Farklı Tarih", "N/A")
            
            progress_bar.progress(50)
            
            # Mevcut sütunları göster
            st.subheader("📑 Mevcut Sütunlar")
            st.write("Dosyanızdaki sütunlar:")
            
            # Sütunları 4'lü gruplarda göster
            columns = df.columns.tolist()
            cols = st.columns(4)
            for i, col in enumerate(columns):
                with cols[i % 4]:
                    # Varsayılan sütunları vurgula
                    if col in ['title', 'content', 'rating', 'version', 'date']:
                        st.write(f"✅ **{col}**")
                    else:
                        st.write(f"• {col}")
            
            progress_bar.progress(75)
            
            # Sütun seçimi
            st.subheader("🎯 İşlenecek Sütunları Seçin")
            
            # App Store varsayılan sütunları
            default_columns = ['title', 'content', 'rating', 'version', 'date']
            available_defaults = [col for col in default_columns if col in df.columns]
            
            # Eksik varsayılan sütunları göster
            missing_defaults = [col for col in default_columns if col not in df.columns]
            if missing_defaults:
                st.warning(f"⚠️ Eksik varsayılan sütunlar: {missing_defaults}")
            
            # Sütun seçimi widget'ı
            selected_columns = st.multiselect(
                "Seçilecek sütunlar:",
                options=df.columns.tolist(),
                default=available_defaults,
                help="İşlemek istediğiniz sütunları seçin"
            )
            
            if selected_columns:
                # Seçilen sütunların önizlemesi
                st.write(f"**Seçilen {len(selected_columns)} sütun:**")
                preview_df = df[selected_columns].head(5)
                st.dataframe(preview_df, use_container_width=True)
                
                progress_bar.progress(100)
                
                # İşleme butonu
                st.markdown("---")
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    process_button = st.button(
                        "🚀 Veriyi İşle ve İndir", 
                        type="primary",
                        use_container_width=True
                    )
                
                if process_button:
                    # Veriyi işle
                    processed_df = process_app_store_data(df, selected_columns)
                    
                    if processed_df is not None:
                        st.success(f"✅ Veri başarıyla işlendi: {len(processed_df)} satır")
                        
                        # İşlenmiş veri önizlemesi
                        st.subheader("📊 İşlenmiş Veri")
                        st.dataframe(processed_df.head(10), use_container_width=True)
                        
                        # İstatistikler
                        st.subheader("📈 App Store İstatistikleri")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            if 'rating' in processed_df.columns:
                                rating_dist = processed_df['rating'].value_counts().sort_index()
                                st.write("**⭐ Rating Dağılımı:**")
                                for rating, count in rating_dist.items():
                                    percentage = (count / len(processed_df)) * 100
                                    st.write(f"{rating}⭐: {count} ({percentage:.1f}%)")
                        
                        with col2:
                            if 'version' in processed_df.columns:
                                version_count = processed_df['version'].nunique()
                                st.metric("🔢 Farklı Versiyon", version_count)
                                
                                top_versions = processed_df['version'].value_counts().head(3)
                                st.write("**📱 En Çok Yorum Alan:**")
                                for version, count in top_versions.items():
                                    st.write(f"{version}: {count}")
                        
                        with col3:
                            if 'content' in processed_df.columns:
                                # İçerik uzunluğu analizi
                                processed_df['content_length'] = processed_df['content'].str.len()
                                avg_length = processed_df['content_length'].mean()
                                st.metric("📝 Ort. İçerik Uzunluğu", f"{avg_length:.0f} kar.")
                                
                                max_length = processed_df['content_length'].max()
                                min_length = processed_df['content_length'].min()
                                st.write(f"**📏 Uzunluk Aralığı:**")
                                st.write(f"Min: {min_length} - Max: {max_length}")
                        
                        with col4:
                            if 'date' in processed_df.columns:
                                # Tarih analizi
                                processed_df['date_parsed'] = pd.to_datetime(processed_df['date'], errors='coerce')
                                date_range = processed_df['date_parsed'].max() - processed_df['date_parsed'].min()
                                
                                st.metric("📅 Tarih Aralığı", f"{date_range.days} gün")
                                
                                latest_date = processed_df['date_parsed'].max()
                                oldest_date = processed_df['date_parsed'].min()
                                
                                st.write(f"**📊 Tarih Bilgileri:**")
                                st.write(f"En eski: {oldest_date.strftime('%Y-%m-%d') if not pd.isna(oldest_date) else 'N/A'}")
                                st.write(f"En yeni: {latest_date.strftime('%Y-%m-%d') if not pd.isna(latest_date) else 'N/A'}")
                        
                        # Rating trend analizi (eğer tarih ve rating varsa)
                        if 'date' in processed_df.columns and 'rating' in processed_df.columns:
                            st.subheader("📈 Rating Trend Analizi")
                            
                            try:
                                # Günlük ortalama rating
                                processed_df['date_only'] = processed_df['date']
                                daily_ratings = processed_df.groupby('date_only')['rating'].agg(['mean', 'count']).reset_index()
                                daily_ratings = daily_ratings[daily_ratings['count'] >= 2]  # En az 2 yorum olan günler
                                
                                if len(daily_ratings) > 0:
                                    try:
                                        import plotly.express as px
                                        
                                        fig = px.line(
                                            daily_ratings, 
                                            x='date_only', 
                                            y='mean',
                                            title='Günlük Ortalama Rating Trendi',
                                            labels={'date_only': 'Tarih', 'mean': 'Ortalama Rating'}
                                        )
                                        
                                        # Y ekseni aralığını ayarla
                                        fig.update_layout(
                                            yaxis=dict(range=[1, 5]),
                                            height=400,
                                            showlegend=False
                                        )
                                        
                                        st.plotly_chart(fig, use_container_width=True)
                                        
                                    except ImportError:
                                        st.warning("📊 Grafik çizimi için plotly gerekli. Alternatif analiz:")
                                        
                                        # Alternatif: Basit istatistikler
                                        avg_by_period = daily_ratings.groupby(daily_ratings['date_only'].str[:7])['mean'].mean()
                                        st.write("**📊 Aylık Ortalama Rating:**")
                                        for period, avg_rating in avg_by_period.items():
                                            st.write(f"{period}: {avg_rating:.2f}⭐")
                                            
                                    except Exception as e:
                                        st.warning(f"📊 Grafik çizilemedi: {e}")
                                        
                                        # Fallback: Basit trend analizi
                                        if len(daily_ratings) >= 2:
                                            first_avg = daily_ratings['mean'].iloc[0]
                                            last_avg = daily_ratings['mean'].iloc[-1]
                                            trend = "📈 Artan" if last_avg > first_avg else "📉 Azalan" if last_avg < first_avg else "➡️ Sabit"
                                            
                                            st.info(f"""
                                            **📊 Basit Trend Analizi:**
                                            - İlk dönem ortalaması: {first_avg:.2f}⭐
                                            - Son dönem ortalaması: {last_avg:.2f}⭐
                                            - Trend: {trend}
                                            """)
                                else:
                                    st.info("📊 Trend analizi için yeterli veri yok (günde en az 2 yorum gerekli)")
                                    
                            except Exception as e:
                                st.warning(f"📊 Trend analizi hatası: {e}")
                        
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
                                file_name=f"edited_app_store_{timestamp}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        
                        # JSON İndir
                        with col2:
                            json_data = processed_df.to_json(orient='records', force_ascii=False, indent=2)
                            
                            st.download_button(
                                label="📋 JSON İndir",
                                data=json_data,
                                file_name=f"edited_app_store_{timestamp}.json",
                                mime="application/json",
                                use_container_width=True
                            )
                        
                        # TXT İndir
                        with col3:
                            txt_content = create_txt_content(processed_df)
                            
                            st.download_button(
                                label="📝 TXT İndir",
                                data=txt_content,
                                file_name=f"edited_app_store_{timestamp}.txt",
                                mime="text/plain",
                                use_container_width=True
                            )
                        
                        # Özet bilgiler
                        st.markdown("---")
                        st.subheader("📋 İşlem Özeti")
                        
                        summary_col1, summary_col2 = st.columns(2)
                        
                        with summary_col1:
                            st.info(f"""
                            **📊 App Store Veri Özeti:**
                            - Toplam yorum: {len(processed_df):,}
                            - Seçilen sütun: {len(selected_columns)}
                            - Ortalama rating: {processed_df['rating'].mean():.2f}⭐ (varsa)
                            - İşlem tarihi: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                            """)
                        
                        with summary_col2:
                            st.success(f"""
                            **✅ Oluşturulan Dosyalar:**
                            - 📄 edited_app_store_{timestamp}.csv
                            - 📋 edited_app_store_{timestamp}.json  
                            - 📝 edited_app_store_{timestamp}.txt
                            
                            **🎯 Formatlanmış Tarihler:** YYYY-MM-DD
                            """)
            else:
                st.warning("⚠️ Lütfen en az bir sütun seçin!")
                
        except Exception as e:
            st.error(f"❌ Dosya işleme hatası: {str(e)}")
            st.exception(e)

    else:
        # Kullanım talimatları
        st.info("""
        ### 📝 Nasıl Kullanılır?
        
        #### 1. 📁 Dosya Seçimi
        - **app_reviews klasöründen seç:** RSS scraper ile çekilen dosyalar
        - **Dosya yükle:** Kendi CSV dosyanızı yükleyin
        
        #### 2. 🎯 Sütun Seçimi  
        - **App Store varsayılan sütunları** otomatik seçilir:
          - `title` - Yorum başlığı
          - `content` - Yorum içeriği
          - `rating` - Yıldız puanı (1-5)
          - `version` - Uygulama versiyonu
          - `date` - Tarih (formatlanacak)
        - İstediğiniz **ek sütunları** da seçebilirsiniz
        
        #### 3. 🚀 İşleme ve İndirme
        - **"Veriyi İşle ve İndir"** butonuna tıklayın
        - **Tarih formatlaması:** `2025-07-26T02:50:16-07:00` → `2025-07-26`
        - **3 farklı formatta** dosya indirin:
          - 📄 **CSV** - Excel'de açılabilir
          - 📋 **JSON** - API entegrasyonu için
          - 📝 **TXT** - İnsan okunabilir format
        
        ### 🔧 App Store Özellikler
        - ✅ **ISO tarih formatlaması** (T ve timezone kaldırma)
        - 📊 **Rating dağılımı analizi**
        - 📱 **Versiyon analizi**
        - 📈 **Trend grafikleri**
        - 📝 **İçerik uzunluğu analizi**
        - 🎯 **Esnek sütun seçimi**
        
        ### 📂 Varsayılan Dosya Yolu
        Örnek: `app_reviews/rss_reviews_1360892562_20250815_141226_20241205_to_20250815.csv`
        """)
        
        # Örnek veri formatı
        st.subheader("📋 Beklenen App Store Veri Formatı")
        
        example_data = {
            'title': ['Harika uygulama', 'Çok yavaş', 'Beğendim'],
            'content': ['Bu uygulama gerçekten harika çalışıyor!', 'Çok yavaş açılıyor, düzeltilmeli', 'Genel olarak memnunum, tavsiye ederim'],
            'rating': [5, 2, 4],
            'version': ['2.1.0', '2.0.5', '2.1.0'],
            'date': ['2025-07-26T14:30:16-07:00', '2025-07-25T09:15:22-07:00', '2025-07-24T16:45:33-07:00']
        }
        
        example_df = pd.DataFrame(example_data)
        st.dataframe(example_df, use_container_width=True)
        
        st.write("**📅 Formatlanmış tarihler:**")
        formatted_example = example_df.copy()
        formatted_example['date'] = formatted_example['date'].apply(format_date)
        st.dataframe(formatted_example[['date']], use_container_width=True)

    # Footer
    st.markdown("---")
    st.markdown("*📱 App Store Veri Seçici - RSS CSV/JSON/TXT Dönüştürücü*")

if __name__ == "__main__":
    main()