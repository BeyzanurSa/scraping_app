import streamlit as st
import pandas as pd
from datetime import datetime
from io import StringIO
import time

try:
    from googletrans import Translator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    Translator = None
    TRANSLATOR_AVAILABLE = False

def detect_text_columns(df):
    """CSV'deki metin sütunlarını otomatik tespit et"""
    text_columns = []
    possible_text_columns = ['text', 'content', 'review', 'comment', 'title', 'description', 'body']
    
    for col in df.columns:
        # Sütun adı kontrolü
        if any(keyword in col.lower() for keyword in possible_text_columns):
            text_columns.append(col)
        # Veri tipi kontrolü
        elif df[col].dtype == 'object':
            # İlk birkaç değeri kontrol et
            sample_values = df[col].dropna().head(5)
            if len(sample_values) > 0:
                avg_length = sum(len(str(val)) for val in sample_values) / len(sample_values)
                if avg_length > 20:  # Ortalama 20 karakterden uzun ise metin olabilir
                    text_columns.append(col)
    
    return text_columns

def detect_language_columns(df):
    """CSV'deki dil sütunlarını otomatik tespit et"""
    language_columns = []
    possible_lang_columns = ['lang', 'language', 'locale', 'country_code', 'dil']
    
    for col in df.columns:
        if any(keyword in col.lower() for keyword in possible_lang_columns):
            language_columns.append(col)
    
    return language_columns

def is_turkish_text(text, lang_code=None):
    """Metinin Türkçe olup olmadığını kontrol et"""
    if lang_code:
        # Dil kodu varsa kontrol et
        return str(lang_code).lower().strip() in ['tr', 'turkish', 'türkçe', 'turkiye', 'turkey']
    
    # Dil kodu yoksa metin analizi (basit)
    turkish_chars = ['ç', 'ğ', 'ı', 'ö', 'ş', 'ü', 'Ç', 'Ğ', 'İ', 'Ö', 'Ş', 'Ü']
    text_str = str(text).lower()
    
    # Türkçe karakterlerin oranını kontrol et
    turkish_char_count = sum(1 for char in text_str if char in turkish_chars)
    total_chars = len([char for char in text_str if char.isalpha()])
    
    if total_chars == 0:
        return False
    
    turkish_ratio = turkish_char_count / total_chars
    return turkish_ratio > 0.05  # %5'ten fazla Türkçe karakter varsa Türkçe kabul et

def translate_text_batch(texts, source_lang, target_lang='tr', batch_size=10):
    """Metinleri toplu olarak çevir"""
    if not TRANSLATOR_AVAILABLE:
        # googletrans yoksa orijinal metinleri döndür
        try:
            st.warning("googletrans kütüphanesi bulunamadı. Metinler çevrilmeden korunacak.")
        except:
            pass
        return ["" if (pd.isna(t) or not str(t).strip()) else str(t) for t in texts]
    
    translator = Translator()
    translated_texts = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        batch_translated = []
        
        for text in batch:
            try:
                if pd.isna(text) or not str(text).strip():
                    batch_translated.append("")
                elif source_lang.lower() == target_lang.lower():
                    batch_translated.append(str(text))
                else:
                    result = translator.translate(str(text), src=source_lang, dest=target_lang)
                    batch_translated.append(result.text)
            except Exception as e:
                st.warning(f"Çeviri hatası: {e}")
                batch_translated.append(str(text))  # Hata durumunda orijinal metni koru
        
        translated_texts.extend(batch_translated)
        time.sleep(0.5)  # Rate limiting için kısa bekleme
    
    return translated_texts

