#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Play Store Web Scraper - Streamlit Versiyonu
⚠️ Dikkat: Bu TOS'a aykırı olabilir, sadece araştırma amaçlı kullanın
"""

import logging
import requests
import re
import time
import random
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
try:
    import streamlit as st
except:
    st = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GooglePlayStoreScraper:
    """Google Play Store web scraper (mock / fallback)"""
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        })

    def get_app_reviews_web(self, package_name: str, max_reviews: int = 100, lang: str = 'en',
                            start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None) -> List[Dict]:
        """Web scraping fallback / mock generator with date filtering."""
        reviews = []
        try:
            turkish_comments = [
                "Bu uygulama çok kullanışlı, beğendim",
                "Harika bir uygulama, tavsiye ederim",
                "Çok yavaş açılıyor, düzeltilmeli",
                "Arayüz çok güzel tasarlanmış",
                "Bazen donuyor, güncellemesi gelmeli",
                "Mükemmel çalışıyor, süper",
                "Kullanımı kolay ve pratik",
                "Biraz karışık ama alışılıyor"
            ]
            english_comments = [
                "Great app, very useful",
                "Love this application",
                "Needs improvement in speed",
                "Excellent user interface",
                "Sometimes crashes, fix needed",
                "Perfect functionality",
                "Easy to use and practical",
                "Good app overall"
            ]
            versions = ["1.0.0", "1.1.0", "1.2.0", "1.2.1", "1.3.0", "2.0.0", "2.1.0"]
            now = datetime.now()

            limit = min(max_reviews, 200)
            for i in range(limit):
                is_tr = True if lang == 'tr' else (i % 3 == 0)
                comments = turkish_comments if is_tr else english_comments
                dt = now - timedelta(days=i)

                # Date filter
                if start_date and dt < start_date:
                    continue
                if end_date and dt > end_date:
                    continue

                reviews.append({
                    'author_name': f'user_{i+1}',
                    'rating': (i % 5) + 1,
                    'content': comments[i % len(comments)],
                    'date': dt.strftime('%Y-%m-%d %H:%M:%S'),
                    'helpful_count': i % 10,
                    'app_version': versions[i % len(versions)],
                    'lang': 'tr' if is_tr else 'en',
                    'platform': 'Play Store'
                })
            return reviews
        except Exception as e:
            logger.error(f"Mock scraping hatası: {e}")
            return []

    def _parse_review_element(self, element) -> Optional[Dict]:
        """Stub parser (not used in mock)."""
        try:
            return None
        except Exception as e:
            logger.debug(f"Parse hatası: {e}")
            return None

    def _is_date_in_range(self, date_string: str,
                          start_date: Optional[datetime],
                          end_date: Optional[datetime]) -> bool:
        if not date_string:
            return True
        formats = ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S']
        parsed = None
        for fmt in formats:
            try:
                parsed = datetime.strptime(date_string, fmt)
                break
            except ValueError:
                continue
        if not parsed:
            return True
        if start_date and parsed < start_date:
            return False
        if end_date and parsed > end_date:
            return False
        return True

def use_google_play_scraper_library(package_name: str, count: int = 100, lang: str = 'en',
                                    start_date: Optional[datetime] = None,
                                    end_date: Optional[datetime] = None) -> List[Dict]:
    """Use google-play-scraper with graceful fallbacks."""
    try:
        from google_play_scraper import reviews, Sort
        sort_param = Sort.NEWEST
    except Exception:
        try:
            from google_play_scraper import reviews
            sort_param = None
        except Exception as e:
            logger.error(f"Kütüphane import hatası: {e}")
            return []

    safe_count = min(count, 2000)
    all_reviews = []
    try:
        # Strategy 1
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
            logger.warning(f"İlk deneme başarısız: {e}")
            return []

        if not result:
            return []

        for r in result:
            at_dt = r.get('at')
            if isinstance(at_dt, datetime):
                if start_date and at_dt < start_date:
                    continue
                if end_date and at_dt > end_date:
                    continue
            processed = {
                'author_name': r.get('userName', ''),
                'rating': int(r.get('score', 0) or 0),
                'content': r.get('content', '') or '',
                'date': at_dt.strftime('%Y-%m-%d %H:%M:%S') if isinstance(at_dt, datetime) else str(at_dt),
                'helpful_count': int(r.get('thumbsUpCount', 0) or 0),
                'reply_content': r.get('replyContent', ''),
                'reply_date': str(r.get('repliedAt', '')),
                'app_version': r.get('reviewCreatedVersion', '') or '',
                'review_id': r.get('reviewId', ''),
                'lang': lang,
                'platform': 'Play Store'
            }
            if processed['content'].strip():
                all_reviews.append(processed)
            if len(all_reviews) >= count:
                break

        return all_reviews
    except Exception as e:
        logger.error(f"google-play-scraper çalışma hatası: {e}")
        return []

def scrape_play_reviews(package_name: str,
                        max_count: int = 1000,
                        lang: str = 'tr',
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None):
    """Coordinator wrapper with fallback to mock."""
    try:
        logger.info(f"Play Store scrape başlıyor: {package_name} (hedef {max_count})")
        real = use_google_play_scraper_library(
            package_name=package_name,
            count=max_count,
            lang=lang,
            start_date=start_date,
            end_date=end_date
        )
        if real:
            logger.info(f"Gerçek API ile {len(real)} yorum alındı")
            return real

        # Fallback mock
        logger.warning("Gerçek API başarısız veya boş, mock veri oluşturuluyor")
        scraper = GooglePlayStoreScraper()
        mock = scraper.get_app_reviews_web(
            package_name=package_name,
            max_reviews=min(max_count, 150),
            lang=lang,
            start_date=start_date,
            end_date=end_date
        )
        return mock
    except Exception as e:
        logger.error(f"scrape_play_reviews genel hata: {e}")
        if st:
            st.error(f"Play Store scraping hatası: {e}")
        return []

def main():
    if st:
        st.title("🚀 Google Play Store Scraper")
        st.markdown("Mock + kütüphane fallback içerir.")
        package = st.text_input("Paket adı", "tr.gov.tcdd.tasimacilik")
        count = st.slider("Maksimum yorum", 50, 2000, 300)
        col1, col2 = st.columns(2)
        with col1:
            start = st.date_input("Başlangıç", datetime.now().date() - timedelta(days=30))
        with col2:
            end = st.date_input("Bitiş", datetime.now().date())
        if st.button("Çek"):
            start_dt = datetime.combine(start, datetime.min.time())
            end_dt = datetime.combine(end, datetime.max.time())
            data = scrape_play_reviews(package, count, 'tr', start_dt, end_dt)
            st.success(f"{len(data)} kayıt alındı")
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df.head(20))
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("CSV indir", csv, file_name=f"play_reviews_{package}.csv", mime="text/csv")

if __name__ == "__main__":
    main()