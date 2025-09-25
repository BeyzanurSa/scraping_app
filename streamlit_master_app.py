import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import math
import io
import json
import time

# Page config - SADECE BURADA
st.set_page_config(
    page_title="🔥 Yorum Scraping Analiz Sistemi", 
    page_icon="🎯", 
    layout="wide"
)

# Modüller import - Hata yakalama ile
try:
    from play_scraper_streamlit import scrape_play_reviews
    from streamlit_version_fixer import process_and_save_data
    from translator_streamlit import translate_reviews
    from rss_scraper_streamlit import scrape_app_store_reviews
    from streamlit_app_selector import process_app_store_data
    from streamlit_z_analiz import (
        analyze_platform_data,
        create_platform_rating_pie_charts,
        create_version_rating_analysis,
        create_rating_trend_analysis,
        create_heatmap_analysis,
        create_platform_comparison_summary,
    )
    MODULES_LOADED = True
except ImportError as e:
    st.error(f"⚠ Modül import hatası: {e}")
    st.error("Lütfen tüm gerekli dosyaların aynı dizinde olduğundan emin olun.")
    MODULES_LOADED = False

if not MODULES_LOADED:
    st.stop()

# SESSION STATE INITIALIZATION - SADECE TEMEL VERİLER
if "analysis_data" not in st.session_state:
    st.session_state.analysis_data = None

if "scraped_data" not in st.session_state:
    st.session_state.scraped_data = None

if "scraping_metadata" not in st.session_state:
    st.session_state.scraping_metadata = None

if "show_analysis" not in st.session_state:
    st.session_state.show_analysis = False

# Ana başlık
st.title("🎯 Yorum Scraping & Analiz Sistemi")
st.markdown("**Otomatik:** çek → düzelt → çevir → işle → analiz")

# KULLANICI GİRİŞİ FORMU - BASİTLEŞTİRİLMİŞ
with st.form("main_form"):
    st.subheader("📱 Uygulama Bilgileri")
    
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        package_name = st.text_input(
            "📱 Play Store Paket Adı", 
            value="tr.gov.tcdd.tasimacilik", 
            help="Örnek: com.whatsapp, tr.gov.tcdd.tasimacilik"
        )
    
    with col2:
        appstore_app_id = st.number_input(
            "🍎 App Store App ID", 
            min_value=1, 
            value=1360892562, 
            step=1,
            help="App Store'dan alınan numerik ID"
        )
    
    # Tarih aralığı
    st.subheader("📅 Tarih Aralığı")
    
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "Başlangıç Tarihi",
            value=datetime(2025, 5, 1).date()
        )
    
    with col2:
        end_date = st.date_input(
            "Bitiş Tarihi",
            value=datetime.now().date()
        )
    
    # İşlem seçenekleri
    st.subheader("⚙️ İşlem Seçenekleri")
    
    col1, col2 = st.columns(2)
    
    with col1:
        selected_platforms = st.multiselect(
            "📊 Veri Kaynağını Seçin:",
            ["📱 Play Store", "🍎 App Store"],
            default=["📱 Play Store", "🍎 App Store"]
        )
    
    with col2:
        processing_options = st.multiselect(
            "🔧 İşleme Seçenekleri:",
            ["🔧 Versiyon düzeltme", "🌍 Çeviri işlemi", "📊 Analiz"],
            default=["🔧 Versiyon düzeltme", "🌍 Çeviri işlemi", "📊 Analiz"]
        )
    
    # Pipeline başlat butonu
    submitted = st.form_submit_button(
        "🚀 Scraping Başlat", 
        type="primary", 
        use_container_width=True
    )

