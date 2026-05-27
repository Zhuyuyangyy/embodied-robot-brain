"""
Embodied-Robot-Brain Dashboard
==============================
Real-time monitoring dashboard for multi-agent research assistant.
Port: 18713

Usage:
    cd /mnt/d/ZYY Project/embodied-robot-brain/backend
    python dashboard.py
"""

import streamlit as st
import requests
import json
import time
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Page config
st.set_page_config(
    page_title="Embodied Robot Brain - Research Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
API_BASE = "http://localhost:8013"
REFRESH_INTERVAL = 5

# Custom CSS
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: bold; color: #00d4ff; }
    .agent-card { background: linear-gradient(135deg, #0a0a1a 0%, #1a1a3e 100%); padding: 20px; border-radius: 12px; }
    .status-running { color: #00ff88; font-weight: bold; }
    .status-pending { color: #ffaa00; font-weight: bold; }
    .status-completed { color: #00d4ff; font-weight: bold; }
    .status-failed { color: #ff4757; font-weight: bold; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { padding: 10px 20px; }
</style>
""", unsafe_allow_html=True)


def check_api_health():
    """Check if the API is running"""
    try:
        resp = requests.get(f"{API_BASE}/health", timeout=2)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None


def get_sample_research_sessions():
    """Get sample research sessions for demo"""
    return [
        {
            "session_id": "rs_001",
            "user_profile": {"name": "张三", "major": "计算机科学", "skill_level": "intermediate"},
            "research_topic": "大语言模型在医学诊断中的应用",
            "status": "running",
            "created_at": (datetime.now() - timedelta(hours=2)).isoformat(),
            "literature_count": 15,
            "experiment_designs": 3,
            "progress_percent": 45.5,
            "agents": {
                "literature": {"status": "running", "calls": 12},
                "experiment": {"status": "completed", "calls": 8},
                "progress": {"status": "running", "calls": 5}
            }
        },
        {
            "session_id": "rs_002",
            "user_profile": {"name": "李四", "major": "生物医学工程", "skill_level": "beginner"},
            "research_topic": "基于深度学习的医学影像分析",
            "status": "completed",
            "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
            "literature_count": 28,
            "experiment_designs": 5,
            "progress_percent": 100.0,
            "agents": {
                "literature": {"status": "completed", "calls": 25},
                "experiment": {"status": "completed", "calls": 15},
                "progress": {"status": "completed", "calls": 10}
            }
        },
        {
            "session_id": "rs_003",
            "user_profile": {"name": "王五", "major": "药学", "skill_level": "advanced"},
            "research_topic": "AI辅助药物发现",
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "literature_count": 0,
            "experiment_designs": 0,
            "progress_percent": 0.0,
            "agents": {
                "literature": {"status": "pending", "calls": 0},
                "experiment": {"status": "pending", "calls": 0},
                "progress": {"status": "pending", "calls": 0}
            }
        }
    ]


def get_sample_literature_results():
    """Get sample literature search results"""
    return {
        "papers": [
            {"title": "BERT在医学文本分类中的应用", "authors": ["张三", "李四"], "year": 2023, "relevance_score": 0.92, "citations": 156},
            {"title": "Transformer架构的医学诊断系统", "authors": ["王五"], "year": 2024, "relevance_score": 0.88, "citations": 89},
            {"title": "深度学习医学影像分析综述", "authors": ["赵六", "陈七"], "year": 2023, "relevance_score": 0.85, "citations": 234},
        ],
        "web_results": [
            {"title": "ArXiv: Medical AI最新进展", "url": "https://arxiv.org/abs/2401.00001", "year": 2024, "relevance_score": 0.80},
        ],
        "knowledge_graph_nodes": [
            {"id": "node_1", "type": "method", "label": "BERT"},
            {"id": "node_2", "type": "method", "label": "Transformer"},
            {"id": "node_3", "type": "domain", "label": "医学诊断"},
        ]
    }


def get_sample_experiment_design():
    """Get sample experiment design"""
    return {
        "research_question": "如何提高医学影像分类的准确率？",
        "hypothesis": "使用预训练的Transformer模型可以提高准确率10%以上",
        "iterations": [
            {
                "iteration": 1,
                "design_snapshot": {
                    "title": "实验设计：提高医学影像分类准确率",
                    "objectives": ["验证假设的有效性", "对比基线方法"],
                    "procedure": [{"step": 1, "action": "准备数据集"}, {"step": 2, "action": "实现基线"}]
                },
                "reflection_notes": "设计基本合理",
                "score": 0.82
            },
            {
                "iteration": 2,
                "design_snapshot": {
                    "title": "实验设计：提高医学影像分类准确率(v2)",
                    "objectives": ["验证假设的有效性", "对比基线方法", "增加对照实验"],
                    "procedure": [{"step": 1, "action": "准备数据集"}, {"step": 2, "action": "实现基线"}, {"step": 3, "action": "实现Transformer"}]
                },
                "reflection_notes": "已增加对照实验",
                "score": 0.88
            }
        ],
        "final_design": {
            "title": "最终实验设计：医学影像分类准确率提升",
            "methodology": "实验法 + 定量分析 + 对照实验",
            "variables": {"independent": ["模型类型"], "dependent": ["准确率", "F1分数"], "controlled": ["数据集", "硬件"]}
        },
        "reflection_score": 0.85,
        "total_iterations": 3
    }


def render_agent_status(agent_name: str, status: str, calls: int):
    """Render agent status indicator"""
    status_colors = {
        "running": "🟢",
        "completed": "🔵",
        "pending": "🟡",
        "failed": "🔴",
        "idle": "⚪"
    }
    icon = status_colors.get(status.lower(), "⚪")
    return f"{icon} **{agent_name}**: {status} ({calls} calls)"


def render_knowledge_graph_visualization():
    """Render knowledge graph visualization using mermaid-style text"""
    st.markdown("""
    ```mermaid
    graph TD
        A[研究主题] --> B[文献调研]
        A --> C[实验设计]
        A --> D[进度管理]
        B --> E[论文1]
        B --> F[论文2]
        B --> G[论文3]
        E --> H[方法论: BERT]
        F --> I[方法论: Transformer]
        C --> J[假设验证]
        D --> K[双轨管理]
        K --> L[探索轨]
        K --> M[验证轨]
    ```
    """)


def render_research_progress(session):
    """Render research progress visualization"""
    progress = session.get("progress_percent", 0)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.progress(progress / 100, text=f"研究进度: {progress:.1f}%")
    with col2:
        status = session.get("status", "unknown")
        status_colors = {"running": "🟢", "completed": "🔵", "pending": "🟡", "failed": "🔴"}
        st.markdown(f"{status_colors.get(status, '⚪')} {status.upper()}")


def main():
    # Header
    st.markdown('<p class="main-header">🤖 Embodied Robot Brain</p>', unsafe_allow_html=True)
    st.caption("Multi-Agent Research Assistant Dashboard | Multi-Agent Research Assistant for University Students")
    
    # Sidebar
    st.sidebar.title("Navigation")
    
    # API Status
    health = check_api_health()
    if health:
        st.sidebar.success("✅ API Online")
        st.sidebar.json(health)
    else:
        st.sidebar.error("❌ API Offline")
        st.sidebar.caption(f"Start API at {API_BASE}")
        st.sidebar.caption("uvicorn main:app --port 8013")
    
    st.sidebar.divider()
    
    # Quick Stats
    st.sidebar.subheader("System Stats")
    sessions = get_sample_research_sessions()
    active = len([s for s in sessions if s.get("status") == "running"])
    completed = len([s for s in sessions if s.get("status") == "completed"])
    
    st.sidebar.metric("Active Sessions", active)
    st.sidebar.metric("Completed", completed)
    st.sidebar.metric("Total Sessions", len(sessions))
    
    st.sidebar.divider()
    
    # Agent Status
    st.sidebar.subheader("Agent Status")
    st.sidebar.markdown(render_agent_status("Literature", "running", 37))
    st.sidebar.markdown(render_agent_status("Experiment", "completed", 23))
    st.sidebar.markdown(render_agent_status("Progress", "running", 15))
    
    st.sidebar.divider()
    
    # Settings
    st.sidebar.subheader("Settings")
    refresh = st.sidebar.slider("Auto-refresh (seconds)", 0, 30, 5)
    if refresh > 0:
        time.sleep(refresh)
    
    # Main Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Dashboard",
        "📚 Literature Agent",
        "🔬 Experiment Agent", 
        "📈 Progress Tracker",
        "🧠 Knowledge Graph"
    ])
    
    with tab1:
        st.subheader("Research Sessions Overview")
        
        # Session cards
        for session in sessions:
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"**{session['research_topic']}**")
                    st.caption(f"👤 {session['user_profile']['name']} | {session['user_profile']['major']}")
                    render_research_progress(session)
                
                with col2:
                    st.metric("Papers", session.get('literature_count', 0))
                    st.metric("Designs", session.get('experiment_designs', 0))
                
                with col3:
                    created = session.get('created_at', '')
                    if created:
                        dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        st.caption(f"Created: {dt.strftime('%m-%d %H:%M')}")
                    
                    if st.button("View Details", key=f"view_{session['session_id']}"):
                        st.session_state.selected_session = session['session_id']
                
                st.divider()
        
        # Agent Activity Chart
        st.subheader("Agent Activity")
        agent_data = pd.DataFrame({
            'Agent': ['Literature', 'Experiment', 'Progress', 'Orchestrator'],
            'Total Calls': [37, 23, 15, 8],
            'Avg Duration (s)': [2.5, 4.2, 1.8, 0.5],
            'Success Rate': [0.95, 0.88, 0.92, 1.0]
        })
        st.dataframe(agent_data, use_container_width=True, hide_index=True)
    
    with tab2:
        st.subheader("Literature Agent")
        st.caption("RAG + Web Search for academic papers")
        
        # Search interface
        col1, col2 = st.columns([3, 1])
        with col1:
            query = st.text_input("Search Query", placeholder="Enter research topic...")
        with col2:
            mode = st.selectbox("Mode", ["hybrid", "rag", "web"])
        
        if st.button("🔍 Search Literature"):
            with st.spinner("Searching..."):
                time.sleep(1)  # Simulate API call
                literature = get_sample_literature_results()
                
                st.success(f"Found {len(literature['papers'])} papers")
                
                # Results
                for paper in literature['papers']:
                    with st.expander(f"📄 {paper['title']}"):
                        st.write(f"**Authors:** {', '.join(paper['authors'])}")
                        st.write(f"**Year:** {paper['year']}")
                        st.write(f"**Relevance:** {paper['relevance_score']:.2f}")
                        st.write(f"**Citations:** {paper['citations']}")
                
                # Web results
                st.subheader("Web Results")
                for web in literature['web_results']:
                    st.markdown(f"- 🌐 [{web['title']}]({web['url']}) (Relevance: {web['relevance_score']:.2f})")
        
        st.divider()
        
        # Knowledge Graph for Literature
        st.subheader("Literature Knowledge Graph")
        render_knowledge_graph_visualization()
    
    with tab3:
        st.subheader("Experiment Design Agent")
        st.caption("Chain-of-Design Loop with reflection")
        
        # Design interface
        col1, col2 = st.columns(2)
        with col1:
            research_question = st.text_area("Research Question", placeholder="What research question do you want to address?")
        with col2:
            hypothesis = st.text_area("Hypothesis (optional)", placeholder="Your hypothesis...")
        
        col3, col4 = st.columns(2)
        with col3:
            constraints = st.multiselect("Constraints", ["Limited data", "Limited compute", "Time constraint", "No GPU"])
        with col4:
            resources = st.multiselect("Available Resources", ["Python", "PyTorch", "Jupyter", "Google Colab"])
        
        iterations = st.slider("Reflection Iterations", 1, 5, 3)
        
        if st.button("🔬 Design Experiment"):
            with st.spinner("Running Chain-of-Design Loop..."):
                time.sleep(2)
                design = get_sample_experiment_design()
                
                st.success("Experiment design completed!")
                
                # Show iterations
                for it in design['iterations']:
                    with st.expander(f"🔁 Iteration {it['iteration']} (Score: {it['score']:.2f})"):
                        snapshot = it['design_snapshot']
                        st.write(f"**Title:** {snapshot['title']}")
                        st.write(f"**Objectives:** {', '.join(snapshot['objectives'])}")
                        st.write(f"**Reflection:** {it['reflection_notes']}")
                
                # Final design
                st.subheader("Final Design")
                final = design['final_design']
                st.json(final)
                
                # Reflection score
                st.metric("Reflection Score", f"{design['reflection_score']:.2f}")
    
    with tab4:
        st.subheader("Progress Management Agent")
        st.caption("Digital Twin Knowledge Graph + Dual-Track Async Management")
        
        # Progress overview
        progress_data = {
            "Exploration Track": {"total": 10, "completed": 6, "in_progress": 2, "pending": 2},
            "Verification Track": {"total": 8, "completed": 4, "in_progress": 2, "pending": 2}
        }
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🚀 Exploration Track")
            for status, count in progress_data["Exploration Track"].items():
                pct = count / progress_data["Exploration Track"]["total"] * 100
                st.progress(pct / 100, text=f"{status}: {count}")
        
        with col2:
            st.markdown("### ✅ Verification Track")
            for status, count in progress_data["Verification Track"].items():
                pct = count / progress_data["Verification Track"]["total"] * 100
                st.progress(pct / 100, text=f"{status}: {count}")
        
        st.divider()
        
        # Milestones
        st.subheader("Milestones")
        milestones = [
            {"name": "Literature Review", "due": "2024-06-01", "status": "completed", "progress": 100},
            {"name": "Experiment Design", "due": "2024-06-15", "status": "completed", "progress": 100},
            {"name": "Data Collection", "due": "2024-07-01", "status": "in_progress", "progress": 60},
            {"name": "Model Training", "due": "2024-08-01", "status": "pending", "progress": 0},
            {"name": "Results Analysis", "due": "2024-09-01", "status": "pending", "progress": 0},
        ]
        
        for m in milestones:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                status_icon = {"completed": "✅", "in_progress": "🔄", "pending": "⏳"}.get(m['status'], "❓")
                st.write(f"{status_icon} {m['name']}")
                st.progress(m['progress'] / 100)
            with col2:
                st.caption(f"Due: {m['due']}")
            with col3:
                st.write(f"{m['progress']}%")
        
        st.divider()
        
        # Estimated completion
        st.info("📅 Estimated completion: 2024-10-15")
    
    with tab5:
        st.subheader("Knowledge Graph")
        st.caption("Multi-granularity: Topic → Paper → Claim → Evidence")
        
        # KG Overview
        kg_stats = {
            "Topics": 5,
            "Papers": 28,
            "Claims": 84,
            "Evidence": 156
        }
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Topics", kg_stats["Topics"])
        with col2:
            st.metric("Papers", kg_stats["Papers"])
        with col3:
            st.metric("Claims", kg_stats["Claims"])
        with col4:
            st.metric("Evidence", kg_stats["Evidence"])
        
        st.divider()
        
        # Knowledge Graph Visualization
        st.subheader("Knowledge Graph Visualization")
        render_knowledge_graph_visualization()
        
        st.divider()
        
        # KG Statistics
        st.subheader("Method Distribution")
        method_data = pd.DataFrame({
            'Method': ['BERT', 'Transformer', 'CNN', 'RNN', 'GNN', 'Others'],
            'Frequency': [45, 38, 25, 18, 12, 22],
            'Avg Relevance': [0.88, 0.85, 0.72, 0.68, 0.75, 0.65]
        })
        st.dataframe(method_data, use_container_width=True, hide_index=True)
        
        # AddKG interface
        st.subheader("Add to Knowledge Graph")
        with st.form("add_kg_node"):
            node_type = st.selectbox("Node Type", ["topic", "paper", "claim", "evidence", "method"])
            node_label = st.text_input("Label")
            node_properties = st.text_area("Properties (JSON)")
            
            if st.form_submit_button("Add Node"):
                st.success(f"Added {node_type}: {node_label}")
    
    # Footer
    st.divider()
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
