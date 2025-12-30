import streamlit as st
import parselmouth
import numpy as np
import matplotlib.pyplot as plt
import tempfile
import os

# --- 1. 頁面基本設定 ---
st.set_page_config(page_title="Web-Praat Pro", layout="wide", page_icon="🎙️")

# --- 2. 注入莫蘭迪色系 CSS (Morandi Style) ---
# 這段 HTML/CSS 會覆蓋 Streamlit 的預設樣式
morandi_css = """
<style>
    /* 全局背景：燕麥灰 */
    .stApp {
        background-color: #F2F0EB;
    }
    
    /* 側邊欄背景：暖灰 */
    [data-testid="stSidebar"] {
        background-color: #E6E2DD;
        border-right: 1px solid #D3D3D3;
    }
    
    /* 標題文字顏色：深灰藍 */
    h1, h2, h3, .stMarkdown {
        color: #5F6F7A;
        font-family: 'Helvetica Neue', sans-serif;
    }
    
    /* 按鈕樣式：霧霾綠 */
    .stButton>button {
        background-color: #8DA399;
        color: white;
        border-radius: 8px;
        border: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #7A9188;
        transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.15);
    }
    
    /* 檔案上傳區塊優化 */
    [data-testid="stFileUploader"] {
        background-color: #FFFFFF;
        padding: 15px;
        border-radius: 10px;
        border: 1px dashed #A88F83;
    }
</style>
"""
st.markdown(morandi_css, unsafe_allow_html=True)

# --- 3. 側邊欄：控制中心 ---
with st.sidebar:
    st.title("🎙️ Web-Praat Pro")
    st.markdown("---")
    
    st.subheader("1. 匯入資料")
    uploaded_wav = st.file_uploader("上傳音檔 (WAV)", type=["wav"])
    uploaded_tg = st.file_uploader("上傳標註檔 (TextGrid)", type=["TextGrid"])
    
    st.markdown("---")
    st.subheader("2. 顯示設定")
    show_spectrogram = st.checkbox("顯示語譜圖", value=True)
    show_pitch = st.checkbox("疊加音高 (Pitch)", value=True)
    
    st.markdown("---")
    st.subheader("3. 腳本操作")
    default_script = """
    # 範例：計算總時長
    dur = Get total duration
    appendInfoLine: "Total Duration: " + fixed$(dur, 2) + " s"
    """
    script_code = st.text_area("Praat Script", value=default_script, height=150)
    run_btn = st.button("執行腳本")

# --- 4. 核心邏輯 ---

