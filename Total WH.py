import streamlit as st
import pandas as pd
import os

# --- 1. 语言配置字典 ---
LANG_DICT = {
    "CN": {
        "title": "MDC 仓库监控 (手机优化版)",
        "total_usage": "利用率",
        "used": "已用",
        "total_avail": "总可用",
        "ctrl_panel": "⚙️ 控制面板",
        "wh_sel": "选择库房",
        "aisle_sel": "选择货道 (减少卡顿)",
        "stats_title": "统计",
        "bin_total": "可用总数",
        "bin_used": "已占用",
        "bin_free": "空闲",
        "legend_empty": "空位",
        "legend_used": "占用",
        "legend_disabled": "不可用",
        "legend_beam": "横梁",
        "legend_pillar": "立柱",
        "aisle_label": "货道",
        "data_error": "数据加载失败"
    },
    "PT": {
        "title": "MDC Monitor (Versão Mobile)",
        "total_usage": "Ocupação",
        "used": "Usado",
        "total_avail": "Total",
        "ctrl_panel": "⚙️ Painel",
        "wh_sel": "Selecionar Armazém",
        "aisle_sel": "Selecionar Corredor",
        "stats_title": "Estatísticas",
        "bin_total": "Total Locais",
        "bin_used": "Ocupados",
        "bin_free": "Livres",
        "legend_empty": "Vazio",
        "legend_used": "Ocupado",
        "legend_disabled": "Bloqueado",
        "legend_beam": "Viga",
        "legend_pillar": "Pilar",
        "aisle_label": "Corredor",
        "data_error": "Erro de dados"
    }
}

# --- 2. 页面配置与 UI 样式 (已去掉阴影和渐变以提升性能) ---
st.set_page_config(page_title="MDC Mobile", layout="wide")

