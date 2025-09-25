import streamlit as st
import requests
import json
import time
import csv
import os
from datetime import datetime, timezone
import random
import re
import pandas as pd
from io import StringIO
import math
from typing import Optional

class SafeRSSAppStoreScraper:
    def __init__(self):
        self.session = requests.Session()
        
        # Daha güvenli headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })

    def parse_date_string(self, date_str):
        """Tarih string'ini datetime objesine çevir"""
        if not date_str:
            return None
            
        try:
            # Apple'ın kullandığı format: "2024-01-15T10:30:45-07:00"
            if 'T' in date_str:
                clean_date = re.sub(r'[-+]\d{2}:\d{2}$', '', date_str)
                if '.' in clean_date:
                    clean_date = clean_date.split('.')[0]
                return datetime.fromisoformat(clean_date.replace('T', ' '))
            
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%Y-%m-%dT%H:%M:%S',
                '%d.%m.%Y',
                '%d/%m/%Y'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
                    
        except Exception as e:
            st.error(f"Tarih parse hatası: {date_str} -> {e}")
            
        return None

    def is_date_in_range(self, review_date_str, start_date, end_date):
        """Review tarihinin belirtilen tarih aralığında olup olmadığını kontrol et"""
        if not review_date_str:
            return True
            
        review_date = self.parse_date_string(review_date_str)
        if not review_date:
            return True
        
        if start_date and review_date < start_date:
            return False
        if end_date and review_date > end_date:
            return False
            
        return True

    def safe_get_label(self, entry, key):
        """Güvenli label çekme"""
        try:
            value = entry.get(key, {})
            if isinstance(value, dict):
                return value.get('label', '')
            return str(value) if value else ''
        except:
            return ''

    def safe_get_rating(self, entry):
        """Güvenli rating çekme"""
        try:
            rating_str = entry.get('im:rating', {}).get('label', '0')
            return int(rating_str) if rating_str and rating_str.isdigit() else 0
        except:
            return 0

    def safe_get_author(self, entry):
        """Güvenli author çekme"""
        try:
            author_info = entry.get('author', {})
            if isinstance(author_info, dict):
                name_info = author_info.get('name', {})
                if isinstance(name_info, dict):
                    return name_info.get('label', '')
                return str(name_info) if name_info else ''
            return str(author_info) if author_info else ''
        except:
            return ''

    def safe_rss_scraper(self, app_id, country='en', max_pages=50, delay_range=(2, 5), 
                        start_date_filter=None, end_date_filter=None, progress_callback=None,
                        max_reviews=None):  # YENİ PARAMETRE
        """Güvenli RSS Feed scraper with progress tracking and review limit"""
        
        start_date = None
        end_date = None
        
        if start_date_filter:
            try:
                if isinstance(start_date_filter, str):
                    start_date = datetime.strptime(start_date_filter, '%Y-%m-%d')
                else:
                    start_date = start_date_filter
            except ValueError:
                st.error(f"Geçersiz başlangıç tarih formatı: {start_date_filter}. YYYY-MM-DD formatı kullanın")
                return []
        
        if end_date_filter:
            try:
                if isinstance(end_date_filter, str):
                    end_date = datetime.strptime(end_date_filter, '%Y-%m-%d')
                else:
                    end_date = end_date_filter
            except ValueError:
                st.error(f"Geçersiz bitiş tarih formatı: {end_date_filter}. YYYY-MM-DD formatı kullanın")
                return []
        
        all_reviews = []
        page = 1
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        # HTTP hata türlerine göre sayaçlar
        http_400_count = 0
        http_502_count = 0
        http_429_count = 0
        consecutive_400_errors = 0
        max_consecutive_400_errors = 5
        max_specific_errors = 8
        
        # Tarih filtresi için geliştirilmiş mantık
        consecutive_out_of_range_pages = 0
        max_consecutive_out_of_range_pages = 15
        out_of_range_threshold = 0.9
        
        found_any_in_range = False
        total_pages_checked = 0
        min_pages_to_check = 10
        successful_pages = 0
        empty_pages_count = 0
        max_empty_pages = 3
    
        while page <= max_pages:
            # YORUM SAYISI LİMİT KONTROLÜ
            if max_reviews and len(all_reviews) >= max_reviews:
                break
            
            if progress_callback:
                progress_callback(page, max_pages, len(all_reviews))
            
            total_pages_checked += 1
            
            # RSS URL'si
            url = f"https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json"
            
            try:
                delay = random.uniform(delay_range[0], delay_range[1])
                time.sleep(delay)
                
                response = self.session.get(url, timeout=30)
                
                if response.status_code == 200:
                    successful_pages += 1
                    consecutive_errors = 0
                    consecutive_400_errors = 0
                    empty_pages_count = 0
                    
                    try:
                        data = response.json()
                        
                        if 'feed' in data and 'entry' in data['feed']:
                            entries = data['feed']['entry']
                            start_index = 1 if page == 1 else 0
                            
                            if len(entries) <= start_index:
                                empty_pages_count += 1
                                if empty_pages_count >= max_empty_pages:
                                    break
                                page += 1
                                continue
                            
                            page_reviews = []
                            filtered_count = 0
                            total_processed = 0
                            
                            for entry in entries[start_index:]:
                                # YORUM SAYISI LİMİT KONTROLÜ (sayfa içinde)
                                if max_reviews and len(all_reviews) >= max_reviews:
                                    break
                                
                                try:
                                    review = {
                                        'title': self.safe_get_label(entry, 'title'),
                                        'content': self.safe_get_label(entry, 'content'),
                                        'rating': self.safe_get_rating(entry),
                                        'author': self.safe_get_author(entry),
                                        'date': self.safe_get_label(entry, 'updated'),
                                        'version': self.safe_get_label(entry, 'im:version'),
                                        'id': self.safe_get_label(entry, 'id'),
                                        'page': page,
                                        'method': 'rss'
                                    }
                                    
                                    if review['content'] and review['content'].strip():
                                        total_processed += 1
                                        
                                        if self.is_date_in_range(review['date'], start_date, end_date):
                                            page_reviews.append(review)
                                            found_any_in_range = True
                                        else:
                                            filtered_count += 1
                                            
                                except Exception as e:
                                    continue
                        
                        # Sayfa değerlendirmesi
                        if total_processed > 0:
                            out_of_range_ratio = filtered_count / total_processed
                            
                            if page_reviews:
                                # YORUM SAYISI LİMİT KONTROLÜ (ekleme öncesi)
                                if max_reviews:
                                    remaining_slots = max_reviews - len(all_reviews)
                                    if remaining_slots <= 0:
                                        break
                                    page_reviews = page_reviews[:remaining_slots]
                                
                                all_reviews.extend(page_reviews)
                                
                                if out_of_range_ratio >= out_of_range_threshold:
                                    consecutive_out_of_range_pages += 1
                                else:
                                    consecutive_out_of_range_pages = 0
                                
                                should_stop = False
                                
                                if consecutive_out_of_range_pages >= max_consecutive_out_of_range_pages:
                                    if total_pages_checked >= min_pages_to_check:
                                        should_stop = True
                                
                                if not found_any_in_range and total_pages_checked >= min_pages_to_check * 2:
                                    should_stop = True
                                
                                if should_stop:
                                    break
                                
                                page += 1
                                
                            else:
                                if filtered_count > 0:
                                    consecutive_out_of_range_pages += 1
                                    
                                    if consecutive_out_of_range_pages >= max_consecutive_out_of_range_pages:
                                        if total_pages_checked >= min_pages_to_check:
                                            break
                                    
                                    page += 1
                                else:
                                    break
                        else:
                            break
                            
                    except json.JSONDecodeError as e:
                        consecutive_errors += 1
                        page += 1
                        
                # HTTP error handling...
                elif response.status_code == 400:
                    http_400_count += 1
                    consecutive_400_errors += 1
                    consecutive_errors += 1
                    
                    if consecutive_400_errors >= max_consecutive_400_errors:
                        break
                    
                    if http_400_count <= 3:
                        page += 1
                    elif http_400_count <= 6:
                        time.sleep(random.uniform(3, 5))
                        page += 1
                    else:
                        break
                        
                elif response.status_code == 502:
                    http_502_count += 1
                    consecutive_errors += 1
                    consecutive_400_errors = 0
                    
                    time.sleep(random.uniform(3, 6))
                    
                    if http_502_count >= max_specific_errors:
                        break
                    
                elif response.status_code == 429:
                    http_429_count += 1
                    consecutive_400_errors = 0
                    time.sleep(random.uniform(45, 75))
                    consecutive_errors += 1
                    
                    if http_429_count >= max_specific_errors:
                        break
                    
                elif response.status_code == 404:
                    consecutive_400_errors = 0
                    page += 1
                    consecutive_errors += 1
                    
                    if consecutive_errors >= 3:
                        break
                    
                else:
                    consecutive_errors += 1
                    consecutive_400_errors = 0
                    page += 1
                    time.sleep(random.uniform(3, 7))
                    
            except requests.exceptions.Timeout:
                consecutive_errors += 1
                consecutive_400_errors = 0
                page += 1
                
            except requests.exceptions.ConnectionError:
                consecutive_errors += 1
                consecutive_400_errors = 0
                page += 1
                time.sleep(random.uniform(5, 10))
                
            except Exception as e:
                consecutive_errors += 1
                consecutive_400_errors = 0
                page += 1
            
            if consecutive_errors >= max_consecutive_errors:
                break
                
            if page % 10 == 0 and successful_pages > 0:
                time.sleep(random.uniform(3, 6))
        
        return all_reviews

