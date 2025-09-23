# 🎯 Yorum Scraping & Analiz Sistemi

Bu proje, **Play Store** ve **App Store** yorumlarını otomatik olarak çekip analiz eden kapsamlı bir Streamlit uygulamasıdır. Verileri toplar, işler, çevirir ve görselleştirir.

## 📋 İçindekiler

- [Özellikler](#özellikler)
- [Kurulum](#kurulum)
- [Kullanım](#kullanım)
- [Modüller](#modüller)
- [API ve Veri Kaynakları](#api-ve-veri-kaynakları)
- [Dosya Yapısı](#dosya-yapısı)
- [Örnekler](#örnekler)
- [Sorun Giderme](#sorun-giderme)

## 🚀 Özellikler

### 📱 Platform Desteği
- **Play Store**: google-play-scraper kullanarak yorum çekme
- **App Store**: RSS API ile yorum toplama
- **Karma Platform**: Her iki platformu aynı anda analiz

### 🔧 Veri İşleme
- **Akıllı Versiyon Düzeltme**: Boş app_version alanlarını otomatik doldurma
- **Çoklu Dil Desteği**: Türkçe olmayan yorumları otomatik çevirme
- **Tarih Filtreleme**: Belirtilen tarih aralığındaki yorumları çekme
- **Veri Standardizasyonu**: Farklı platformlardan gelen verileri birleştirme

### 📊 Analiz ve Görselleştirme
- **Rating Dağılım Grafikleri**: Platform bazında yıldız dağılımı
- **Versiyon Bazında Analiz**: Hangi versiyon ne kadar başarılı?
- **Trend Analizi**: Zaman içindeki rating değişimleri
- **Heatmap Görselleştirme**: Versiyon vs Rating korelasyonu
- **Platform Karşılaştırması**: Play Store vs App Store performansı

### 💾 Çoklu Format Desteği
- **CSV**: Excel uyumlu dosya formatı
- **JSON**: API entegrasyonu için
- **TXT**: İnsan okunabilir rapor formatı

## 🛠 Kurulum

### Gereksinimler

```bash
pip install -r requirements.txt
```

**Ana Bağımlılıklar:**
```
streamlit>=1.32.0
pandas>=2.2.0
requests>=2.31.0
googletrans==4.0.0rc1
packaging>=23.2
plotly>=5.19.0
seaborn>=0.13.2
matplotlib>=3.8.0
numpy>=1.26.0
google-play-scraper>=1.2.7
```

### Hızlı Başlangıç

1. **Projeyi klonlayın:**
```bash
git clone <repository-url>
cd scraping_app
```

2. **Bağımlılıkları yükleyin:**
```bash
pip install -r requirements.txt
```

3. **Ana uygulamayı başlatın:**
```bash
streamlit run streamlit_master_app.py
```

## 📖 Kullanım

### 🎯 Ana Dashboard (Master App)

**En kapsamlı çözüm - Tüm işlemleri tek yerden yapın:**

```bash
streamlit run streamlit_master_app.py
```

**Özellikler:**
- 📱 Play Store + 🍎 App Store yorumları aynı anda çekme
- 🔧 Otomatik versiyon düzeltme
- 🌍 Otomatik çeviri (Türkçe olmayanlar)
- 📊 Canlı analiz ve görselleştirme
- 💾 3 formatta indirme (CSV, JSON, TXT)

**Kullanım Adımları:**
1. Play Store paket adını girin (örn: `tr.gov.tcdd.tasimacilik`)
2. App Store App ID'sini girin (örn: `1360892562`)
3. Tarih aralığını belirleyin
4. İşlem seçeneklerini işaretleyin
5. "🚀 Scraping Başlat" butonuna tıklayın

### 🔧 Özel Modüller

#### 1. Play Store Versiyon Düzenleyici
```bash
streamlit run streamlit_version_fixer.py
```
- Boş `app_version` alanlarını akıllı algoritma ile doldurur
- Kullanıcı hatalarını korur ama etkisiz hale getirir
- Versiyon progression mantığı uygular

#### 2. App Store Veri Seçici
```bash
streamlit run streamlit_app_selector.py
```
- RSS verilerini işler ve formatlar
- ISO tarih formatını basit tarihe çevirir
- Esnek sütun seçimi imkanı

#### 3. Akıllı Çevirmen
```bash
streamlit run translator_streamlit.py
```
- Sadece Türkçe olmayan yorumları çevirir
- Türkçe karakterleri otomatik tespit eder
- Batch işleme ile hızlı çeviri

#### 4. RSS Scraper
```bash
streamlit run rss_scraper_streamlit.py
```
- App Store RSS API ile yorum çekme
- Güvenli rate limiting
- Tarih filtresi desteği

#### 5. Platform Analiz
```bash
streamlit run streamlit_z_analiz.py
```
- Detaylı platform karşılaştırması
- Versiyon bazında trend analizi
- İnteraktif görselleştirmeler

## 📁 Modüller

### 🎯 `streamlit_master_app.py`
**Ana koordinatör uygulama**

```python
# Temel kullanım
python streamlit_master_app.py
```

- Tüm modülleri birleştirir
- End-to-end pipeline sağlar
- Session state ile veri koruması
- Otomatik hata işleme

### 🔧 `streamlit_version_fixer.py`
**Play Store versiyon düzeltici**

**Akıllı Mantık:**
- Versiyonları tarih sırasına göre inceler
- Sayıca büyüyen versiyonları "geçerli" olarak işaretler
- Geriye giden versiyonları kullanıcı hatası olarak korur
- Sadece geçerli versiyonlar boş tarihleri doldurur

**Örnek Çıktı:**
```
🏆 Geçerli Progression: 1.0.0 → 1.1.0 → 2.0.0 → 2.1.0
🔒 Kullanıcı Hataları: 1.5.0 (1.1.0'dan sonra gelmiş)
✅ Dolduruldu: 1,245 boş versiyon
```

### 🌍 `translator_streamlit.py`
**Akıllı çeviri sistemi**

**Türkçe Tespit Yöntemleri:**
1. **Dil Sütunu Kontrolü**: `lang=tr` olanları atla
2. **Otomatik Tespit**: Türkçe karakter analizi (%5+ Türkçe karakter)
3. **Hibrit Yaklaşım**: Her iki yöntemi birleştir

**Çeviri İstatistikleri:**
```
📊 İşlem Sonucu:
🇹🇷 Türkçe Atlanan: 1,234 (%45.2)
🌍 Çevrilen: 1,456 (%53.4)
❌ Hata: 38 (%1.4)
⚡ Verimlilik: %98.6
```

### 📱 `rss_scraper_streamlit.py`
**App Store RSS scraper**

**Güvenlik Özellikleri:**
- Rate limiting (2-5 saniye arası)
- HTTP hata yönetimi (400, 502, 429)
- Otomatik retry mekanizması
- Tarih filtresi optimizasyonu

**Örnek Kullanım:**
```python
reviews = scrape_app_store_reviews(
    app_id="1360892562",
    max_pages=30,
    country='tr',
    start_date=datetime(2024, 12, 5),
    end_date=datetime(2025, 8, 15),
    max_reviews=5000
)
```

### 📊 `streamlit_z_analiz.py`
**Platform analiz motoru**

**Görselleştirmeler:**
- 🥧 **Platform Rating Dağılımı**: Genel performans karşılaştırması
- 📈 **Versiyon Analizi**: Stacked bar chart ile rating dağılımı
- 📊 **Trend Analizi**: Zaman içinde rating değişimi
- 🔥 **Heatmap**: Versiyon vs Rating korelasyonu
- 🔄 **Platform Karşılaştırma**: Detaylı metrik karşılaştırması

### 🍎 `streamlit_app_selector.py`
**App Store veri işleyici**

**Özelleştirilmiş İşlemler:**
- ISO tarih formatını basit tarihe çevirme
- Rating dağılım analizi
- İçerik uzunluğu analizi
- Versiyon popülerlik analizi

### 📱 `play_scraper_streamlit.py`
**Play Store scraper**

**Fallback Mekanizması:**
1. **google-play-scraper** kütüphanesi dene
2. Başarısız olursa **mock data** oluştur
3. Tarih filtresi uygula
4. Standart formata çevir

## 🌐 API ve Veri Kaynakları

### Play Store
- **Kütüphane**: `google-play-scraper`
- **Rate Limit**: Yok (kütüphane tarafından yönetiliyor)
- **Veri Formatı**: JSON
- **Maksimum**: ~2000 yorum/çağrı

### App Store
- **API**: iTunes RSS Customer Reviews
- **Endpoint**: `https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json`
- **Rate Limit**: 2-5 saniye arası bekleme
- **Veri Formatı**: JSON (RSS wrapped)
- **Maksimum**: Sınırsız (sayfa bazında)

### Çeviri API
- **Kütüphane**: `googletrans`
- **Rate Limit**: 0.5 saniye/batch
- **Fallback**: Orijinal metin koruma
- **Batch Size**: 10-20 metin/batch

## 📂 Dosya Yapısı

```
scraping_app/
├── 📱 streamlit_master_app.py       # Ana koordinatör uygulama
├── 🔧 streamlit_version_fixer.py    # Play Store versiyon düzeltici
├── 🌍 translator_streamlit.py       # Akıllı çeviri sistemi
├── 🍎 rss_scraper_streamlit.py      # App Store RSS scraper
├── 📊 streamlit_z_analiz.py         # Platform analiz motoru
├── 🍎 streamlit_app_selector.py     # App Store veri seçici
├── 📱 play_scraper_streamlit.py     # Play Store scraper
├── 📋 requirements.txt              # Python bağımlılıkları
├── 📖 README.md                     # Bu dosya
└── 📁 app_reviews/                  # RSS çıktı klasörü (otomatik)
    ├── rss_reviews_1360892562_*.csv
    └── edited_app_store_*.csv
```

## 💡 Örnekler

### Örnek 1: Temel Scraping

```python
# TCDD Uygulaması için son 3 ayın yorumları
package_name = "tr.gov.tcdd.tasimacilik"
app_id = 1360892562
start_date = datetime(2024, 12, 5)
end_date = datetime(2025, 8, 15)

# Master app ile çek
streamlit run streamlit_master_app.py
```

**Beklenen Sonuç:**
- Play Store: ~1,500 yorum
- App Store: ~800 yorum
- Toplam: ~2,300 yorum işlendi

### Örnek 2: Sadece Çeviri

```python
# Mevcut CSV dosyasını çevir
df = pd.read_csv("play_reviews.csv")
translated_df = translate_reviews(df)

# Türkçe olmayan yorumları çevir
# Türkçe olanları koru
```

### Örnek 3: Analiz Odaklı

```python
# Sadece analiz için veri hazırla
# Versiyon düzeltme + çeviri atla
# Hızlı sonuç al

selected_platforms = ["📱 Play Store", "🍎 App Store"]
processing_options = ["📊 Analiz"]  # Sadece analiz
```

## 🔧 Sorun Giderme

### Yaygın Hatalar

#### 1. **googletrans Hatası**
```bash
❌ googletrans kütüphanesi yüklü değil!
```

**Çözüm:**
```bash
pip install googletrans==4.0.0rc1
# VEYA
pip install googletrans==3.1.0a0
```

#### 2. **google-play-scraper Hatası**
```bash
❌ google-play-scraper import hatası
```

**Çözüm:**
```bash
pip install google-play-scraper
```

#### 3. **RSS API 429 (Rate Limit)**
```bash
⚠️ App Store: 429 Too Many Requests
```

**Çözüm:**
- Delay değerlerini artırın (5-10 saniye)
- max_pages değerini azaltın
- Farklı zamanda deneyin

#### 4. **Boş Veri Sorunu**
```bash
⚠️ Belirtilen tarih aralığında yorum bulunamadı
```

**Çözüm:**
- Tarih aralığını genişletin
- Farklı package_name/app_id deneyin
- Mock data ile test edin

### Debug Modları

#### Verbose Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Session State Temizleme
```python
# Streamlit uygulamasında
if st.button("🗑️ Cache Temizle"):
    st.session_state.clear()
    st.cache_data.clear()
    st.rerun()
```

### Performans Optimizasyonu

#### Batch Sizes
- **Çeviri**: 10-20 metin/batch
- **Versiyon Düzeltme**: 1000 satır/chunk
- **RSS Scraping**: 2-5 sayfa/minute

#### Memory Management
- Büyük dosyalar için chunk processing
- Session state'i düzenli temizleme
- Unused dataframe'leri silme

## 📈 Gelecek Özellikler

### Planlanan İyileştirmeler
- [ ] **Elasticsearch Entegrasyonu**: Büyük veri desteği
- [ ] **Machine Learning**: Sentiment analizi
- [ ] **Real-time Dashboard**: Canlı veri akışı
- [ ] **Multi-threaded Scraping**: Hız optimizasyonu
- [ ] **Database Backend**: PostgreSQL/MongoDB desteği
- [ ] **API Endpoints**: REST API servisi
- [ ] **Docker Support**: Konteyner desteği

### Yeni Platform Desteği
- [ ] **Huawei AppGallery**
- [ ] **Amazon Appstore**
- [ ] **Samsung Galaxy Store**

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/yeni-ozellik`)
3. Commit yapın (`git commit -am 'Yeni özellik eklendi'`)
4. Push yapın (`git push origin feature/yeni-ozellik`)
5. Pull Request oluşturun

## ⚖️ Lisans ve Uyarılar

**⚠️ Önemli Uyarılar:**
- Bu araç sadece **araştırma ve eğitim** amaçlıdır
- Play Store ve App Store **Kullanım Şartları**'na dikkat edin
- **Rate limiting** kurallarına uyun
- **Kişisel veri** gizliliğini koruyun
- **Ticari kullanım** öncesi yasal değerlendirme yapın

## 📞 Destek

- **Issues**: GitHub Issues bölümünü kullanın
- **Dokumentasyon**: Bu README dosyasını güncel tutuyoruz
- **Örnekler**: `examples/` klasöründe ek örnekler

---

**🎯 Yorum Scraping & Analiz Sistemi** - Kapsamlı mobil uygulama analiz çözümü

*Son güncelleme: Eylül 2025*

