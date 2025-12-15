import streamlit as st
import pandas as pd
import re
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import altair as alt
from collections import Counter
import seaborn as sns
from konlpy.tag import Okt

st.set_page_config(
    page_title="K팝 데몬 헌터스 팬덤 형성 요인 분석",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get help': "https://docs.streamlit.io",
        'Report a bug': "https://streamlit.io",
        'About': "### 주은강 \n - [Contact](https://www.instagram.com/zoollllk/)"
    }
)

st.title("K팝 데몬 헌터스 팬덤 형성 요인 분석")

# 수집한 데이터 불러오기
@st.cache_data
def load_data():
    return pd.read_csv("data/naver_news.csv", encoding="utf-8-sig")

df = load_data()

# 전처리: 날짜 변환
df["pubDate"] = pd.to_datetime(df["pubDate"])
df["date"] = df["pubDate"].dt.date

# 전처리: 텍스트 합치기
df["title"] = df["title"].astype(str)
df["description"] = df["description"].astype(str)
text = " ".join(df["title"].tolist()) + " " + " ".join(df["description"].tolist())

# HTML 태그 제거
text = re.sub(r"<.*?>", "", text)

# 형태소 분석 (명사 추출) - 캐싱
@st.cache_data
def extract_all_nouns(text):
    okt = Okt()
    return okt.nouns(text)

all_nouns = extract_all_nouns(text)

# 불용어 설정
stopwords = set(STOPWORDS)
stopwords.update(["뉴스", "기자", "단독", "사진", "영상", "보도", "것", "등", "수", "위"])

# 사이드바 옵션
st.sidebar.header("옵션")
max_words = st.sidebar.slider("워드클라우드 단어 개수", 10, 200, 50, 10)
top_n = st.sidebar.slider("Top 키워드 개수", 5, 30, 15, 5)

# 워드클라우드
st.header("1. 워드클라우드")

font_path = "data/malgun.ttf"

wc = WordCloud(
    font_path=font_path,
    background_color="white",
    width=1000,
    height=500,
    max_words=max_words,
    stopwords=stopwords
).generate(" ".join(all_nouns))

fig1, ax1 = plt.subplots(figsize=(12, 6))
ax1.imshow(wc, interpolation="bilinear")
ax1.axis("off")
st.pyplot(fig1)

st.markdown("""
**분석 목적:** 케이팝 데몬 헌터스 관련 기사에서 가장 많이 언급된 키워드를 파악.
""")

st.markdown("""
워드클라우드를 통해 팬덤과 미디어에서 주로 다루는 주제와 관심사를 파악할 수 있습니다.
""")

# 시계열 분석 (Altair)
st.header("2. 일별 기사량 추이")

min_date = df["date"].min()
max_date = df["date"].max()

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("시작일", min_date)
with col2:
    end_date = st.date_input("종료일", max_date)

df_filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

daily_counts = df_filtered.groupby("date").size().reset_index(name="count")
daily_counts["date"] = pd.to_datetime(daily_counts["date"])

chart = alt.Chart(daily_counts).mark_line(point=True).encode(
    x=alt.X("date:T", title="날짜"),
    y=alt.Y("count:Q", title="기사 수"),
    tooltip=["date:T", "count:Q"]
).properties(
    height=400
).interactive()

st.altair_chart(chart, use_container_width=True)

st.markdown("""
**분석 목적:** 시간에 따른 기사량 변화를 통해 언제 버즈가 발생했는지 파악.
""")

st.markdown("""
기사량 피크 시점을 분석하면 팬덤 형성에 영향을 준 핵심 이벤트를 추정할 수 있습니다.
""")

# 3. Top 키워드 (Seaborn)
st.header("3. Top 키워드")

filtered_nouns = [n for n in all_nouns if n not in stopwords and len(n) > 1]
noun_counts = Counter(filtered_nouns).most_common(top_n)

df_top = pd.DataFrame(noun_counts, columns=["키워드", "빈도"])

fig2, ax2 = plt.subplots(figsize=(10, 6))
sns.barplot(data=df_top, x="빈도", y="키워드", palette="Blues_d", ax=ax2)

# 폰트 직접 적용
font_prop = fm.FontProperties(fname="data/malgun.ttf")
ax2.set_title(f"Top {top_n} 키워드", fontproperties=font_prop)
ax2.set_xlabel("빈도", fontproperties=font_prop)
ax2.set_ylabel("키워드", fontproperties=font_prop)
for label in ax2.get_yticklabels():
    label.set_fontproperties(font_prop)

st.pyplot(fig2)

# 키워드 트렌드 (Plotly)
st.header("4. 키워드 트렌드")

# 각 기사별 명사 추출
df["nouns"] = df["title"].apply(lambda x: re.findall(r"[가-하]{2,}", str(x))) + \
              df["description"].apply(lambda x: re.findall(r"[가-하]{2,}", str(x)))

# Top 10 키워드 선택 옵션
top_keywords = [word for word, count in noun_counts[:10]]
selected_keywords = st.multiselect("키워드 선택", top_keywords, default=top_keywords[:3])

# 선택된 키워드별 일별 빈도 계산
if selected_keywords:
    trend_data = []
    for date in df["date"].unique():
        daily_df = df[df["date"] == date]
        daily_nouns = sum(daily_df["nouns"].tolist(), [])
        for keyword in selected_keywords:
            count = daily_nouns.count(keyword)
            trend_data.append({"date": date, "keyword": keyword, "count": count})
    
    df_trend = pd.DataFrame(trend_data)
    df_trend["date"] = pd.to_datetime(df_trend["date"])
    
    # Plotly 라인차트
    fig3 = px.line(df_trend, x="date", y="count", color="keyword",
                   title="키워드별 시계열 트렌드", markers=True)
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.write("키워드를 선택해주세요.")