# MEVCUT VERİ KONTROL PANEL - BASİT
if st.session_state.scraped_data is not None and not submitted:
    st.markdown("---")
    st.subheader("📊 Mevcut Scraping Verileri")
    
    metadata = st.session_state.scraping_metadata or {}
    scraped_df = st.session_state.scraped_data
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("⏱️ Son İşlem", metadata.get('timestamp', 'Bilinmiyor')[:10])
    
    with col2:
        play_count = metadata.get('play_count', 0)
        st.metric("📱 Play Store", f"{play_count:,}")
    
    with col3:
        app_count = metadata.get('app_count', 0)
        st.metric("🍎 App Store", f"{app_count:,}")
    
    with col4:
        total_count = play_count + app_count
        st.metric("🎯 Toplam", f"{total_count:,}")
    
    # Ana kontrol butonları
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Analiz Göster/Gizle", type="primary", use_container_width=True):
            st.session_state.show_analysis = not st.session_state.show_analysis
            st.rerun()
    
    with col2:
        if st.button("🔄 Yeni Scraping", type="secondary", use_container_width=True):
            # SADECE SCRAPING VERİLERİNİ TEMİZLE
            st.session_state.scraped_data = None
            st.session_state.scraping_metadata = None
            st.session_state.show_analysis = False
            st.rerun()
    
    with col3:
        if st.button("👁️ Veri Önizleme", type="secondary", use_container_width=True):
            # Önizleme toggle
            if 'show_preview' not in st.session_state:
                st.session_state.show_preview = True
            else:
                st.session_state.show_preview = not st.session_state.show_preview
            st.rerun()

