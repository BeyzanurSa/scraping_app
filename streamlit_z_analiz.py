import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from collections import Counter
from packaging import version
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
import os

# Sayfa konfigürasyonu
# st.set_page_config(
#     page_title="Platform Bazında Versiyon Analizi",
#     page_icon="📊",
#     layout="wide"
# )

# Font ayarları
plt.rcParams['font.family'] = ['Arial', 'Helvetica', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def natural_version_sort(version_list):
    """Versiyonları doğal sıralama ile sıralar (1.0.0 < 1.0.1 < 1.1.0 < 2.0.0)"""
    try:
        sorted_versions = sorted(version_list, key=lambda v: version.parse(str(v)))
        return sorted_versions
    except:
        return sorted(version_list)

def get_version_dates(df, versions):
    """Versiyonlar için en erken tarih bilgisini al"""
    version_dates = {}
    
    for version_name in versions:
        version_data = df[df['version'] == version_name]
        
        if len(version_data) > 0:
            date_column = None
            for col in ['date', 'review_date', 'timestamp', 'created_at', 'published_at']:
                if col in version_data.columns:
                    date_column = col
                    break
            
            if date_column:
                try:
                    dates = pd.to_datetime(version_data[date_column], errors='coerce')
                    valid_dates = dates.dropna()
                    
                    if len(valid_dates) > 0:
                        earliest_date = valid_dates.min()
                        formatted_date = earliest_date.strftime('%m.%y')
                        version_dates[version_name] = formatted_date
                    else:
                        version_dates[version_name] = "N/A"
                except:
                    version_dates[version_name] = "N/A"
            else:
                version_dates[version_name] = "N/A"
        else:
            version_dates[version_name] = "N/A"
    
    return version_dates

def format_version_with_date(version, date_str):
    """Versiyon ve tarihi formatla"""
    if date_str and date_str != "N/A":
        return f"{date_str} - {version}"
    else:
        return version

def scan_csv_files():
    """Mevcut dizindeki CSV dosyalarını tara"""
    csv_files = []
    
    # Mevcut dizindeki CSV dosyalar
    for file in os.listdir('.'):
        if file.endswith('.csv'):
            csv_files.append(file)
    
    return csv_files

@st.cache_data
def load_and_prepare_data(play_file=None, app_file=None, uploaded_play=None, uploaded_app=None):
    """Hem Play Store hem App Store verilerini yükle ve hazırla - CACHED"""
    
    df_play = pd.DataFrame()
    df_app = pd.DataFrame()
    
    # Play Store verisi yükle
    if uploaded_play is not None:
        try:
            df_play = pd.read_csv(uploaded_play)
            df_play['platform'] = 'Play Store'
            
            if 'app_version' in df_play.columns and 'version' not in df_play.columns:
                df_play['version'] = df_play['app_version']
            elif 'version' not in df_play.columns:
                df_play['version'] = 'Unknown'
                
            st.success(f"✅ Play Store dosyası yüklendi: {len(df_play)} kayıt")
        except Exception as e:
            st.error(f"❌ Play Store dosyası okuma hatası: {e}")
    elif play_file:
        try:
            df_play = pd.read_csv(play_file)
            df_play['platform'] = 'Play Store'
            
            if 'app_version' in df_play.columns and 'version' not in df_play.columns:
                df_play['version'] = df_play['app_version']
            elif 'version' not in df_play.columns:
                df_play['version'] = 'Unknown'
                
            st.success(f"✅ Play Store verisi yüklendi: {len(df_play)} kayıt ({os.path.basename(play_file)})")
        except Exception as e:
            st.error(f"❌ Play Store dosyası okuma hatası: {e}")
    
    # App Store verisi yükle
    if uploaded_app is not None:
        try:
            df_app = pd.read_csv(uploaded_app)
            df_app['platform'] = 'App Store'
            
            # Gerekli sütunları kontrol et ve oluştur
            required_columns = ['title', 'content', 'rating', 'version', 'date']
            for col in required_columns:
                if col not in df_app.columns:
                    if col == 'title':
                        df_app['title'] = ''
                    elif col == 'content':
                        df_app['content'] = ''
                    elif col == 'rating':
                        df_app['rating'] = 0
                    elif col == 'version':
                        df_app['version'] = 'Unknown'
                    elif col == 'date':
                        df_app['date'] = ''
            
            st.success(f"✅ App Store dosyası yüklendi: {len(df_app)} kayıt")
        except Exception as e:
            st.error(f"❌ App Store dosyası okuma hatası: {e}")
    elif app_file:
        try:
            df_app = pd.read_csv(app_file)
            df_app['platform'] = 'App Store'
            
            # Gerekli sütunları kontrol et ve oluştur
            required_columns = ['title', 'content', 'rating', 'version', 'date']
            for col in required_columns:
                if col not in df_app.columns:
                    if col == 'title':
                        df_app['title'] = ''
                    elif col == 'content':
                        df_app['content'] = ''
                    elif col == 'rating':
                        df_app['rating'] = 0
                    elif col == 'version':
                        df_app['version'] = 'Unknown'
                    elif col == 'date':
                        df_app['date'] = ''
            
            st.success(f"✅ App Store verisi yüklendi: {len(df_app)} kayıt ({os.path.basename(app_file)})")
        except Exception as e:
            st.error(f"❌ App Store dosyası okuma hatası: {e}")
    
    return df_play, df_app

@st.cache_data
def analyze_platform_data(df_play, df_app, max_versions=15):
    """Platform verilerini analiz et - CACHED"""
    
    platform_data = {}
    
    for platform_name, df in [('Play Store', df_play), ('App Store', df_app)]:
        if len(df) == 0:
            continue
            
        # Veri temizleme
        df_clean = df.dropna(subset=['rating', 'version'])
        df_clean = df_clean[df_clean['version'].astype(str).str.strip() != '']
        df_clean = df_clean[df_clean['version'] != 'Unknown']
        
        if len(df_clean) == 0:
            continue
        
        # Rating'i numeric'e çevir
        df_clean['rating'] = pd.to_numeric(df_clean['rating'], errors='coerce')
        df_clean = df_clean.dropna(subset=['rating'])
        
        # En popüler versiyonları al
        version_counts = df_clean['version'].value_counts().head(max_versions)
        top_versions_unsorted = version_counts.index.tolist()
        
        # Versiyonları doğal sıralama ile sırala
        top_versions = natural_version_sort(top_versions_unsorted)
        
        # Versiyon tarihlerini al
        version_dates = get_version_dates(df_clean, top_versions)
        
        # Tarihli versiyon isimlerini oluştur
        top_versions_with_dates = [format_version_with_date(v, version_dates.get(v)) for v in top_versions]
        
        # Sadece popüler versiyonları filtrele
        df_filtered = df_clean[df_clean['version'].isin(top_versions)]
        
        # Rating dağılımını hesapla
        version_ratings = {}
        for i, version_name in enumerate(top_versions):
            version_data = df_filtered[df_filtered['version'] == version_name]
            rating_dist = version_data['rating'].value_counts().sort_index()
            
            total_reviews = len(version_data)
            rating_percentages = {}
            rating_counts = {}
            for rating in range(1, 6):
                count = rating_dist.get(rating, 0)
                percentage = (count / total_reviews) * 100 if total_reviews > 0 else 0
                rating_percentages[rating] = percentage
                rating_counts[rating] = count
            
            display_version = top_versions_with_dates[i]
            
            version_ratings[display_version] = {
                'percentages': rating_percentages,
                'counts': rating_counts,
                'total': total_reviews,
                'avg_rating': version_data['rating'].mean(),
                'original_version': version_name
            }
        
        platform_data[platform_name] = {
            'version_ratings': version_ratings,
            'top_versions': top_versions_with_dates,
            'original_versions': top_versions,
            'version_dates': version_dates,
            'df': df_filtered
        }
    
    return platform_data

def create_platform_rating_pie_charts(platform_data):
    """Her platform için genel rating dağılımı pie chart'ı"""
    
    platforms = list(platform_data.keys())
    
    if len(platforms) == 0:
        st.warning("❌ Pie chart için veri yok!")
        return
    
    # Her platform için ayrı pie chart
    cols = st.columns(len(platforms))
    
    for idx, platform_name in enumerate(platforms):
        data = platform_data[platform_name]
        df = data['df']
        
        # Rating dağılımını hesapla
        rating_counts = df['rating'].value_counts().sort_index()
        total_reviews = len(df)
        avg_rating = df['rating'].mean()
        
        # YENİ RENK PALETİ - Rating kalitesine göre sabit renkler
        rating_colors = {
            1: '#ff3333',  # 1⭐: Kırmızı
            2: '#ff8800',  # 2⭐: Koyu turuncu
            3: '#ffbb44',  # 3⭐: Hafif turuncu
            4: '#88dd44',  # 4⭐: Açık yeşil
            5: '#00cc44'   # 5⭐: Yeşil
        }
        
        # Pie chart için veri hazırla
        pie_values = []
        pie_labels = []
        pie_colors = []
        
        for rating in rating_counts.index:
            pie_values.append(rating_counts[rating])
            pie_labels.append(f"{rating}⭐")
            pie_colors.append(rating_colors[rating])
        
        # Pie chart oluştur
        fig = go.Figure(data=[go.Pie(
            labels=pie_labels,
            values=pie_values,
            marker=dict(colors=pie_colors),
            hovertemplate='%{label}<br>%{value} yorum<br>%{percent}<extra></extra>',
            textinfo='label+percent'
        )])
        
        fig.update_layout(
            title=f'{platform_name}<br>Rating Dağılımı<br>({total_reviews:,} yorum)<br>📊 Ort: {avg_rating:.2f}⭐',
            showlegend=True,
            height=500,
            font_size=12
        )
        
        with cols[idx]:
            st.plotly_chart(fig, use_container_width=True)

def create_version_rating_analysis(platform_data):
    """Versiyon bazında rating analizi"""
    
    platforms = list(platform_data.keys())
    
    if len(platforms) == 0:
        st.warning("❌ Analiz için veri yok!")
        return
    
    # Platform seçimi
    selected_platform = st.selectbox(
        "📱 Platform seçin:",
        platforms,
        key="version_analysis_platform"
    )
    
    if selected_platform not in platform_data:
        return
    
    data = platform_data[selected_platform]
    version_ratings = data['version_ratings']
    versions = data['top_versions']
    
    st.subheader(f"📊 {selected_platform} - Versiyon Bazında Rating Analizi")
    
    # Stacked bar chart
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Veri hazırlığı
        ratings_data = []
        for version in versions:
            version_data = {
                'Versiyon': version,
                '1⭐': version_ratings[version]['percentages'][1],
                '2⭐': version_ratings[version]['percentages'][2],
                '3⭐': version_ratings[version]['percentages'][3],
                '4⭐': version_ratings[version]['percentages'][4],
                '5⭐': version_ratings[version]['percentages'][5],
                'Toplam': version_ratings[version]['total']
            }
            ratings_data.append(version_data)
        
        df_ratings = pd.DataFrame(ratings_data)
        
        # Stacked bar chart
        fig = go.Figure()
        
        colors = ['#ff4444', '#ff8800', '#ffbb00', '#88dd00', '#00cc44']
        rating_labels = ['1⭐', '2⭐', '3⭐', '4⭐', '5⭐']
        
        for i, rating in enumerate(rating_labels):
            fig.add_trace(go.Bar(
                name=rating,
                x=df_ratings['Versiyon'],
                y=df_ratings[rating],
                marker_color=colors[i],
                hovertemplate=f'{rating}: %{{y:.1f}}%<extra></extra>'
            ))
        
        # Toplam yorum sayısını annotation olarak ekle
        for i, row in df_ratings.iterrows():
            fig.add_annotation(
                x=row['Versiyon'],
                y=105,
                text=f"{row['Toplam']}",
                showarrow=False,
                font=dict(size=10, color="black"),
                bgcolor="white",
                bordercolor="black",
                borderwidth=1
            )
        
        fig.update_layout(
            title=f'{selected_platform} - Rating Dağılımı (%)',
            xaxis_title='Versiyon',
            yaxis_title='Yüzde (%)',
            barmode='stack',
            height=600,
            showlegend=True,
            xaxis={'tickangle': 45}
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.write("**📈 Versiyon İstatistikleri:**")
        
        # En iyi versiyon
        best_version = max(versions, key=lambda v: version_ratings[v]['avg_rating'])
        st.success(f"**🏆 En İyi Versiyon:**\n{best_version}\n{version_ratings[best_version]['avg_rating']:.2f}⭐")
        
        # En kötü versiyon
        worst_version = min(versions, key=lambda v: version_ratings[v]['avg_rating'])
        st.error(f"**👎 En Kötü Versiyon:**\n{worst_version}\n{version_ratings[worst_version]['avg_rating']:.2f}⭐")
        
        # En popüler versiyon
        most_reviewed = max(versions, key=lambda v: version_ratings[v]['total'])
        st.info(f"**💬 En Popüler Versiyon:**\n{most_reviewed}\n{version_ratings[most_reviewed]['total']} yorum")
        
        # Platform özeti
        total_reviews = sum(v['total'] for v in version_ratings.values())
        avg_platform_rating = np.mean([v['avg_rating'] for v in version_ratings.values()])
        
        st.write("**📊 Platform Özeti:**")
        st.write(f"• Toplam Yorum: {total_reviews:,}")
        st.write(f"• Platform Ort: {avg_platform_rating:.2f}⭐")
        st.write(f"• Versiyon Sayısı: {len(versions)}")

def create_rating_trend_analysis(platform_data):
    """Rating trend analizi"""
    
    platforms = list(platform_data.keys())
    
    if len(platforms) == 0:
        return
    
    st.subheader("📈 Platform Bazında Rating Trend Analizi")
    
    # Her platform için trend grafiği
    for platform_name in platforms:
        data = platform_data[platform_name]
        version_ratings = data['version_ratings']
        versions = data['top_versions']
        
        # Veri hazırlığı
        avg_ratings = [version_ratings[v]['avg_rating'] for v in versions]
        total_reviews = [version_ratings[v]['total'] for v in versions]
        
        # Trend grafiği
        fig = go.Figure()
        
        # Ana çizgi
        fig.add_trace(go.Scatter(
            x=list(range(len(versions))),
            y=avg_ratings,
            mode='lines+markers',
            name=f'{platform_name} Rating',
            line=dict(width=4, color='#34a853' if platform_name == 'Play Store' else '#007aff'),
            marker=dict(size=10, color='white', line=dict(width=2, color='black')),
            hovertemplate='%{text}<br>Rating: %{y:.2f}⭐<extra></extra>',
            text=versions
        ))
        
        # Bubble chart (yorum sayısına göre)
        fig.add_trace(go.Scatter(
            x=list(range(len(versions))),
            y=avg_ratings,
            mode='markers',
            name=f'{platform_name} Volume',
            marker=dict(
                size=[max(t/50, 10) for t in total_reviews],
                color='#34a853' if platform_name == 'Play Store' else '#007aff',
                opacity=0.4,
                line=dict(width=2, color='black')
            ),
            hovertemplate='%{text}<br>Rating: %{y:.2f}⭐<br>Yorum: %{customdata}<extra></extra>',
            text=versions,
            customdata=total_reviews
        ))
        
        # Trend çizgisi
        if len(versions) > 2:
            x_numeric = np.array(range(len(versions)))
            z = np.polyfit(x_numeric, avg_ratings, min(2, len(versions)-1))
            p = np.poly1d(z)
            
            fig.add_trace(go.Scatter(
                x=list(range(len(versions))),
                y=p(x_numeric),
                mode='lines',
                name=f'{platform_name} Trend',
                line=dict(width=3, dash='dash', color='gray'),
                hoverinfo='skip'
            ))
        
        fig.update_layout(
            title=f'{platform_name} - Versiyon Rating Trendi',
            xaxis_title='Versiyon',
            yaxis_title='Ortalama Rating',
            yaxis=dict(range=[0, 5.5]),
            height=500,
            showlegend=True,
            xaxis=dict(
                tickmode='array',
                tickvals=list(range(len(versions))),
                ticktext=versions,
                tickangle=45
            )
        )
        
        # Referans çizgileri
        for y_val in [1, 2, 3, 4, 5]:
            fig.add_hline(y=y_val, line_dash="dot", line_color="gray", opacity=0.5)
        
        st.plotly_chart(fig, use_container_width=True)

def create_heatmap_analysis(platform_data):
    """Heatmap analizi"""
    
    platforms = list(platform_data.keys())
    
    if len(platforms) == 0:
        return
    
    st.subheader("🔥 Platform Heatmap Analizi")
    
    # Platform seçimi
    selected_platform = st.selectbox(
        "📱 Heatmap için platform seçin:",
        platforms,
        key="heatmap_platform"
    )
    
    if selected_platform not in platform_data:
        return
    
    data = platform_data[selected_platform]
    version_ratings = data['version_ratings']
    versions = data['top_versions']
    
    # Heatmap verisi hazırlığı
    heatmap_data = []
    annotations = []
    
    for version in versions:
        row_data = []
        row_annotations = []
        for rating in range(1, 6):
            count = version_ratings[version]['counts'].get(rating, 0)
            total = version_ratings[version]['total']
            percentage = version_ratings[version]['percentages'][rating]
            
            row_data.append(percentage)
            row_annotations.append(f"{count}/{total}")
        
        heatmap_data.append(row_data)
        annotations.append(row_annotations)
    
    # Plotly heatmap
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_data,
        x=['1⭐', '2⭐', '3⭐', '4⭐', '5⭐'],
        y=versions,
        colorscale='YlOrRd',
        text=annotations,
        texttemplate="%{text}",
        textfont={"size": 10},
        hovertemplate='Versiyon: %{y}<br>Rating: %{x}<br>Yüzde: %{z:.1f}%<br>Oran: %{text}<extra></extra>'
    ))
    
    fig.update_layout(
        title=f'{selected_platform} - Versiyon vs Rating Heatmap (Sayı/Toplam)',
        xaxis_title='Rating',
        yaxis_title='Versiyon',
        height=max(400, len(versions) * 30),
        yaxis=dict(autorange='reversed')
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_platform_comparison_summary(platform_data):
    """Platform karşılaştırma özeti"""
    
    platforms = list(platform_data.keys())
    
    if len(platforms) < 2:
        st.info("Platform karşılaştırması için en az 2 platform verisi gerekli.")
        return
    
    st.subheader("🔄 Platform Karşılaştırma Özeti")
    
    # Platform özet metrikleri
    col1, col2 = st.columns(2)
    
    platform_summary = {}
    
    for platform_name in platforms:
        data = platform_data[platform_name]
        df = data['df']
        
        summary = {
            'total_reviews': len(df),
            'avg_rating': df['rating'].mean(),
            'total_versions': df['version'].nunique(),
            'rating_distribution': df['rating'].value_counts().sort_index().to_dict()
        }
        
        platform_summary[platform_name] = summary
    
    # Karşılaştırma tablosu
    comparison_data = []
    for platform_name in platforms:
        data = platform_summary[platform_name]
        
        row = {
            'Platform': platform_name,
            'Toplam Yorum': f"{data['total_reviews']:,}",
            'Ortalama Rating': f"{data['avg_rating']:.2f}⭐",
            'Versiyon Sayısı': data['total_versions'],
            '5⭐ Oranı': f"{(data['rating_distribution'].get(5, 0) / data['total_reviews'] * 100):.1f}%",
            '1⭐ Oranı': f"{(data['rating_distribution'].get(1, 0) / data['total_reviews'] * 100):.1f}%"
        }
        comparison_data.append(row)
    
    comparison_df = pd.DataFrame(comparison_data)
    st.dataframe(comparison_df, use_container_width=True)
    
    # En iyi platform
    best_platform = max(platforms, key=lambda p: platform_summary[p]['avg_rating'])
    best_rating = platform_summary[best_platform]['avg_rating']
    
    st.success(f"🏆 **En İyi Performans:** {best_platform} ({best_rating:.2f}⭐)")
    
    # Platform farkı analizi
    if len(platforms) == 2:
        platform1, platform2 = platforms
        rating1 = platform_summary[platform1]['avg_rating']
        rating2 = platform_summary[platform2]['avg_rating']
        diff = abs(rating1 - rating2)
        
        if diff < 0.1:
            comparison = "📊 Platformlar neredeyse eşit performans gösteriyor"
        elif diff < 0.3:
            comparison = f"📊 {best_platform} hafif avantajlı (+{diff:.2f})"
        elif diff < 0.5:
            comparison = f"📊 {best_platform} belirgin avantajlı (+{diff:.2f})"
        else:
            comparison = f"📊 {best_platform} çok daha iyi performans (+{diff:.2f})"
        
        st.info(f"**🔍 Platform Karşılaştırma:** {comparison}")

# Ana Streamlit uygulaması
def main():
    st.set_page_config(
        page_title="Platform Bazında Versiyon Analizi",
        page_icon="📊",
        layout="wide"
    )
    st.title("📊 Platform Bazında Versiyon Analizi")
    st.markdown("---")
    
    # SESSION STATE İÇİN ANALİZ SONUÇLARINI SAKLA
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None
    
    if 'analysis_params' not in st.session_state:
        st.session_state.analysis_params = None
    
    # Sidebar - Dosya seçimi ve ayarlar
    with st.sidebar:
        st.header("📁 Dosya Yönetimi")
        
        # Dosya seçim yöntemi
        file_source = st.radio(
            "📂 Veri kaynağını seçin:",
            ["📂 Mevcut dosyalardan seç", "📤 Dosya yükle"],
            help="Mevcut dosyalardan seçin veya yeni dosya yükleyin"
        )
        
        play_file = None
        app_file = None
        uploaded_play = None
        uploaded_app = None
        
        if file_source == "📂 Mevcut dosyalardan seç":
            # Mevcut CSV dosyalarını tara
            csv_files = scan_csv_files()
            
            if csv_files:
                # Play Store dosyası
                play_files = [f for f in csv_files if 'play' in f.lower() or 'version_fixed' in f.lower()]
                if play_files:
                    play_file = st.selectbox(
                        "📱 Play Store dosyası:",
                        [None] + play_files,
                        help="Play Store verisi içeren CSV dosyası"
                    )
                else:
                    st.info("Play Store dosyası bulunamadı")
                
                # App Store dosyası
                app_files = [f for f in csv_files if ('app' in f.lower() or 'edited_app_store' in f.lower()) and f not in play_files]
                if app_files:
                    app_file = st.selectbox(
                        "🍎 App Store dosyası:",
                        [None] + app_files,
                        help="App Store verisi içeren CSV dosyası"
                    )
                else:
                    st.info("App Store dosyası bulunamadı")
            else:
                st.warning("❌ CSV dosyası bulunamadı!")
        
        else:  # Dosya yükleme
            st.subheader("📤 Dosya Yükleme")
            
            uploaded_play = st.file_uploader(
                "📱 Play Store CSV dosyası:",
                type=['csv'],
                help="rating, version/app_version sütunları gerekli",
                key="play_upload"
            )
            
            uploaded_app = st.file_uploader(
                "🍎 App Store CSV dosyası:",
                type=['csv'],
                help="rating, version sütunları gerekli",
                key="app_upload"
            )
        
        st.markdown("---")
        
        st.header("⚙️ Analiz Ayarları")
        
        # Versiyon sayısı
        max_versions = st.slider("📱 Maksimum versiyon sayısı", 5, 25, 15)
        
        # Analiz seçenekleri - KORELASYON KALDIRILDI
        st.subheader("📊 Görselleştirmeler")
        show_pie_charts = st.checkbox("🥧 Pie Charts", value=True)
        show_version_analysis = st.checkbox("📈 Versiyon Analizi", value=True)
        show_trend_analysis = st.checkbox("📊 Trend Analizi", value=True)
        show_heatmap = st.checkbox("🔥 Heatmap", value=True)
        show_comparison = st.checkbox("🔄 Platform Karşılaştırma", value=True)
        
        st.markdown("---")
        
        # Veri yenileme
        if st.button("🔄 Veriyi Yenile"):
            st.cache_data.clear()
            st.rerun()
        
        # Dosya bilgileri
        st.subheader("📋 Gerekli Formatlar")
        st.info("""
        **📱 Play Store:**
        - `rating` (1-5)
        - `version` veya `app_version`
        - `date` (opsiyonel)
        
        **🍎 App Store:**
        - `rating` (1-5) 
        - `version`
        - `date` (opsiyonel)
        """)
    
    # Ana içerik
    try:
        # Veriyi yükle
        with st.spinner("📊 Veriler yükleniyor..."):
            df_play, df_app = load_and_prepare_data(
                play_file=play_file, 
                app_file=app_file,
                uploaded_play=uploaded_play,
                uploaded_app=uploaded_app
            )
        
        if len(df_play) == 0 and len(df_app) == 0:
            # SESSION STATE TEMİZLE
            st.session_state.analysis_results = None
            st.session_state.analysis_params = None
            
            st.warning("⚠️ Henüz veri yüklenmedi!")
            st.info("""
            ### 📋 Platform Bazında Versiyon Analizi
            
            Bu araç **Play Store** ve **App Store** verilerini karşılaştırmalı olarak analiz eder.
            
            #### 🎯 Özellikler:
            - **🥧 Platform Rating Dağılımı** - Her platform için genel performans
            - **📈 Versiyon Bazında Analiz** - Hangi versiyon ne kadar başarılı?
            - **📊 Trend Analizi** - Versiyonlar arası rating eğilimleri  
            - **🔥 Heatmap** - Versiyon vs Rating görselleştirmesi
            - **🔄 Platform Karşılaştırması** - Play Store vs App Store
            
            #### 📂 Desteklenen Dosya Formatları:
            - **Play Store:** `play`, `version_fixed` içeren CSV dosyaları
            - **App Store:** `app`, `edited_app_store` içeren CSV dosyaları
            
            #### 📊 Gerekli Sütunlar:
            - `rating`: 1-5 yıldız puanı
            - `version` veya `app_version`: Uygulama versiyonu
            - `date`: Tarih bilgisi (opsiyonel, trend analizi için)
            
            **📁 Dosya seç/yükle butonlarını kullanarak başlayın!**
            """)
            return
        
        # ANALİZ PARAMETRELERINI KONTROL ET
        current_params = {
            'play_len': len(df_play),
            'app_len': len(df_app),
            'max_versions': max_versions,
            'play_file': play_file,
            'app_file': app_file
        }
        
        # EĞER PARAMETRELER DEĞİŞMİŞSE VEYA İLK KEZ ÇALIŞIYORSA ANALİZ ET
        if (st.session_state.analysis_params != current_params or 
            st.session_state.analysis_results is None):
            
            # Platform verilerini analiz et
            with st.spinner("🔍 Platform verileri analiz ediliyor..."):
                platform_data = analyze_platform_data(df_play, df_app, max_versions)
                
                # Sonuçları session state'e kaydet
                st.session_state.analysis_results = platform_data
                st.session_state.analysis_params = current_params
                
                st.success("✅ Yeni analiz tamamlandı!")
        else:
            # Mevcut sonuçları kullan
            platform_data = st.session_state.analysis_results
            st.info("📊 Mevcut analiz sonuçları kullanılıyor...")
        
        if len(platform_data) == 0:
            st.error("❌ Analiz edilebilir veri bulunamadı!")
            st.info("Veri dosyalarında `rating` ve `version` sütunlarının olduğundan emin olun.")
            return
        
        # Analiz özeti
        st.success(f"✅ Analiz tamamlandı! {len(platform_data)} platform verisi işlendi.")
        
        # Metrikler
        total_reviews = sum(len(data['df']) for data in platform_data.values())
        total_versions = sum(len(data['top_versions']) for data in platform_data.values())
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Toplam Yorum", f"{total_reviews:,}")
        with col2:
            st.metric("Analiz Edilen Versiyon", total_versions)
        with col3:
            st.metric("Platform Sayısı", len(platform_data))
        
        st.markdown("---")
        
        # Görselleştirmeler - KORELASYON KALDIRILDI
        if show_pie_charts:
            st.header("🥧 Genel Rating Dağılımı")
            create_platform_rating_pie_charts(platform_data)
            st.markdown("---")
        
        if show_version_analysis:
            st.header("📈 Versiyon Bazında Rating Analizi")
            create_version_rating_analysis(platform_data)
            st.markdown("---")
        
        if show_trend_analysis:
            st.header("📊 Rating Trend Analizi")
            create_rating_trend_analysis(platform_data)
            st.markdown("---")
        
        if show_heatmap:
            st.header("🔥 Heatmap Analizi")
            create_heatmap_analysis(platform_data)
            st.markdown("---")
        
        if show_comparison:
            st.header("🔄 Platform Karşılaştırması")
            create_platform_comparison_summary(platform_data)
        
        # Analiz raporu indirme - HAZIR RAPOR KULLAN
        st.markdown("---")
        st.subheader("📥 Analiz Raporu")
        
        # RAPORU SESSION STATE'DE SAKLA
        if 'analysis_report' not in st.session_state or st.session_state.analysis_params != current_params:
            # Rapor oluştur
            report_content = f"""
PLATFORM BAZINDA VERSİYON ANALİZİ RAPORU
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}

📊 GENEL BİLGİLER:
- Analiz edilen platform: {len(platform_data)}
- Toplam yorum: {total_reviews:,}
- Toplam versiyon: {total_versions}

"""
            
            for platform_name in platform_data.keys():
                data = platform_data[platform_name]
                df = data['df']
                
                report_content += f"""
📱 {platform_name.upper()}:
- Toplam yorum: {len(df):,}
- Ortalama rating: {df['rating'].mean():.2f}⭐
- Versiyon sayısı: {len(data['top_versions'])}
- En iyi versiyon: {max(data['top_versions'], key=lambda v: data['version_ratings'][v]['avg_rating'])}
"""
            
            st.session_state.analysis_report = report_content
        
        # HAZIR RAPORU İNDİR
        st.download_button(
            label="📋 Analiz Raporu İndir",
            data=st.session_state.analysis_report,
            file_name=f"platform_analiz_raporu_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            key="download_analysis_report"
        )
        
        # CACHE TEMİZLEME BUTONU
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        
        with col2:
            if st.button("🗑️ Cache Temizle", help="Analiz sonuçlarını sıfırla"):
                st.session_state.analysis_results = None
                st.session_state.analysis_params = None
                st.session_state.analysis_report = None
                st.cache_data.clear()
                st.success("✅ Cache temizlendi!")
                st.rerun()
        
    except Exception as e:
        st.error(f"❌ Analiz sırasında hata oluştu: {str(e)}")
        st.exception(e)

# Footer'u buraya taşıyoruz
st.markdown("---")
st.markdown("*📊 Platform Bazında Versiyon Analizi - Interactive Dashboard*")

if __name__ == "__main__":
    main()