# Streamlit App
def main():
    
    st.set_page_config(
        page_title="RSS App Store Review Scraper",
        page_icon="📱",
        layout="wide"
    )
    
    st.title("📱 RSS App Store Review Scraper")
    st.markdown("---")
    
    # Global scraper instance - DÜZELTİLDİ
    if 'scraper' not in st.session_state:
        st.session_state.scraper = SafeRSSAppStoreScraper()
    
    # Sidebar - Ayarlar
    with st.sidebar:
        st.header("⚙️ Ayarlar")
        
        app_id = st.number_input("App ID", value=1360892562, min_value=1)
        country = st.selectbox("Ülke", ['tr', 'en', 'us', 'de', 'fr'], index=0)
        max_pages = st.slider("Maksimum Sayfa", min_value=5, max_value=100, value=30)
        
        delay_min = st.slider("Minimum Delay (saniye)", min_value=1, max_value=10, value=2)
        delay_max = st.slider("Maksimum Delay (saniye)", min_value=delay_min, max_value=15, value=4)
        
        st.markdown("### 📅 Tarih Filtresi")
        start_date = st.date_input("Başlangıç Tarihi", value=datetime(2024, 12, 5))
        end_date = st.date_input("Bitiş Tarihi", value=datetime(2025, 8, 15))
    
    # Ana içerik
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📊 Scraping İşlemi")
        
        if st.button("🚀 Scraping Başlat", type="primary"):
            scraper = st.session_state.scraper  # Session state'den al
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def progress_callback(current_page, max_pages, reviews_count):
                progress = current_page / max_pages
                progress_bar.progress(progress)
                status_text.text(f"Sayfa {current_page}/{max_pages} - {reviews_count} review bulundu")
            
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            with st.spinner('Reviews çekiliyor...'):
                reviews = scraper.safe_rss_scraper(
                    app_id=app_id,
                    country=country,
                    max_pages=max_pages,
                    delay_range=(delay_min, delay_max),
                    start_date_filter=start_date_str,
                    end_date_filter=end_date_str,
                    progress_callback=progress_callback
                )
            
            # Sonuçları session state'e kaydet
            st.session_state.reviews = reviews
            st.session_state.app_id = app_id
            st.session_state.start_date = start_date_str
            st.session_state.end_date = end_date_str
            
            if reviews:
                st.success(f"✅ {len(reviews)} review başarıyla çekildi!")
            else:
                st.error("❌ Hiçbir review alınamadı")
    
    with col2:
        st.header("📈 Scraping Bilgileri")
        
        if 'reviews' in st.session_state and st.session_state.reviews:
            reviews = st.session_state.reviews
            scraper = st.session_state.scraper  # Session state'den al - DÜZELTİLDİ
            
            # İstatistikler
            st.metric("Toplam Review", len(reviews))
            
            if reviews:
                ratings = [r.get('rating', 0) for r in reviews if r.get('rating', 0) > 0]
                if ratings:
                    avg_rating = sum(ratings) / len(ratings)
                    st.metric("Ortalama Rating", f"{avg_rating:.1f} ⭐")
                
                # Tarih aralığı
                dates = []
                for r in reviews:
                    date_obj = scraper.parse_date_string(r.get('date', ''))
                    if date_obj:
                        dates.append(date_obj)
                
                if dates:
                    dates.sort()
                    st.write("📅 **Tarih Aralığı:**")
                    st.write(f"En Eski: {dates[0].strftime('%Y-%m-%d %H:%M')}")
                    st.write(f"En Yeni: {dates[-1].strftime('%Y-%m-%d %H:%M')}")
    
    # Reviews görüntüleme
    if 'reviews' in st.session_state and st.session_state.reviews:
        st.markdown("---")
        st.header("📋 Review Sonuçları")
        
        reviews = st.session_state.reviews
        
        # İstatistikler
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Toplam Review", len(reviews))
        
        with col2:
            ratings = [r.get('rating', 0) for r in reviews if r.get('rating', 0) > 0]
            if ratings:
                avg_rating = sum(ratings) / len(ratings)
                st.metric("Ortalama Rating", f"{avg_rating:.1f} ⭐")
        
        with col3:
            authors = [r.get('author', '') for r in reviews if r.get('author', '')]
            unique_authors = len(set(authors))
            st.metric("Benzersiz Yazar", unique_authors)
        
        with col4:
            pages = [r.get('page', 0) for r in reviews]
            if pages:
                st.metric("Sayfa Aralığı", f"{min(pages)}-{max(pages)}")
        
        # Rating dağılımı
        if ratings:
            st.subheader("⭐ Rating Dağılımı")
            rating_counts = {}
            for i in range(1, 6):
                rating_counts[f"{i} ⭐"] = ratings.count(i)
            
            st.bar_chart(rating_counts)
        
        # DataFrame olarak göster
        st.subheader("📊 Review Tablosu")
        df = pd.DataFrame(reviews)
        
        # Sütun seçimi
        columns_to_show = st.multiselect(
            "Gösterilecek sütunları seçin:",
            df.columns.tolist(),
            default=['title', 'rating', 'author', 'date', 'content'][:len(df.columns)]
        )
        
        if columns_to_show:
            st.dataframe(df[columns_to_show], use_container_width=True)
        
        # Download butonları
        st.subheader("💾 İndirme Seçenekleri")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # CSV download
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False, encoding='utf-8')
            st.download_button(
                label="📄 CSV İndir",
                data=csv_buffer.getvalue(),
                file_name=f"rss_reviews_{st.session_state.app_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # JSON download
            json_str = json.dumps(reviews, indent=2, ensure_ascii=False, default=str)
            st.download_button(
                label="📄 JSON İndir",
                data=json_str,
                file_name=f"rss_reviews_{st.session_state.app_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        with col3:
            # TXT download
            txt_content = ""
            for i, review in enumerate(reviews[:5], 1):
                txt_content += f"{i}. Review:\n"
                txt_content += f"Rating: {review.get('rating', 'N/A')} ⭐\n"
                txt_content += f"Başlık: {review.get('title', 'Başlık yok')}\n"
                txt_content += f"Yazar: {review.get('author', 'Yazar yok')}\n"
                txt_content += f"Tarih: {review.get('date', 'Tarih yok')}\n"
                txt_content += f"İçerik: {review.get('content', 'İçerik yok')}\n\n"
            
            st.download_button(
                label="📄 TXT İndir (Örnek)",
                data=txt_content,
                file_name=f"rss_reviews_sample_{st.session_state.app_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
        
        # İlk birkaç review'u göster
        st.subheader("📋 İlk 3 Review Örneği")
        
        for i, review in enumerate(reviews[:3], 1):
            with st.expander(f"{i}. Review (Sayfa {review.get('page', 'N/A')}) - {review.get('rating', 'N/A')} ⭐"):
                st.write(f"**Başlık:** {review.get('title', 'Başlık yok')}")
                st.write(f"**Yazar:** {review.get('author', 'Yazar yok')}")
                st.write(f"**Tarih:** {review.get('date', 'Tarih yok')}")
                st.write(f"**Versiyon:** {review.get('version', 'Versiyon yok')}")
                st.write(f"**İçerik:** {review.get('content', 'İçerik yok')}")

# Koordinatör için ana fonksiyon - İyileştirilmiş
def scrape_app_store_reviews(app_id: str, max_pages: int = 30, country: str = 'tr',
                           start_date: Optional[datetime] = None, end_date: Optional[datetime] = None,
                           max_reviews: Optional[int] = None):
    """Ana koordinatör tarafından çağrılacak fonksiyon - Sadece gerçek RSS API"""
    try:
        # MAX_REVIEWS LİMİT KONTROLÜ
        if max_reviews:
            # Sayfa başına ~15 yorum varsayımı
            estimated_pages = min(max_pages, math.ceil(max_reviews / 15) + 5)  # +5 güvenlik marjı
            max_pages = estimated_pages
        
        # RSS API çağrısı
        scraper = SafeRSSAppStoreScraper()
        
        # Tarih string'lerini hazırla
        start_date_str = start_date.strftime('%Y-%m-%d') if start_date else None
        end_date_str = end_date.strftime('%Y-%m-%d') if end_date else None
        
        reviews = scraper.safe_rss_scraper(
            app_id=int(app_id),
            country=country,
            max_pages=max_pages,
            delay_range=(2, 4),
            start_date_filter=start_date_str,
            end_date_filter=end_date_str,
            max_reviews=max_reviews
        )
        
        if reviews and len(reviews) > 0:
            try:
                import streamlit as st
                st.success(f"✅ App Store RSS: {len(reviews)} gerçek yorum alındı")
            except:
                pass
            return reviews
        else:
            # Mock veri yok - sadece boş liste döndür
            try:
                import streamlit as st
                st.warning(f"⚠️ App Store RSS API'dan veri alınamadı (App ID: {app_id})")
            except:
                pass
            return []
        
    except Exception as e:
        try:
            import streamlit as st
            st.error(f"❌ App Store RSS scraping hatası: {e}")
        except:
            pass
        return []

if __name__ == "__main__":
    main()