# SCRAPING PIPELINE - FORM SUBMİT EDİLDİĞİNDE
if submitted:
    if start_date >= end_date:
        st.error("⚠ Başlangıç tarihi bitiş tarihinden önce olmalıdır!")
        st.stop()
    
    # Platform seçimlerini değişkenlere çevir
    enable_play_store = "📱 Play Store" in selected_platforms
    enable_app_store = "🍎 App Store" in selected_platforms
    enable_version_fix = "🔧 Versiyon düzeltme" in processing_options
    enable_translation = "🌍 Çeviri işlemi" in processing_options
    enable_analysis = "📊 Analiz" in processing_options
    
    st.markdown("---")
    st.subheader("🔄 Scraping İşlemi")
    
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_steps = sum([enable_play_store, enable_app_store, enable_version_fix, enable_translation])
    current_step = 0
    
    def update_progress(message, step_increment=1):
        global current_step
        current_step += step_increment
        progress = min(current_step / total_steps, 1.0) if total_steps > 0 else 1.0
        progress_bar.progress(progress)
        status_text.info(f"🔄 {message}")
    
    # Veri saklama
    combined_data = []
    metadata = {
        'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
        'date_range': f"{start_date} - {end_date}",
        'play_count': 0,
        'app_count': 0,
        'package_name': package_name,
        'app_id': appstore_app_id
    }
    
    # PLAY STORE SCRAPING
    if enable_play_store:
        update_progress("📱 Play Store yorumları çekiliyor...")
        
        try:
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            play_raw = scrape_play_reviews(
                package_name=package_name, 
                max_count=5000, 
                lang='tr',
                start_date=start_datetime,
                end_date=end_datetime
            )
            
            df_play = pd.DataFrame(play_raw) if play_raw else pd.DataFrame()
            
            if not df_play.empty:
                # Version fixing
                if enable_version_fix:
                    update_progress("🔧 Play Store versiyon düzeltiliyor...")
                    df_play = process_and_save_data(df_play)
                
                # Translation
                if enable_translation:
                    update_progress("🌍 Play Store yorumları çevriliyor...")
                    df_play = translate_reviews(df_play)
                
                # Platform bilgisi ekle
                df_play['platform'] = 'Play Store'
                df_play['source_package'] = package_name
                
                combined_data.append(df_play)
                metadata['play_count'] = len(df_play)
                
                st.success(f"✅ Play Store: {len(df_play)}  yorum işlendi")
            else:
                st.warning(f"⚠️ Play Store: {package_name} için belirtilen tarih aralığında yorum bulunamadı")
                
        except Exception as e:
            st.error(f"❌ Play Store hatası: {e}")
    
    # APP STORE SCRAPING
    if enable_app_store:
        update_progress("🍎 App Store yorumları çekiliyor...")
        
        try:
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            app_raw = scrape_app_store_reviews(
                app_id=str(appstore_app_id), 
                max_pages=10, 
                country='tr',
                start_date=start_datetime,
                end_date=end_datetime,
                max_reviews=5000
            )
            
            df_app = pd.DataFrame(app_raw) if app_raw else pd.DataFrame()
            
            if not df_app.empty:
                # App Store veri işleme
                needed_columns = ['title', 'content', 'rating', 'version', 'date']
                available_columns = [col for col in needed_columns if col in df_app.columns]
                
                if not available_columns:
                    available_columns = list(df_app.columns)
                
                df_app = process_app_store_data(df_app, available_columns)
                
                # Platform bilgisi ekle
                df_app['platform'] = 'App Store'
                df_app['source_app_id'] = str(appstore_app_id)
                
                combined_data.append(df_app)
                metadata['app_count'] = len(df_app)
                
                st.success(f"✅ App Store: {len(df_app)}  yorum işlendi")
            else:
                st.warning(f"⚠️ App Store: App ID {appstore_app_id} için belirtilen tarih aralığında yorum bulunamadı")
                
        except Exception as e:
            st.error(f"❌ App Store hatası: {e}")
    
    # VERİYİ BİRLEŞTİR VE KAYDET
    if combined_data:
        # VERİLERİ BİRLEŞTİRMEDEN ÖNCE STANDARDİZE ET
        standardized_data = []
        
        for df in combined_data:
            if not df.empty:
                # Gerekli sütunları kontrol et ve oluştur
                required_columns = ['content', 'rating', 'date', 'platform']
                
                # Eksik sütunları ekle
                for col in required_columns:
                    if col not in df.columns:
                        if col == 'content':
                            # title veya text sütunu varsa kullan
                            if 'title' in df.columns:
                                df['content'] = df['title'].fillna('').astype(str)
                            elif 'text' in df.columns:
                                df['content'] = df['text'].fillna('').astype(str)
                            else:
                                df['content'] = 'No content'
                        elif col == 'rating':
                            if 'score' in df.columns:
                                df['rating'] = df['score']
                            else:
                                df['rating'] = 0
                        elif col == 'date':
                            if 'updated' in df.columns:
                                df['date'] = df['updated']
                            elif 'at' in df.columns:
                                df['date'] = df['at']
                            else:
                                df['date'] = datetime.now()
                
                # Rating'i numeric yap
                if 'rating' in df.columns:
                    df['rating'] = pd.to_numeric(df['rating'], errors='coerce').fillna(0)
                
                # Version sütunu kontrolü
                if 'version' not in df.columns:
                    if 'app_version' in df.columns:
                        df['version'] = df['app_version'].astype(str)
                    elif 'appVersion' in df.columns:
                        df['version'] = df['appVersion'].astype(str)
                    else:
                        df['version'] = 'Unknown'
                
                # Author name kontrolü
                if 'author_name' not in df.columns:
                    if 'userName' in df.columns:
                        df['author_name'] = df['userName']
                    elif 'author' in df.columns:
                        df['author_name'] = df['author']
                    else:
                        df['author_name'] = 'Unknown'
                
                standardized_data.append(df)
        
        if standardized_data:
            scraped_df = pd.concat(standardized_data, ignore_index=True)
            
            # Tarihleri standart formata çevir
            if 'date' in scraped_df.columns:
                scraped_df['date'] = pd.to_datetime(scraped_df['date'], errors='coerce')
            
            metadata['total_count'] = len(scraped_df)
            
            # SESSION STATE'E KAYDET
            st.session_state.scraped_data = scraped_df
            st.session_state.scraping_metadata = metadata
            
            # Platform bazında sayıları güncelle
            if 'platform' in scraped_df.columns:
                platform_counts = scraped_df['platform'].value_counts()
                metadata['play_count'] = platform_counts.get('Play Store', 0)
                metadata['app_count'] = platform_counts.get('App Store', 0)
            
            # ANALİZ HAZIRLA - GELİŞTİRİLMİŞ
            if enable_analysis:
                update_progress("📊 Analiz hazırlanıyor...")
                try:
                    # Platform bazında veri ayır
                    df_play_ready = scraped_df[scraped_df['platform'] == 'Play Store'].copy() if 'platform' in scraped_df.columns else pd.DataFrame()
                    df_app_ready = scraped_df[scraped_df['platform'] == 'App Store'].copy() if 'platform' in scraped_df.columns else pd.DataFrame()
                    
                    # Her iki platformun da veri olup olmadığını kontrol et
                    play_has_data = not df_play_ready.empty and len(df_play_ready) > 0
                    app_has_data = not df_app_ready.empty and len(df_app_ready) > 0
                    
                    if play_has_data or app_has_data:
                        # Boş dataframe'ler için minimum sütun yapısı oluştur
                        required_cols = ['content', 'rating', 'date', 'version', 'platform']
                        
                        for df_name, df in [('Play Store', df_play_ready), ('App Store', df_app_ready)]:
                            if df.empty:
                                # Boş DataFrame oluştur ama doğru sütunlarla
                                empty_df = pd.DataFrame(columns=required_cols)
                                if df_name == 'Play Store':
                                    df_play_ready = empty_df
                                else:
                                    df_app_ready = empty_df
                    
                        # Analiz verisini hazırla
                        analysis_data = analyze_platform_data(df_play_ready, df_app_ready, max_versions=15)
                        
                        if analysis_data:
                            st.session_state.analysis_data = analysis_data
                            st.session_state.show_analysis = True
                            
                            # Analiz özeti göster
                            total_analyzed = len(df_play_ready) + len(df_app_ready)
                            st.success(f"✅ Analiz hazırlandı! ({total_analyzed:,} yorum analiz edildi)")
                        else:
                            st.warning("⚠ Analiz için uygun veri bulunamadı")
                    else:
                        st.warning("⚠ Analiz için hiç veri bulunamadı")
                        
                except Exception as e:
                    st.error(f"❌ Analiz hatası: {e}")
                    st.write("Debug: Scraped data columns:", scraped_df.columns.tolist() if not scraped_df.empty else "Empty DataFrame")
        
        progress_bar.progress(1.0)
        status_text.success("✅ Scraping tamamlandı!")
        
        # Platform bazında özet göster
        platform_summary = ""
        if 'platform' in scraped_df.columns:
            platform_counts = scraped_df['platform'].value_counts()
            for platform, count in platform_counts.items():
                platform_summary += f"{platform}: {count:,} yorum | "
        
        st.success(f"🎯 Toplam {metadata['total_count']:,} yorum başarıyla işlendi! ({platform_summary.rstrip(' | ')})")
        
        time.sleep(1)
        st.rerun()
    
    else:
        # Hiçbir platform seçilmemişse
        if not enable_play_store and not enable_app_store:
            st.error("❌ En az bir platform seçmelisiniz!")
        else:
            # Platformlar seçilmiş ama veri çekilememiş
            st.warning("⚠ Belirtilen tarih aralığında hiç yorum bulunamadı. Tarih aralığını genişletmeyi deneyin.")