def translate_reviews(df):
    """Ana çeviri fonksiyonu - Sadece Türkçe olmayanları çevir - İYİLEŞTİRİLMİŞ"""
    try:
        if df is None or df.empty:
            return df
        
        # Metin sütunlarını tespit et
        text_columns = detect_text_columns(df)
        
        if not text_columns:
            # Varsayılan sütun isimleri dene
            possible_columns = ['content', 'review_text', 'text', 'title']
            for col in possible_columns:
                if col in df.columns:
                    text_columns = [col]
                    break
        
        if not text_columns:
            # Eğer hiç metin sütunu yoksa, content sütununu koru
            df_result = df.copy()
            if 'content' in df.columns:
                df_result['translated_text'] = df_result['content'].astype(str).fillna("")
            else:
                df_result['translated_text'] = ""
            return df_result
        
        # İlk metin sütununu çevir
        text_column = text_columns[0]
        
        # Dil sütununu tespit et
        language_columns = detect_language_columns(df)
        lang_column = language_columns[0] if language_columns else None

        df_result = df.copy()

        if not TRANSLATOR_AVAILABLE:
            # Kütüphane yoksa orijinal metni koru
            try:
                import streamlit as st
                st.warning("googletrans kurulu değil. translated_text orijinal metinle doldurulacak.")
            except:
                pass
            df_result['translated_text'] = df_result[text_column].astype(str).fillna("")
            
            try:
                import streamlit as st
                st.session_state.translation_stats = {
                    'total': len(df_result),
                    'translated': 0,
                    'skipped_turkish': len(df_result),
                    'empty_or_error': 0
                }
            except:
                pass
            return df_result

        # googletrans mevcutsa normal akış
        translated_texts = []
        skipped_count = 0
        translated_count = 0

        try:
            translator = Translator()  # Tek örnek
        except:
            # Translator oluşturulamazsa fallback
            df_result['translated_text'] = df_result[text_column].astype(str).fillna("")
            return df_result

        for idx, row in df_result.iterrows():
            text = row[text_column]
            lang_code = row[lang_column] if lang_column else None
            try:
                if pd.isna(text) or not str(text).strip():
                    translated_texts.append("")
                elif is_turkish_text(text, lang_code):
                    translated_texts.append(str(text))
                    skipped_count += 1
                else:
                    result = translator.translate(str(text), src='auto', dest='tr')
                    translated_texts.append(result.text)
                    translated_count += 1
                if idx % 10 == 0 and idx > 0:
                    time.sleep(0.5)
            except Exception as e:
                translated_texts.append(str(text))

        df_result['translated_text'] = translated_texts
        
        # İstatistikleri session state'e kaydet (sadece streamlit kontekstinde)
        try:
            import streamlit as st
            st.session_state.translation_stats = {
                'total': len(df_result),
                'translated': translated_count,
                'skipped_turkish': skipped_count,
                'empty_or_error': len(df_result) - translated_count - skipped_count
            }
        except:
            pass  # Streamlit context yoksa ignore et
        
        return df_result

    except Exception as e:
        try:
            import streamlit as st
            st.error(f"Çeviri hatası: {e}")
        except:
            pass
        return df