st.markdown("""
    <style>
    .total-card {
        background-color: #1e3c72;
        padding: 12px; border-radius: 8px; color: white; text-align: center;
        margin-bottom: 15px;
    }
    .wh-stat-card {
        background: white; padding: 8px; border-radius: 5px;
        border: 1px solid #ddd; text-align: center;
        margin-bottom: 5px;
    }
    .wh-stat-title { font-weight: bold; color: #1e3c72; font-size: 14px; }
    .wh-stat-val { color: #2ecc71; font-weight: bold; font-size: 16px; }
    
    .legend-container {
        display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;
        background: #fdfdfd; padding: 8px; border-radius: 5px;
        border: 1px solid #eee; margin-bottom: 15px; font-size: 11px;
    }
    .legend-item { display: flex; align-items: center; gap: 4px; }
    
    .shelf-container {
        display: flex; flex-wrap: nowrap; justify-content: flex-start;
        gap: 0px; padding: 10px; overflow-x: auto; background: white;
        border: 1px solid #eee; margin-bottom: 20px;
    }
    .bay-unit { display: flex; flex-direction: row; align-items: flex-start; }
    .bin-column { display: flex; flex-direction: column; align-items: center; width: 38px; flex-shrink: 0; }
    
    .bin-box {
        width: 32px; height: 28px;
        display: flex; align-items: center; justify-content: center;
        border-radius: 1px; font-size: 9px; font-weight: bold;
        border: 1px solid #f0f0f0; background-color: white;
    }
    
    .orange-beam-row { width: 100%; height: 3px; background-color: #ff9800; margin: 1px 0; }
    
    .pillar-tech-blue {
        width: 0; height: 180px; border-left: 3px dotted #3498db; 
        margin: 0 8px; opacity: 0.8; align-self: flex-start; margin-top: 3px;
    }

    .status-used { background-color: #3498db !important; color: white; border: none; }
    .status-empty { background-color: #2ecc71 !important; color: white; border: none; }
    .status-disabled { background-color: #95a5a6 !important; color: white; border: none; }
    
    .aisle-title { 
        background: #eee; padding: 4px 10px; border-radius: 4px; 
        font-weight: bold; color: #333; font-size: 14px; margin-bottom: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 数据加载 ---
@st.cache_data(ttl=60)
def load_data():
    if not os.path.exists("SGF.csv"): return None, None
    try:
        raw_df = pd.read_csv("SGF.csv", low_memory=False)
        df = raw_df.iloc[:, [0, 6, 9, 11, 12, 13, 14]].copy()
        df.columns = ['SKU', 'Loc', 'Qty', 'L', 'W', 'H', 'Status']
        df['Loc'] = df['Loc'].astype(str).str.strip()
        df['Status'] = df['Status'].astype(str).str.strip()
        df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce').fillna(0)
        for c in ['L','W','H']: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        df['Vol'] = (df['L'] * df['W'] * df['H']) / 1000000
        
        m_mask = (~df['Loc'].str.contains('-', na=False)) & (df['Loc'].str.startswith(('A','B','C','D','E'))) & (df['L']>0)
        master = df[m_mask].drop_duplicates('Loc')
        
        l_map, stats = {}, {wh: {'t_v':0.0, 'u_v':0.0, 'total_bins':0, 'used_bins':0} for wh in 'ABCDE'}
        for _, r in master.iterrows():
            wh = r['Loc'][0].upper()
            l_map[r['Loc']] = {'Items':[], 'Status':r['Status'], 'Vol':r['Vol'], 'WH':wh, 'Aisle':r['Loc'][0:3], 'Col':r['Loc'][3:5], 'Lvl':r['Loc'][5:7]}
            if r['Status'] == "可用": 
                stats[wh]['t_v'] += r['Vol']
                stats[wh]['total_bins'] += 1
        
        inv = df[df['Qty'] > 0]
        for _, r in inv.iterrows():
            if r['Loc'] in l_map: l_map[r['Loc']]['Items'].append(f"{r['SKU']}:{int(r['Qty'])}")
        
        for k, v in l_map.items():
            if len(v['Items']) > 0 and v['Status'] == "可用": 
                stats[v['WH']]['u_v'] += v['Vol']; stats[v['WH']]['used_bins'] += 1
        return l_map, stats
    except: return None, None

l_map, wh_stats = load_data()

# --- 4. 界面渲染 ---
if l_map:
    # 语言切换
    lang_choice = st.sidebar.radio("Língua / 语言", ["中文", "Português"])
    L = LANG_DICT["CN"] if lang_choice == "中文" else LANG_DICT["PT"]
    
    st.markdown(f'<h3 style="text-align:center; color:#1e3c72; margin:0;">{L["title"]}</h3>', unsafe_allow_html=True)
    
    # 顶部汇总
    t_all = sum(s['t_v'] for s in wh_stats.values())
    u_all = sum(s['u_v'] for s in wh_stats.values())
    r_all = (u_all/t_all*100) if t_all>0 else 0
    st.markdown(f'<div class="total-card">{L["total_usage"]}: {r_all:.1f}% ({u_all:.1f}/{t_all:.1f} m³)</div>', unsafe_allow_html=True)

    # 库房与货道选择 (关键优化：分货道显示)
    wh_sel = st.sidebar.selectbox(L["wh_sel"], ['A','B','C','D','E'])
    aisle_list = sorted(list(set(v['Aisle'] for v in l_map.values() if v['WH']==wh_sel)))
    a_sel = st.sidebar.selectbox(L["aisle_sel"], aisle_list)
    
    # 统计信息
    curr = wh_stats[wh_sel]
    st.sidebar.divider()
    st.sidebar.markdown(f"**{wh_sel} {L['stats_title']}**")
    st.sidebar.write(f"{L['bin_total']}: {curr['total_bins']}")
    st.sidebar.write(f"{L['bin_used']}: {curr['used_bins']}")
    st.sidebar.write(f"{L['bin_free']}: {curr['total_bins'] - curr['used_bins']}")

    # 图例
    st.markdown(f"""
        <div class="legend-container">
            <div class="legend-item"><div class="bin-box status-empty"></div> {L['legend_empty']}</div>
            <div class="legend-item"><div class="bin-box status-used"></div> {L['legend_used']}</div>
            <div class="legend-item" style="color:#ff9800; font-weight:bold;">━ {L['legend_beam']}</div>
            <div class="legend-item" style="color:#3498db; font-weight:bold;">⫶ {L['legend_pillar']}</div>
        </div>
    """, unsafe_allow_html=True)

    # 渲染单条货道
    levels = ["50","40","30","20","10","00"] if wh_sel=='A' else ["40","30","20","10","00"]
    split = 3 if wh_sel=='A' else 2
    
    st.markdown(f'<div class="aisle-title">📍 {L["aisle_label"]}: {a_sel}</div>', unsafe_allow_html=True)
    all_cols = sorted(list(set(v['Col'] for v in l_map.values() if v['Aisle']==a_sel)), reverse=True)
    
    h_str = '<div class="shelf-container"><div class="pillar-tech-blue"></div>'
    for i in range(0, len(all_cols), split):
        bay_cols = all_cols[i : i + split]
        h_str += '<div class="bay-unit">'
        col_htmls = ["" for _ in bay_cols]
        for l_idx, lvl in enumerate(levels):
            for c_idx, cid in enumerate(bay_cols):
                f_id = f"{a_sel}{cid}{lvl}"
                d = l_map.get(f_id)
                cls, sym = "status-unknown", lvl
                if d:
                    if len(d['Items']) > 0: cls = "status-used"
                    elif d['Status'] == "可用": cls = "status-empty"
                    elif d['Status'] == "不可用": cls, sym = "status-disabled", "❌"
                col_htmls[c_idx] += f'<div class="bin-box {cls}">{sym}</div>'
            if l_idx < len(levels) - 1:
                for c_idx in range(len(bay_cols)): col_htmls[c_idx] += '<div class="orange-beam-row"></div>'
        for idx, c_html in enumerate(col_htmls):
            h_str += f'<div class="bin-column">{c_html}<div style="font-size:9px;color:#999;">{bay_cols[idx]}</div></div>'
        h_str += '</div><div class="pillar-tech-blue"></div>'
    st.markdown(h_str + '</div>', unsafe_allow_html=True)

else:
    st.error("Error: SGF.csv")