# ANALİZ GÖRSELLEŞTİRMELERİ - KARLI DURUM
if st.session_state.show_analysis and st.session_state.analysis_data is not None:
    st.markdown("---")
    st.subheader("🎛️ Analiz Görselleştirmeleri")
    
    try:
        analysis_data = st.session_state.analysis_data
        
        # Görselleştirmeler - HERHANGİ BİR BUTON ETKİLEŞİMİNDE KAYBOLMAZ
        create_platform_rating_pie_charts(analysis_data)
        st.markdown("---")
        create_version_rating_analysis(analysis_data)
        st.markdown("---")
        create_rating_trend_analysis(analysis_data)
        st.markdown("---")
        create_heatmap_analysis(analysis_data)
        st.markdown("---")
        create_platform_comparison_summary(analysis_data)
        
    except Exception as e:
        st.error(f"❌ Analiz görselleştirme hatası: {e}")

# VERİ ÖNİZLEME - TOGGLE
if 'show_preview' in st.session_state and st.session_state.show_preview and st.session_state.scraped_data is not None:
    st.markdown("---")
    st.subheader("👁️ Veri Önizlemesi")
    
    scraped_df = st.session_state.scraped_data
    
    # Platform dağılımı
    if 'platform' in scraped_df.columns:
        platform_counts = scraped_df['platform'].value_counts()
        st.write("**Platform Dağılımı:**")
        for platform, count in platform_counts.items():
            st.write(f"• {platform}: {count:,}")
    
    # DataFrame önizleme
    st.dataframe(scraped_df.head(20), use_container_width=True)