def main():
    st.set_page_config(
        page_title="🌐 Smart Review Translator",
        page_icon="🌐",
        layout="wide"
    )
    
    # Ana içerik başında kütüphane durumu kontrolü
    if not TRANSLATOR_AVAILABLE:
        st.error("❌ googletrans kütüphanesi yüklü değil!")
        st.info("📦 Kurulum: `pip install googletrans==4.0.0rc1` veya `pip install googletrans==3.1.0a0`")
    
    st.title("🌐 Smart Review Translator")
    st.markdown("📝 Türkçe yorumları koruyarak diğer dilleri Türkçe'ye çevirin")
    st.markdown("---")
    
    # Sidebar - Ayarlar
    with st.sidebar:
        st.header("⚙️ Akıllı Çeviri Ayarları")
        
        target_language = st.selectbox(
            "Hedef Dil",
            options=['tr', 'en', 'de', 'fr', 'es', 'it'],
            index=0,
            format_func=lambda x: {
                'tr': '🇹🇷 Türkçe',
                'en': '🇺🇸 İngilizce',
                'de': '🇩🇪 Almanca',
                'fr': '🇫🇷 Fransızca',
                'es': '🇪🇸 İspanyolca',
                'it': '🇮🇹 İtalyanca'
            }[x]
        )
        
        batch_size = st.slider("Batch Boyutu", min_value=5, max_value=50, value=10, 
                              help="Aynı anda çevrilecek metin sayısı")
        
        auto_detect = st.checkbox("Dil Otomatik Tespit", value=True,
                                 help="Kaynak dili otomatik tespit et")
        
        st.markdown("---")
        
        # Türkçe atlama ayarları
        st.subheader("🇹🇷 Türkçe Koruma")
        
        skip_turkish = st.checkbox("Türkçe yorumları atla", value=True,
                                  help="lang=tr olan yorumları çevirme")
        
        turkish_detection_method = st.radio(
            "Türkçe tespit yöntemi:",
            ["Dil sütunu (lang)", "Otomatik tespit", "Her ikisi"],
            index=0,
            help="Türkçe metinleri nasıl tespit edilsin?"
        )
    
    # Ana içerik
    tab1, tab2, tab3 = st.tabs(["📁 Dosya Yükleme", "🔧 Gelişmiş Ayarlar", "📊 İstatistikler"])
    
    with tab1:
        # Dosya yükleme
        uploaded_file = st.file_uploader(
            "📁 CSV Dosyası Yükleyin",
            type=['csv'],
            help="Çevrilecek metinleri içeren CSV dosyasını yükleyin"
        )
        
        if uploaded_file is not None:
            try:
                # Dosyayı oku
                df = pd.read_csv(uploaded_file)
                
                st.success(f"✅ Dosya yüklendi: {len(df)} satır, {len(df.columns)} sütun")
                
                # Sütun bilgileri
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📊 Dosya Bilgileri")
                    st.metric("Toplam Satır", len(df))
                    st.metric("Toplam Sütun", len(df.columns))
                    
                    # Mevcut sütunlar
                    st.write("**Mevcut Sütunlar:**")
                    for col in df.columns:
                        st.write(f"• {col}")
                
                with col2:
                    st.subheader("🎯 Sütun Analizi")
                    
                    # Otomatik tespit edilen sütunlar
                    text_columns = detect_text_columns(df)
                    language_columns = detect_language_columns(df)
                    
                    if text_columns:
                        st.write("**📝 Tespit edilen metin sütunları:**")
                        for col in text_columns:
                            st.write(f"• {col}")
                    
                    if language_columns:
                        st.write("**🌐 Tespit edilen dil sütunları:**")
                        for col in language_columns:
                            st.write(f"• {col}")
                            
                            # Dil dağılımını göster
                            if col in df.columns:
                                lang_dist = df[col].value_counts().head(5)
                                st.write("**Dil dağılımı (Top 5):**")
                                for lang, count in lang_dist.items():
                                    percentage = (count / len(df)) * 100
                                    flag = "🇹🇷" if str(lang).lower() in ['tr', 'turkish'] else "🌍"
                                    st.write(f"  {flag} {lang}: {count} (%{percentage:.1f})")
                
                # Türkçe içerik analizi
                if language_columns:
                    st.markdown("---")
                    st.subheader("🇹🇷 Türkçe İçerik Analizi")
                    
                    lang_col = language_columns[0]
                    
                    # Türkçe olan satırları say
                    turkish_mask = df[lang_col].astype(str).str.lower().str.strip().isin(['tr', 'turkish', 'türkçe', 'turkiye', 'turkey'])
                    turkish_count = turkish_mask.sum()
                    non_turkish_count = len(df) - turkish_count
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("🇹🇷 Türkçe Yorumlar", turkish_count)
                    
                    with col2:
                        st.metric("🌍 Diğer Diller", non_turkish_count)
                    
                    with col3:
                        turkish_percentage = (turkish_count / len(df)) * 100 if len(df) > 0 else 0
                        st.metric("Türkçe Oranı", f"%{turkish_percentage:.1f}")
                    
                    # Görselleştirme
                    try:
                        import plotly.express as px
                        
                        lang_data = pd.DataFrame({
                            'Dil Grubu': ['Türkçe', 'Diğer'],
                            'Sayı': [turkish_count, non_turkish_count]
                        })
                        
                        fig = px.pie(lang_data, values='Sayı', names='Dil Grubu', 
                                   title='Dil Dağılımı',
                                   color_discrete_map={'Türkçe': '#e74c3c', 'Diğer': '#3498db'})
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                    except ImportError:
                        st.info("📊 Grafik için plotly gerekli")
                
                # Çeviri ayarları
                st.markdown("---")
                st.header("🔄 Çeviri Ayarları")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Çevrilecek sütun seçimi
                    text_column = st.selectbox(
                        "Çevrilecek Metin Sütunu",
                        options=df.columns.tolist(),
                        index=0 if not text_columns else df.columns.tolist().index(text_columns[0])
                    )
                
                with col2:
                    # Dil sütunu seçimi
                    if language_columns:
                        language_column = st.selectbox(
                            "Dil Sütunu",
                            options=language_columns,
                            index=0
                        )
                    else:
                        language_column = None
                        st.info("⚠️ Dil sütunu tespit edilemedi")
                        st.warning("Türkçe atlaması çalışmayabilir!")
                
                # Kaynak dil ayarı (eğer dil sütunu yoksa)
                if not language_column and not auto_detect:
                    source_language = st.selectbox(
                        "Kaynak Dil",
                        options=['en', 'tr', 'de', 'fr', 'es', 'it'],
                        index=0,
                        format_func=lambda x: {
                            'tr': '🇹🇷 Türkçe',
                            'en': '🇺🇸 İngilizce',
                            'de': '🇩🇪 Almanca',
                            'fr': '🇫🇷 Fransızca',
                            'es': '🇪🇸 İspanyolca',
                            'it': '🇮🇹 İtalyanca'
                        }[x]
                    )
                else:
                    source_language = 'auto'
                
                # Önizleme - Türkçe ve diğer dilleri ayır
                st.subheader("👁️ Çeviri Önizlemesi")
                
                if text_column in df.columns and language_column:
                    # Türkçe olmayan örnekler
                    non_turkish_mask = ~df[language_column].astype(str).str.lower().str.strip().isin(['tr', 'turkish', 'türkçe'])
                    non_turkish_samples = df[non_turkish_mask][text_column].dropna().head(2)
                    
                    # Türkçe örnekler  
                    turkish_mask = df[language_column].astype(str).str.lower().str.strip().isin(['tr', 'turkish', 'türkçe'])
                    turkish_samples = df[turkish_mask][text_column].dropna().head(2)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**🌍 Çevrilecek Metinler (Türkçe Olmayan):**")
                        for i, text in enumerate(non_turkish_samples, 1):
                            with st.expander(f"Örnek {i}", expanded=i==1):
                                row_index = non_turkish_samples.index[i-1]
                                lang = df.loc[row_index, language_column]
                                st.write(f"**Dil:** {lang}")
                                st.write(f"**Metin:** {str(text)[:200]}...")
                                st.info("➡️ Bu metin çevrilecek")
                    
                    with col2:
                        st.write("**🇹🇷 Atlanacak Metinler (Türkçe):**")
                        for i, text in enumerate(turkish_samples, 1):
                            with st.expander(f"TR Örnek {i}", expanded=i==1):
                                st.write(f"**Metin:** {str(text)[:200]}...")
                                st.success("✅ Bu metin atlanacak (zaten Türkçe)")
                
                # Çeviri başlat
                st.markdown("---")
                
                if st.button("🚀 Akıllı Çeviriyi Başlat", type="primary"):
                    if Translator is None: 
                        st.warning("googletrans yok, orijinal metin korunacak")
                    
                    # Boş olmayan metinleri filtrele
                    df_to_process = df[df[text_column].notna() & (df[text_column] != '')].copy()
                    
                    if len(df_to_process) == 0:
                        st.error("❌ İşlenecek metin bulunamadı!")
                        return
                    
                    # Türkçe olanları ayır
                    if language_column and skip_turkish:
                        turkish_mask = df_to_process[language_column].astype(str).str.lower().str.strip().isin(['tr', 'turkish', 'türkçe', 'turkiye', 'turkey'])
                        turkish_count = turkish_mask.sum()
                        non_turkish_count = len(df_to_process) - turkish_count
                        
                        st.info(f"""
                        📊 **İşlem Planı:**
                        - 🇹🇷 Türkçe yorumlar: {turkish_count} (atlanacak)
                        - 🌍 Diğer dil yorumları: {non_turkish_count} (çevrilecek)
                        - 📊 Toplam işlenecek: {len(df_to_process)}
                        """)
                    else:
                        st.info(f"📊 {len(df_to_process)} metin işlenecek...")
                    
                    # Progress tracking
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    translated_texts = []
                    total_texts = len(df_to_process)
                    turkish_skipped = 0
                    actually_translated = 0
                    errors = 0
                    
                    for idx, (_, row) in enumerate(df_to_process.iterrows()):
                        text_to_process = str(row[text_column])
                        
                        # Dil kodunu belirle
                        if language_column and language_column in df.columns:
                            source_lang = str(row[language_column]).strip()
                        else:
                            source_lang = source_language
                        
                        try:
                            # Türkçe kontrolü
                            if skip_turkish and is_turkish_text(text_to_process, source_lang):
                                # Türkçe ise atla
                                translated_texts.append(text_to_process)
                                turkish_skipped += 1
                                status_text.text(f"🇹🇷 Türkçe atlandı: {idx + 1}/{total_texts}")
                            else:
                                # Türkçe değilse çevir
                                if source_lang.lower() == target_language.lower():
                                    translated_text = text_to_process
                                else:
                                    translator = Translator()
                                    result = translator.translate(text_to_process, 
                                                                src=source_lang if source_lang != 'auto' else None, 
                                                                dest=target_language)
                                    translated_text = result.text
                                
                                translated_texts.append(translated_text)
                                actually_translated += 1
                                status_text.text(f"🌍 Çevriliyor: {idx + 1}/{total_texts}")
                            
                            # Progress güncelle
                            progress = (idx + 1) / total_texts
                            progress_bar.progress(progress)
                            
                            # Rate limiting
                            if idx % batch_size == 0 and idx > 0:
                                time.sleep(1)
                            
                        except Exception as e:
                            st.warning(f"⚠️ Satır {idx+1} çeviri hatası: {e}")
                            translated_texts.append(text_to_process)
                            errors += 1
                    
                    # Çevrilmiş metinleri DataFrame'e ekle
                    df_result = df.copy()
                    df_result['translated_text'] = None
                    
                    # Sadece işlenen satırları güncelle
                    df_result.loc[df_to_process.index, 'translated_text'] = translated_texts
                    
                    # Session state'e kaydet
                    st.session_state.translated_df = df_result
                    st.session_state.translation_complete = True
                    st.session_state.translation_stats = {
                        'total_processed': len(df_to_process),
                        'turkish_skipped': turkish_skipped,
                        'actually_translated': actually_translated,
                        'errors': errors,
                        'success_rate': (actually_translated / len(df_to_process)) * 100 if len(df_to_process) > 0 else 0
                    }
                    
                    st.success(f"""
                    ✅ **Akıllı çeviri tamamlandı!**
                    - 🇹🇷 Türkçe atlandı: {turkish_skipped}
                    - 🌍 Çevrildi: {actually_translated}
                    - ❌ Hata: {errors}
                    """)
                
            except Exception as e:
                st.error(f"❌ Dosya okunurken hata oluştu: {e}")
    
    with tab2:
        st.header("🔧 Gelişmiş Çeviri Ayarları")
        
        st.markdown("""
        ### 🧠 Akıllı Türkçe Tespiti
        
        **Dil Sütunu Kontrolü:**
        - `lang`, `language`, `locale` sütunlarını otomatik tespit eder
        - `tr`, `turkish`, `türkçe` değerlerini Türkçe olarak kabul eder
        - Türkçe tespit edilen metinler çevrilmez
        
        **Otomatik Tespit:**
        - Metin içindeki Türkçe karakterleri analiz eder (ç, ğ, ı, ö, ş, ü)
        - %5'ten fazla Türkçe karakter varsa Türkçe kabul eder
        
        **Çeviri Optimizasyonu:**
        - Türkçe metinler çevrilmediği için işlem hızı artar
        - API kullanımı azalır
        - Orijinal Türkçe kalitesi korunur
        """)
        
        st.markdown("### ⚙️ Batch İşleme")
        st.markdown("""
        **Optimum Ayarlar:**
        - Küçük dosyalar (<1000 satır): Batch boyutu 5-10
        - Orta dosyalar (1000-5000 satır): Batch boyutu 10-20  
        - Büyük dosyalar (>5000 satır): Batch boyutu 20-50
        
        **Rate Limiting:**
        - Her 10 istekte 0.5 saniye bekleme
        - Her batch'te 1 saniye bekleme
        - Google Translate limitlerini aşmamak için
        """)
        
        st.markdown("### 🎯 Desteklenen Formatlar")
        st.markdown("""
        **Metin Sütunları:**
        - `text`, `content`, `review`, `comment`
        - `title`, `description`, `body`
        - Otomatik tespit: >20 karakter ortalama uzunluk
        
        **Dil Sütunları:**
        - `lang`, `language`, `locale`  
        - `country_code`, `dil`
        - ISO 639-1 kodları (tr, en, de, fr, es, it)
        """)
    
    with tab3:
        st.header("📊 Çeviri İstatistikleri")
        
        if hasattr(st.session_state, 'translation_stats'):
            stats = st.session_state.translation_stats
            
            # Ana metrikler
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📊 Toplam İşlenen", stats['total_processed'])
            
            with col2:
                st.metric("🇹🇷 Türkçe Atlanan", stats['turkish_skipped'])
            
            with col3:
                st.metric("🌍 Çevrilen", stats['actually_translated'])
            
            with col4:
                st.metric("❌ Hata", stats['errors'])
            
            # Oranlar
            st.subheader("📈 İşlem Oranları")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                skip_rate = (stats['turkish_skipped'] / stats['total_processed']) * 100 if stats['total_processed'] > 0 else 0
                st.metric("🇹🇷 Türkçe Atlama Oranı", f"%{skip_rate:.1f}")
            
            with col2:
                translation_rate = (stats['actually_translated'] / stats['total_processed']) * 100 if stats['total_processed'] > 0 else 0
                st.metric("🌍 Çeviri Oranı", f"%{translation_rate:.1f}")
            
            with col3:
                error_rate = (stats['errors'] / stats['total_processed']) * 100 if stats['total_processed'] > 0 else 0
                st.metric("❌ Hata Oranı", f"%{error_rate:.1f}")
            
            # Görselleştirme
            try:
                import plotly.express as px
                
                stats_data = pd.DataFrame({
                    'İşlem Tipi': ['Türkçe Atlanan', 'Çevrilen', 'Hata'],
                    'Sayı': [stats['turkish_skipped'], stats['actually_translated'], stats['errors']],
                    'Renk': ['#e74c3c', '#27ae60', '#f39c12']
                })
                
                fig = px.bar(stats_data, x='İşlem Tipi', y='Sayı', 
                           color='İşlem Tipi',
                           title='Çeviri İşlem Dağılımı',
                           color_discrete_map={
                               'Türkçe Atlanan': '#e74c3c',
                               'Çevrilen': '#27ae60', 
                               'Hata': '#f39c12'
                           })
                
                st.plotly_chart(fig, use_container_width=True)
                
            except ImportError:
                st.info("📊 Detaylı grafik için plotly gerekli")
        else:
            st.info("📊 Henüz çeviri işlemi yapılmadı")
    
    # Çeviri sonuçlarını göster
    if hasattr(st.session_state, 'translation_complete') and st.session_state.translation_complete:
        st.markdown("---")
        st.header("📊 Çeviri Sonuçları")
        
        df_result = st.session_state.translated_df
        
        # İNDİRME DOSYALARINI ÖNCEDEN HAZIRLA - SESSION STATE KONTROLÜ
        if 'translation_download_files' not in st.session_state:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Sütun seçimi için varsayılan değerler
            all_columns = df_result.columns.tolist()
            default_columns = []
            important_columns = ['translated_text', 'content', 'rating', 'author_name', 'date', 'app_version', 'helpful_count']
            
            for col in important_columns:
                if col in all_columns:
                    default_columns.append(col)
            
            if 'translated_text' in all_columns and 'translated_text' not in default_columns:
                default_columns.insert(0, 'translated_text')
            
            # Varsayılan sütunlarla dosyaları hazırla
            selected_columns = default_columns[:7] if len(default_columns) >= 7 else default_columns
            if not selected_columns:
                selected_columns = ['translated_text'] if 'translated_text' in df_result.columns else [df_result.columns[0]]
            
            # Dosyaları hazırla ve session state'e kaydet
            final_df = df_result[selected_columns].copy()
            
            # CSV hazırla
            csv_buffer = StringIO()
            final_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
            
            # JSON hazırla
            json_data = final_df.to_json(orient='records', force_ascii=False, indent=2)
            
            # Tam CSV hazırla
            full_csv_buffer = StringIO()
            df_result.to_csv(full_csv_buffer, index=False, encoding='utf-8-sig')
            
            st.session_state.translation_download_files = {
                'selected_csv': {
                    'data': csv_buffer.getvalue(),
                    'filename': f"translated_selected_{timestamp}.csv",
                    'columns': selected_columns
                },
                'selected_json': {
                    'data': json_data,
                    'filename': f"translated_selected_{timestamp}.json"
                },
                'full_csv': {
                    'data': full_csv_buffer.getvalue(),
                    'filename': f"translated_full_{timestamp}.csv"
                },
                'timestamp': timestamp,
                'default_columns': selected_columns
            }
        
        # Gelişmiş istatistikler
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 Toplam Satır", len(df_result))
        
        with col2:
            translated_count = df_result['translated_text'].notna().sum()
            st.metric("✅ İşlenen Metin", translated_count)
        
        with col3:
            if hasattr(st.session_state, 'translation_stats'):
                stats = st.session_state.translation_stats
                st.metric("🌍 Gerçek Çeviri", stats['actually_translated'])
            else:
                st.metric("🌍 Çevrilen", "N/A")
        
        with col4:
            if hasattr(st.session_state, 'translation_stats'):
                efficiency = (stats['actually_translated'] / translated_count) * 100 if translated_count > 0 else 0
                st.metric("⚡ Verimlilik", f"%{efficiency:.1f}")
            else:
                st.metric("⚡ Verimlilik", "N/A")
        
        # Çeviri örnekleri - Türkçe ve çevrilmiş ayrı
        st.subheader("🔄 Çeviri Örnekleri")
        
        col1, col2 = st.columns(2)
        
        # Çevrilen metinler (Türkçe olmayanlar)
        with col1:
            st.write("**🌍 Çevrilen Metinler:**")
            
            # language_column varsa kullan
            if 'language_column' in locals() and language_column:
                non_turkish_mask = ~df_result[language_column].astype(str).str.lower().str.strip().isin(['tr', 'turkish', 'türkçe'])
                translated_samples = df_result[non_turkish_mask & df_result['translated_text'].notna()].head(2)
            else:
                translated_samples = df_result[df_result['translated_text'].notna()].head(2)
            
            for i, (_, row) in enumerate(translated_samples.iterrows(), 1):
                with st.expander(f"Çeviri Örnek {i}", expanded=i==1):
                    if 'text_column' in locals() and text_column in df_result.columns:
                        original_text = str(row[text_column])
                        st.write("**🌍 Orijinal:**")
                        st.write(original_text[:200] + "..." if len(original_text) > 200 else original_text)
                    
                    translated_text = str(row['translated_text'])
                    st.write("**🇹🇷 Çevrilmiş:**")
                    st.write(translated_text[:200] + "..." if len(translated_text) > 200 else translated_text)
                    
                    if 'language_column' in locals() and language_column in df_result.columns:
                        st.write(f"**🌐 Kaynak Dil:** {row.get(language_column, 'Bilinmiyor')}")
        
        # Türkçe metinler (atlanan)
        with col2:
            st.write("**🇹🇷 Türkçe Metinler (Atlanan):**")
            
            if 'language_column' in locals() and language_column:
                turkish_mask = df_result[language_column].astype(str).str.lower().str.strip().isin(['tr', 'turkish', 'türkçe'])
                turkish_samples = df_result[turkish_mask & df_result['translated_text'].notna()].head(2)
                
                for i, (_, row) in enumerate(turkish_samples.iterrows(), 1):
                    with st.expander(f"Türkçe Örnek {i}", expanded=i==1):
                        turkish_text = str(row['translated_text'])
                        st.write("**🇹🇷 Türkçe Metin:**")
                        st.write(turkish_text[:200] + "..." if len(turkish_text) > 200 else turkish_text)
                        st.success("✅ Çevrilmeden korundu")
            else:
                st.info("Dil sütunu tespit edilemediği için Türkçe ayrımı yapılamadı")
        
        # DataFrame görüntüleme ve sütun seçimi - YENİDEN TASARLANDI
        st.subheader("📋 İşlenmiş Veri Tablosu ve Sütun Seçimi")
        
        # Mevcut dosya bilgilerini göster
        if 'translation_download_files' in st.session_state:
            current_files = st.session_state.translation_download_files
            
            st.info(f"""
            **📁 Hazır Dosyalar:**
            - 📄 Seçili sütunlar CSV: {len(current_files['default_columns'])} sütun
            - 📄 JSON formatı: {len(df_result)} kayıt
            - 📄 Tam CSV: {len(df_result.columns)} sütun
            """)
        
        # Sütun seçimi (isteğe bağlı yeniden oluşturma)
        st.write("**🔄 Dosyaları yeniden oluşturmak isterseniz:**")
        
        all_columns = df_result.columns.tolist()
        
        # Varsayılan sütunları göster
        if 'translation_download_files' in st.session_state:
            default_selection = st.session_state.translation_download_files['default_columns']
        else:
            default_selection = []
        
        with st.expander("📋 Sütun Seçimini Değiştir", expanded=False):
            columns_for_download = st.multiselect(
                "İndirme için sütunları seçin:",
                all_columns,
                default=default_selection,
                help="İndirmek istediğiniz sütunları seçin. translated_text önerilir.",
                key="translation_column_selector"
            )
            
            if st.button("🔄 Dosyaları Yeniden Oluştur", key="regenerate_files"):
                if columns_for_download:
                    # Yeni dosyaları oluştur
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    final_df = df_result[columns_for_download].copy()
                    
                    # CSV hazırla
                    csv_buffer = StringIO()
                    final_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                    
                    # JSON hazırla
                    json_data = final_df.to_json(orient='records', force_ascii=False, indent=2)
                    
                    # Session state'i güncelle
                    st.session_state.translation_download_files.update({
                        'selected_csv': {
                            'data': csv_buffer.getvalue(),
                            'filename': f"translated_selected_{timestamp}.csv",
                            'columns': columns_for_download
                        },
                        'selected_json': {
                            'data': json_data,
                            'filename': f"translated_selected_{timestamp}.json"
                        },
                        'default_columns': columns_for_download
                    })
                    
                    st.success("✅ Dosyalar yeniden oluşturuldu!")
                    st.rerun()
                else:
                    st.warning("⚠️ En az bir sütun seçin!")
        
        # Seçili sütunlarla önizleme
        if 'translation_download_files' in st.session_state:
            current_columns = st.session_state.translation_download_files['default_columns']
            if current_columns:
                st.write(f"**📊 Mevcut seçim ({len(current_columns)} sütun):** {', '.join(current_columns)}")
                preview_df = df_result[current_columns].head(10)
                st.dataframe(preview_df, use_container_width=True)
        
        # İndirme seçenekleri - HAZIR DOSYALARI KULLAN
        st.subheader("💾 İndirme Seçenekleri")
        
        if 'translation_download_files' in st.session_state:
            download_files = st.session_state.translation_download_files
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Seçili sütunlar CSV
                st.download_button(
                    label="📄 Seçili Sütunlar CSV",
                    data=download_files['selected_csv']['data'],
                    file_name=download_files['selected_csv']['filename'],
                    mime="text/csv",
                    type="primary",
                    help=f"Seçilen {len(download_files['selected_csv']['columns'])} sütun",
                    key="dl_selected_csv"
                )
            
            with col2:
                # Seçili sütunlar JSON
                st.download_button(
                    label="📄 Seçili Sütunlar JSON",
                    data=download_files['selected_json']['data'],
                    file_name=download_files['selected_json']['filename'],
                    mime="application/json",
                    help=f"JSON formatında {len(df_result)} kayıt",
                    key="dl_selected_json"
                )
            
            with col3:
                # Tam CSV
                st.download_button(
                    label="📄 Tam CSV (Tüm Sütunlar)",
                    data=download_files['full_csv']['data'],
                    file_name=download_files['full_csv']['filename'],
                    mime="text/csv",
                    help=f"Tüm {len(df_result.columns)} sütun dahil",
                    key="dl_full_csv"
                )
        
        # İndirme sonrası bilgilendirme
        st.markdown("---")
        st.subheader("📋 İndirme Özeti")
        
        if 'translation_download_files' in st.session_state and hasattr(st.session_state, 'translation_stats'):
            download_files = st.session_state.translation_download_files
            stats = st.session_state.translation_stats
            
            summary_col1, summary_col2 = st.columns(2)
            
            with summary_col1:
                st.info(f"""
                **📊 Seçilen Veri Özeti:**
                - 📄 Seçilen sütun: {len(download_files['default_columns'])}
                - 📊 Toplam satır: {len(df_result):,}
                - 🌍 Çevrilen: {stats.get('actually_translated', 0)}
                - 🇹🇷 Türkçe korunan: {stats.get('turkish_skipped', 0)}
                """)
            
            with summary_col2:
                timestamp = download_files['timestamp']
                st.success(f"""
                **✅ Hazır Dosyalar:**
                - 📄 translated_selected_{timestamp}.csv
                - 📄 translated_selected_{timestamp}.json
                - 📄 translated_full_{timestamp}.csv
                
                **📅 İşlem Tarihi:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                """)
        
        # Sayfa durumunu koruma için session state güncelleme
        if 'translation_results' not in st.session_state:
            st.session_state.translation_results = {}
        
        st.session_state.translation_results = {
            'completed_time': timestamp,
            'total_rows': len(df_result),
            'selected_columns': columns_for_download,
            'stats': st.session_state.translation_stats if hasattr(st.session_state, 'translation_stats') else {}
        }

    # Yardım ve bilgi
    if not uploaded_file:
        st.info("📁 Başlamak için bir CSV dosyası yükleyin")
        
        st.markdown("### 🧠 Akıllı Çeviri Özellikleri")
        st.markdown("""
        **🇹🇷 Türkçe Koruma:**
        - `lang=tr` olan yorumlar otomatik atlanır
        - Türkçe karakterli metinler tespit edilir
        - Orijinal Türkçe kalitesi korunur
        
        **⚡ Performans Optimizasyonu:**
        - Gereksiz API çağrıları önlenir
        - İşlem hızı artar
        - Maliyet düşer
        
        **📊 Detaylı Analiz:**
        - Hangi metinlerin çevrildiği izlenir
        - Türkçe atlama oranları hesaplanır
        - Verimlilik metrikleri sunulur
        """)
        
        st.markdown("### 📋 Desteklenen Format")
        st.markdown("""
        **Gerekli Sütunlar:**
        - **Metin sütunu:** `text`, `content`, `review`, `comment` vb.
        - **Dil sütunu:** `lang`, `language`, `locale` (önerilen)
        
        **Dil Kodları:**
        - `tr`: Türkçe (atlanacak)
        - `en`: İngilizce (çevrilecek)
        - `de`, `fr`, `es`, `it`: Diğer diller (çevrilecek)
        """)