if uploaded_wav:
    # 處理 WAV 檔案
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_wav:
        tmp_wav.write(uploaded_wav.getvalue())
        wav_path = tmp_wav.name
    
    snd = parselmouth.Sound(wav_path)
    
    # 處理 TextGrid (如果有上傳)
    tg_obj = None
    if uploaded_tg:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".TextGrid") as tmp_tg:
            tmp_tg.write(uploaded_tg.getvalue())
            tg_path = tmp_tg.name
        tg_obj = parselmouth.read(tg_path)

    # --- 5. 繪圖區 (Matplotlib) ---
    st.subheader(f"波形與標註檢視: {uploaded_wav.name}")

    # 根據是否顯示 TextGrid 決定圖表高度
    # 邏輯：波形 + 語譜圖 + 每個 Tier 都要有空間
    n_tiers = len(tg_obj.tiers) if tg_obj else 0
    fig_height = 4 + (2 if show_spectrogram else 0) + (n_tiers * 1)
    
    # 設定畫布背景色以配合網頁 (Morandi Background)
    fig = plt.figure(figsize=(10, fig_height), facecolor='#F2F0EB')
    
    # 定義子圖網格
    # 根據是否有 TextGrid 動態調整佈局
    gs_rows = 2 + (2 if show_spectrogram else 0) + n_tiers
    gs = fig.add_gridspec(gs_rows, 1)
    
    # A. 繪製波形 (Waveform)
    ax_wave = fig.add_subplot(gs[0:2, 0])
    ax_wave.plot(snd.xs(), snd.values.T, color='#6E7C85', linewidth=0.8) # 鐵灰色波形
    ax_wave.set_facecolor('#F2F0EB') # 背景同色
    ax_wave.set_xlim([snd.xmin, snd.xmax])
    ax_wave.set_xticks([]) # 隱藏 x 軸刻度 (只在最下方顯示)
    ax_wave.spines['top'].set_visible(False)
    ax_wave.spines['right'].set_visible(False)
    ax_wave.spines['bottom'].set_visible(False)
    ax_wave.spines['left'].set_visible(False)
    
    # 疊加 Pitch (可選)
    if show_pitch:
        pitch = snd.to_pitch()
        pitch_values = pitch.selected_array['frequency']
        pitch_values[pitch_values==0] = np.nan # 去除無聲段
        ax_pitch = ax_wave.twinx()
        ax_pitch.plot(pitch.xs(), pitch_values, color='#8DA399', linewidth=1.5, linestyle='-') # 霧霾綠音高線
        ax_pitch.set_ylim([0, 500])
        ax_pitch.axis('off')

    current_row = 2

    # B. 繪製語譜圖 (Spectrogram) - 可選
    if show_spectrogram:
        ax_spec = fig.add_subplot(gs[current_row:current_row+2, 0], sharex=ax_wave)
        spectrogram = snd.to_spectrogram()
        sg_db = 10 * np.log10(spectrogram.values)
        # 使用 'Greys' 或 'Gist_earth' 比較符合莫蘭迪冷淡風，這裡選用 Greys
        ax_spec.pcolormesh(spectrogram.x_grid(), spectrogram.y_grid(), sg_db, cmap='Greys', shading='auto')
        ax_spec.set_ylim([0, 5000])
        ax_spec.set_facecolor('#F2F0EB')
        ax_spec.set_ylabel("Freq (Hz)", color='#5F6F7A')
        ax_spec.set_xticks([])
        current_row += 2

    # C. 繪製 TextGrid (如果有)
    if tg_obj:
        # 遍歷每一個 Tier
        for i, tier in enumerate(tg_obj.tiers):
            ax_tg = fig.add_subplot(gs[current_row, 0], sharex=ax_wave)
            ax_tg.set_facecolor('#FFFFFF') # TextGrid 背景設為純白以突顯文字
            
            # 標示 Tier 名稱
            ax_tg.text(snd.xmin - (snd.duration*0.02), 0.5, tier.name, 
                       ha='right', va='center', fontsize=9, color='#5F6F7A', fontweight='bold')

            # 繪製間隔 (Intervals)
            # 判斷是 IntervalTier 還是 PointTier
            if tier.class_name == "IntervalTier": # 修正：Parselmouth 中通常檢查 class_name
                for interval in tier:
                    # 畫邊界線
                    ax_tg.axvline(x=interval.min_time, color='#A88F83', linewidth=1, linestyle='--') # 乾燥玫瑰褐
                    # 畫文字
                    mid_point = (interval.min_time + interval.max_time) / 2
                    ax_tg.text(mid_point, 0.5, interval.text, 
                               ha='center', va='center', fontsize=10, color='#333333')
            
            # 去除雜亂的軸線
            ax_tg.set_yticks([])
            if i < n_tiers - 1:
                ax_tg.set_xticks([])
            else:
                ax_tg.set_xlabel("Time (s)", color='#5F6F7A')
                
            current_row += 1
    
    # 調整圖表間距
    plt.subplots_adjust(hspace=0.05)
    st.pyplot(fig)

    # --- 6. 執行結果區 ---
    if run_btn:
        st.markdown("---")
        st.subheader("📝 分析報告")
        try:
            # 這裡我們將 snd 和 tg_obj 都傳入環境
            # 注意：run_script 主要針對選取的物件。
            # 為了讓 script 能操作 TextGrid，我們需要用 append 方式
            
            # 這裡示範簡單的邏輯：只對 Sound 跑腳本
            # 若要對 TextGrid 跑，需要更複雜的物件管理，目前維持基礎 Sound 操作
            info = parselmouth.praat.run_script(script_code, snd)
            if info:
                st.info(info)
            else:
                st.success("腳本執行完成 (無輸出)")
        except Exception as e:
            st.error(f"Error: {e}")

    # 清理
    os.unlink(wav_path)
    if tg_obj:
        os.unlink(tg_path)

else:
    # 歡迎畫面
    st.info("👋 請從左側匯入 WAV 音檔以開始。")