# VERİ İNDİRME - SÜREKLI ERİŞİLEBİLİR
if st.session_state.scraped_data is not None:
    st.markdown("---")
    st.subheader("💾 Veri İndirme")
    
    scraped_df = st.session_state.scraped_data
    metadata = st.session_state.scraping_metadata or {}
    
    # Sütun seçimi
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Varsayılan sütunlar - DEĞİŞTİRİLDİ
        all_columns = scraped_df.columns.tolist()
        important_columns = ['content', 'rating', 'date', 'version', 'platform', 'author_name']
        
        default_columns = []
        for col in important_columns:
            if col in all_columns:
                default_columns.append(col)
        
        # Eksik sütunlar varsa tamamla
        if len(default_columns) < 5:
            remaining = [col for col in all_columns if col not in default_columns]
            default_columns.extend(remaining[:8-len(default_columns)])
        
        # Session state'de sütun seçimini sakla
        if 'download_columns' not in st.session_state:
            st.session_state.download_columns = default_columns[:6]
        
        selected_columns = st.multiselect(
            "📋 İndirme için sütunları seçin:",
            options=all_columns,
            default=st.session_state.download_columns,
            help="İndirmek istediğiniz sütunları seçin",
            key="column_multiselect"
        )
        
        # Seçimi session state'e kaydet
        st.session_state.download_columns = selected_columns

    with col2:
        # Hızlı seçim butonları - DEĞİŞTİRİLDİ
        st.write("**⚡ Hızlı Seçim:**")
        
        if st.button("📝 Temel", help="Temel sütunlar", key="basic_btn"):
            basic = ['content', 'rating', 'date', 'version', 'platform']
            st.session_state.download_columns = [col for col in basic if col in all_columns]
            st.rerun()
        
        if st.button("📊 Detaylı", help="Detaylı sütunlar", key="detailed_btn"):
            detailed = ['content', 'rating', 'author_name', 'date', 'version', 'platform']
            if 'translated_text' in all_columns:
                detailed.insert(0, 'translated_text')
            st.session_state.download_columns = [col for col in detailed if col in all_columns]
            st.rerun()
        
        if st.button("🎯 Tümü", help="Tüm sütunlar", key="all_btn"):
            st.session_state.download_columns = all_columns
            st.rerun()
    
    # Filtrelenmiş veri hazırla - TARIH FORMATLAMA EKLENDİ
    if selected_columns:
        filtered_df = scraped_df[selected_columns].copy()
        
        # Tarih formatını değiştir - Gün/Ay/Yıl
        if 'date' in filtered_df.columns:
            filtered_df['date'] = pd.to_datetime(filtered_df['date'], errors='coerce')
            filtered_df['date'] = filtered_df['date'].dt.strftime('%d/%m/%Y')
        
        # Dosya hazırlığı
        timestamp = metadata.get('timestamp', datetime.now().strftime('%Y%m%d_%H%M%S'))
        
        # CSV
        csv_data = filtered_df.to_csv(index=False, encoding='utf-8').encode('utf-8')
        
        # JSON - Tarih formatı için özel işlem
        json_ready_df = filtered_df.copy()
        json_data = json_ready_df.to_json(orient='records', force_ascii=False, indent=2).encode('utf-8')
        
        # TXT
        txt_content = f"Scraping Verileri - {timestamp}\n"
        txt_content += f"Tarih Aralığı: {metadata.get('date_range', 'Bilinmiyor')}\n"
        txt_content += f"Toplam Yorum: {len(filtered_df)}\n"
        txt_content += f"Seçilen Sütunlar: {', '.join(selected_columns)}\n"
        txt_content += "=" * 50 + "\n\n"
        
        for idx, row in filtered_df.head(5000).iterrows():
            txt_content += f"#{idx + 1}\n"
            for col in selected_columns:
                txt_content += f"{col}: {row.get(col, 'N/A')}\n"
            txt_content += "-" * 30 + "\n"
        
        txt_data = txt_content.encode('utf-8')
        
        # İndirme butonları
        st.success(f"✅ {len(selected_columns)} sütun, {len(filtered_df)} yorum hazır")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.download_button(
                "📥 CSV İndir",
                data=csv_data,
                file_name=f"scraping_{timestamp}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            st.download_button(
                "📥 JSON İndir",
                data=json_data,
                file_name=f"scraping_{timestamp}.json",
                mime="application/json",
                use_container_width=True
            )
        
        with col3:
            st.download_button(
                "📥 TXT İndir",
                data=txt_data,
                file_name=f"scraping_{timestamp}.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        # Özet bilgiler
        st.info(f"""
        **📊 İndirme Özeti:**
        - 📋 Seçilen sütun: {len(selected_columns)}
        - 📊 Toplam satır: {len(filtered_df):,}
        - 📱 Play Store: {metadata.get('play_count', 0):,}
        - 🍎 App Store: {metadata.get('app_count', 0):,}
        - 📅 Tarih: {metadata.get('date_range', 'Bilinmiyor')}
        """)
    
    else:
        st.warning("⚠ İndirme için en az bir sütun seçin!")

# İLK AÇILIŞ BİLGİLENDİRME
if st.session_state.scraped_data is None and not submitted:
    st.info("👆 Yukarıdaki formu doldurun ve **'Scraping Başlat'** düğmesine tıklayın.")
    
    # Sistem hakkında
    st.markdown("---")
    st.subheader("ℹ️ Sistem Özellikleri - Sadece Gerçek Veri")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 📱 Play Store İşlemleri:
        - **🔥 Gerçek Veri** - google-play-scraper kütüphanesi
        - **🔧 Versiyon Düzeltme** - Boş versiyonları akıllı doldurma  
        - **🌍 Çeviri** - Türkçe olmayanları çevirme
        - **📊 Sütun İşleme** - Standardizasyon
        
        ### 🍎 App Store İşlemleri:
        - **🔥 Gerçek RSS** - iTunes RSS API
        - **📊 Veri İşleme** - Tarih formatlama ve standardizasyon
        """)
    
    with col2:
        st.markdown("""
        ### ⚠️ Önemli Notlar:
        - **Sadece gerçek API'ler kullanılır**
        - **Mock/sahte veri üretilmez**
        - **Veri bulunammazsa boş sonuç döner**
        - **Tarih aralığını genişletmeyi deneyin**
        
        ### 📊 Analiz Özellikleri:
        - **🥧 Rating Dağılım Grafikleri**
        - **📈 Versiyon Bazında Analiz**
        - **🔄 Platform Karşılaştırması**
        """)