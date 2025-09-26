#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Play Store Scraper - Sadece Gerçek Veri
google-play-scraper kütüphanesini kullanır
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd

try:
    import streamlit as st
except:
    st = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def use_google_play_scraper_library(package_name: str, count: int = 100, lang: str = 'en',
                                    start_date: Optional[datetime] = None,
                                    end_date: Optional[datetime] = None) -> List[Dict]:
    """google-play-scraper kütüphanesini kullanarak gerçek veri çek"""
    try:
        from google_play_scraper import reviews, Sort
        sort_param = Sort.NEWEST
    except Exception:
        try:
            from google_play_scraper import reviews
            sort_param = None
        except Exception as e:
            logger.error(f"google-play-scraper kütüphanesi bulunamadı: {e}")
            if st:
                st.error("❌ google-play-scraper kütüphanesi yüklü değil! Kurulum: `pip install google-play-scraper`")
            return []

    safe_count = min(count, 2000)
    all_reviews = []
    
    try:
        if st:
            st.info(f"📱 Play Store'dan {package_name} için yorumlar çekiliyor...")
        
        # google-play-scraper ile veri çek
        try:
            if sort_param:
                result, token = reviews(
                    package_name,
                    lang=lang,
                    country='tr',
                    sort=sort_param,
                    count=safe_count
                )
            else:
                result, token = reviews(
                    package_name,
                    lang=lang,
                    country='tr',
                    count=safe_count
                )
        except Exception as e:
            logger.error(f"Play Store API çağrısı başarısız: {e}")
            if st:
                st.error(f"❌ Play Store'dan veri çekilemedi: {e}")
            return []

        if not result:
            logger.warning("Play Store API'dan boş sonuç döndü")
            if st:
                st.warning("⚠️ Play Store'dan hiç yorum alınamadı. Paket adını kontrol edin.")
            return []

        # Sonuçları işle ve filtrele
        for r in result:
            at_dt = r.get('at')
            
            # Tarih filtresi uygula
            if isinstance(at_dt, datetime):
                if start_date and at_dt < start_date:
                    continue
                if end_date and at_dt > end_date:
                    continue
            
            processed = {
                'author_name': r.get('userName', '') or 'Anonim',
                'rating': int(r.get('score', 0) or 0),
                'content': r.get('content', '') or '',
                'date': at_dt.strftime('%Y-%m-%d %H:%M:%S') if isinstance(at_dt, datetime) else str(at_dt),
                'helpful_count': int(r.get('thumbsUpCount', 0) or 0),
                'reply_content': r.get('replyContent', '') or '',
                'reply_date': str(r.get('repliedAt', '')) if r.get('repliedAt') else '',
                'app_version': r.get('reviewCreatedVersion', '') or '',
                'review_id': r.get('reviewId', '') or '',
                'lang': lang,
                'platform': 'Play Store'
            }
            
            # Boş içerikli yorumları atla
            if processed['content'].strip():
                all_reviews.append(processed)
                
            # Hedef sayıya ulaştık mı?
            if len(all_reviews) >= count:
                break

        logger.info(f"Play Store'dan {len(all_reviews)} gerçek yorum alındı")
        return all_reviews
        
    except Exception as e:
        logger.error(f"google-play-scraper işleme hatası: {e}")
        if st:
            st.error(f"❌ Veri işleme hatası: {e}")
        return []

def scrape_play_reviews(package_name: str,
                        max_count: int = 1000,
                        lang: str = 'tr',
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None):
    """Ana koordinatör fonksiyonu - Sadece gerçek veri"""
    try:
        logger.info(f"Play Store scraping başlıyor: {package_name} (hedef {max_count})")
        
        # Sadece gerçek API'yi dene
        real_reviews = use_google_play_scraper_library(
            package_name=package_name,
            count=max_count,
            lang=lang,
            start_date=start_date,
            end_date=end_date
        )
        
        if real_reviews:
            logger.info(f"✅ {len(real_reviews)} gerçek yorum alındı")
            if st:
                st.success(f"✅ Play Store: {len(real_reviews)} gerçek yorum alındı")
            return real_reviews
        else:
            logger.warning("Play Store'dan hiç veri alınamadı")
            if st:
                st.warning("⚠️ Play Store'dan veri alınamadı. Tarih aralığını genişletmeyi deneyin.")
            return []
        
    except Exception as e:
        logger.error(f"scrape_play_reviews genel hata: {e}")
        if st:
            st.error(f"❌ Play Store scraping hatası: {e}")
        return []

def main():
    if st:
        st.title("📱 Google Play Store Scraper ")
        st.markdown("google-play-scraper kütüphanesini kullanarak Play Store yorumları çeker")
        
        # Kontrol: Kütüphane yüklü mü?
        try:
            import google_play_scraper
            st.success("✅ google-play-scraper kütüphanesi yüklü")
        except ImportError:
            st.error("❌ google-play-scraper kütüphanesi bulunamadı!")
            st.code("pip install google-play-scraper")
            st.stop()
        
        package = st.text_input("📱 Paket adı", "tr.gov.tcdd.tasimacilik")
        count = st.slider("📊 Maksimum yorum sayısı", 50, 2000, 500)
        
        col1, col2 = st.columns(2)
        with col1:
            start = st.date_input("📅 Başlangıç tarihi", datetime.now().date() - timedelta(days=90))
        with col2:
            end = st.date_input("📅 Bitiş tarihi", datetime.now().date())
        
        if st.button("🚀 Veri Çek", type="primary"):
            if not package.strip():
                st.error("⚠️ Paket adı boş olamaz!")
                return
                
            start_dt = datetime.combine(start, datetime.min.time())
            end_dt = datetime.combine(end, datetime.max.time())
            
            with st.spinner("📱 Play Store'dan gerçek yorumlar çekiliyor..."):
                data = scrape_play_reviews(package, count, 'tr', start_dt, end_dt)
            
            if data:
                st.success(f"✅ {len(data)} yorum alındı!")
                
                # İstatistikler
                df = pd.DataFrame(data)
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("📊 Toplam Yorum", len(df))
                
                with col2:
                    avg_rating = df['rating'].mean()
                    st.metric("⭐ Ortalama Rating", f"{avg_rating:.1f}")
                
                with col3:
                    unique_versions = df['app_version'].nunique()
                    st.metric("📱 Farklı Versiyon", unique_versions)
                
                with col4:
                    helpful_sum = df['helpful_count'].sum()
                    st.metric("👍 Toplam Yararlı", helpful_sum)
                
                # DataFrame önizleme
                st.subheader("📋 Yorumlar Önizleme")
                display_columns = ['author_name', 'rating', 'content', 'date', 'app_version']
                available_columns = [col for col in display_columns if col in df.columns]
                st.dataframe(df[available_columns].head(20), use_container_width=True)
                
                # İndirme
                st.subheader("💾 Veri İndirme")
                csv = df.to_csv(index=False, encoding='utf-8').encode('utf-8')
                st.download_button(
                    "📄 CSV Olarak İndir",
                    csv,
                    file_name=f"play_reviews_{package}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.error("❌ Hiç veri alınamadı. Paket adını ve tarih aralığını kontrol edin.")

if __name__ == "__main__":
    main()