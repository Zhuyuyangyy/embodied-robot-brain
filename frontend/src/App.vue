<template>
  <div class="app-container">
    <!-- 背景动画 -->
    <div class="bg-animation">
      <div class="orb orb-1"></div>
      <div class="orb orb-2"></div>
      <div class="orb orb-3"></div>
      <div class="grid-lines"></div>
    </div>

    <!-- 顶部导航 -->
    <header class="glass-header">
      <div class="logo">
        <span class="logo-icon">🧠</span>
        <span class="logo-text">智能原生教育</span>
      </div>
      <nav class="nav-links">
        <a href="#" class="nav-link active">科研助手</a>
        <a href="#" class="nav-link">知识图谱</a>
        <a href="#" class="nav-link">帮助</a>
      </nav>
    </header>

    <!-- 主内容区 -->
    <main class="main-content">
      <!-- 左侧边栏 - Agent状态 -->
      <aside class="sidebar glass-panel">
        <h3>Agent 状态</h3>
        <div class="agent-list">
          <div class="agent-item" v-for="agent in agents" :key="agent.id">
            <div class="agent-avatar" :class="agent.status">
              <span v-if="agent.type === 'literature'">📚</span>
              <span v-else-if="agent.type === 'experiment'">🔬</span>
              <span v-else>📊</span>
            </div>
            <div class="agent-info">
              <span class="agent-name">{{ agent.name }}</span>
              <span class="agent-status" :class="agent.status">{{ agent.statusText }}</span>
            </div>
          </div>
        </div>
      </aside>

      <!-- 中间工作区 -->
      <section class="workspace">
        <!-- 欢迎卡片 -->
        <div class="welcome-card glass-panel">
          <h1>欢迎使用 Multi-Agent 科研助手</h1>
          <p>基于Agent架构的大学生个性化科研平台</p>
          <div class="features">
            <div class="feature-tag">📚 文献发现</div>
            <div class="feature-tag">🔬 实验设计</div>
            <div class="feature-tag">📊 进度追踪</div>
          </div>
        </div>

        <!-- 研究主题输入 -->
        <div class="research-input glass-panel">
          <h2>开始你的研究</h2>
          <div class="input-wrapper">
            <input 
              v-model="researchTopic" 
              type="text" 
              placeholder="输入你的研究主题，如：Transformer在医学影像中的应用..."
              class="glass-input"
            />
            <button @click="startResearch" class="glow-button" :disabled="isLoading">
              <span v-if="!isLoading">🚀 开始研究</span>
              <span v-else>⏳ 分析中...</span>
            </button>
          </div>
        </div>

        <!-- 研究阶段卡片 -->
        <div class="stages-grid">
          <div 
            v-for="(stage, index) in researchStages" 
            :key="index" 
            class="stage-card glass-panel"
            :class="{ active: stage.active, completed: stage.completed }"
          >
            <div class="stage-icon">{{ stage.icon }}</div>
            <h3>{{ stage.title }}</h3>
            <p>{{ stage.description }}</p>
            <div v-if="stage.result" class="stage-result">
              <pre>{{ JSON.stringify(stage.result, null, 2) }}</pre>
            </div>
            <div class="stage-progress" v-if="stage.loading">
              <div class="spinner"></div>
            </div>
          </div>
        </div>
      </section>

      <!-- 右侧边栏 - 知识图谱预览 -->
      <aside class="kg-panel glass-panel">
        <h3>📊 知识图谱</h3>
        <div class="kg-preview">
          <div class="kg-node topic">Topic</div>
          <div class="kg-line"></div>
          <div class="kg-node paper">Paper</div>
          <div class="kg-line"></div>
          <div class="kg-node claim">Claim</div>
          <div class="kg-line"></div>
          <div class="kg-node evidence">Evidence</div>
        </div>
        <div class="kg-layers">
          <div class="kg-layer">层级: Topic → Paper → Claim → Evidence</div>
        </div>
      </aside>
    </main>

    <!-- 底部状态栏 -->
    <footer class="glass-footer">
      <div class="status-item">
        <span class="status-dot online"></span>
        系统在线
      </div>
      <div class="status-item">
        Agent数量: {{ agents.length }}
      </div>
      <div class="status-item">
        版本: 1.0.0
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import axios from 'axios'

const API_BASE = 'http://localhost:8013/api/v1/research'

const researchTopic = ref('')
const isLoading = ref(false)

const agents = reactive([
  { id: 1, type: 'literature', name: '文献Agent', status: 'idle', statusText: '空闲' },
  { id: 2, type: 'experiment', name: '实验设计Agent', status: 'idle', statusText: '空闲' },
  { id: 3, type: 'progress', name: '进度管理Agent', status: 'idle', statusText: '空闲' },
])

const researchStages = reactive([
  { 
    title: '文献发现', 
    icon: '📚', 
    description: 'RAG + Web搜索，发现相关论文',
    active: false, 
    completed: false,
    loading: false,
    result: null 
  },
  { 
    title: '实验设计', 
    icon: '🔬', 
    description: 'Chain-of-Design Loop反思回路',
    active: false, 
    completed: false,
    loading: false,
    result: null 
  },
  { 
    title: '进度追踪', 
    icon: '📊', 
    description: '数字孪生知识图谱',
    active: false, 
    completed: false,
    loading: false,
    result: null 
  },
])

const sessionId = ref(null)

async function startResearch() {
  if (!researchTopic.value.trim()) return
  
  isLoading.value = true
  researchStages.forEach(s => { s.loading = true; s.active = false; s.completed = false; s.result = null })
  
  try {
    // 启动研究会话
    const resp = await axios.post(`${API_BASE}/sessions`, {
      user_profile: { user_id: 'user_1', name: '学生用户' },
      research_topic: researchTopic.value,
      goals: ['完成文献调研', '设计实验']
    })
    
    sessionId.value = resp.data.session_id
    
    // 更新阶段1 - 文献
    researchStages[0].completed = true
    researchStages[0].result = resp.data.stages?.literature
    
    // 更新阶段2 - 实验
    researchStages[1].completed = true  
    researchStages[1].result = resp.data.stages?.experiment
    
    // 更新阶段3 - 进度
    researchStages[2].completed = true
    researchStages[2].result = resp.data.stages?.progress
    
    // 更新Agent状态
    agents.forEach(a => { a.status = 'idle'; a.statusText = '完成' })
    
  } catch (err) {
    console.error('研究启动失败:', err)
    alert('研究启动失败，请检查后端服务是否运行')
  } finally {
    isLoading.value = false
    researchStages.forEach(s => s.loading = false)
  }
}
</script>

<style>
/* === 沉浸式数字艺术风格 - 玻璃拟态2.0 === */

.app-container {
  min-height: 100vh;
  position: relative;
  color: #e0e0e0;
}

/* 背景动画 */
.bg-animation {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: -1;
  overflow: hidden;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.4;
  animation: float 20s infinite ease-in-out;
}

.orb-1 {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, #667eea 0%, #764ba2 100%);
  top: -200px;
  left: -100px;
  animation-delay: 0s;
}

.orb-2 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, #f093fb 0%, #f5576c 100%);
  top: 50%;
  right: -150px;
  animation-delay: -5s;
}

.orb-3 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, #4facfe 0%, #00f2fe 100%);
  bottom: -100px;
  left: 30%;
  animation-delay: -10s;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  25% { transform: translate(50px, 50px) scale(1.1); }
  50% { transform: translate(0, 100px) scale(0.95); }
  75% { transform: translate(-50px, 50px) scale(1.05); }
}

.grid-lines {
  position: absolute;
  width: 100%;
  height: 100%;
  background-image: 
    linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
  background-size: 50px 50px;
  animation: gridMove 30s linear infinite;
}

@keyframes gridMove {
  0% { transform: perspective(500px) rotateX(60deg) translateY(0); }
  100% { transform: perspective(500px) rotateX(60deg) translateY(50px); }
}

/* 玻璃拟态面板 */
.glass-panel {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

/* 顶部导航 */
.glass-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 40px;
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-icon {
  font-size: 32px;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

.logo-text {
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea, #764ba2);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.nav-links {
  display: flex;
  gap: 30px;
}

.nav-link {
  color: #a0a0a0;
  text-decoration: none;
  font-weight: 500;
  transition: all 0.3s;
  padding: 8px 16px;
  border-radius: 10px;
}

.nav-link:hover, .nav-link.active {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

/* 主内容区 */
.main-content {
  display: grid;
  grid-template-columns: 280px 1fr 280px;
  gap: 30px;
  padding: 30px 40px;
  max-width: 1600px;
  margin: 0 auto;
}

/* 侧边栏 */
.sidebar, .kg-panel {
  padding: 24px;
  height: fit-content;
  position: sticky;
  top: 30px;
}

.sidebar h3, .kg-panel h3 {
  font-size: 16px;
  margin-bottom: 20px;
  color: #a0a0a0;
}

.agent-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.agent-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  transition: all 0.3s;
}

.agent-item:hover {
  background: rgba(255, 255, 255, 0.08);
  transform: translateX(5px);
}

.agent-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  background: rgba(255, 255, 255, 0.1);
}

.agent-avatar.idle { border: 2px solid #4facfe; }
.agent-avatar.working { border: 2px solid #f5576c; animation: spin 1s linear infinite; }
.agent-avatar.completed { border: 2px solid #00f2fe; }

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.agent-info {
  display: flex;
  flex-direction: column;
}

.agent-name {
  font-weight: 500;
  font-size: 14px;
}

.agent-status {
  font-size: 12px;
  color: #666;
}

.agent-status.idle { color: #4facfe; }
.agent-status.working { color: #f5576c; }
.agent-status.completed { color: #00f2fe; }

/* 工作区 */
.workspace {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.welcome-card {
  padding: 40px;
  text-align: center;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(118, 75, 162, 0.2));
}

.welcome-card h1 {
  font-size: 28px;
  margin-bottom: 10px;
  background: linear-gradient(135deg, #fff, #a0a0a0);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.welcome-card p {
  color: #888;
  margin-bottom: 20px;
}

.features {
  display: flex;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
}

.feature-tag {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  font-size: 14px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

/* 输入区域 */
.research-input {
  padding: 30px;
}

.research-input h2 {
  font-size: 18px;
  margin-bottom: 20px;
}

.input-wrapper {
  display: flex;
  gap: 16px;
}

.glass-input {
  flex: 1;
  padding: 16px 24px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  color: #fff;
  font-size: 16px;
  outline: none;
  transition: all 0.3s;
}

.glass-input:focus {
  border-color: #667eea;
  box-shadow: 0 0 20px rgba(102, 126, 234, 0.3);
}

.glass-input::placeholder {
  color: #666;
}

/* 发光按钮 */
.glow-button {
  padding: 16px 32px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border: none;
  border-radius: 12px;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}

.glow-button::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
  transition: left 0.5s;
}

.glow-button:hover::before {
  left: 100%;
}

.glow-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 30px rgba(102, 126, 234, 0.5);
}

.glow-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 阶段卡片网格 */
.stages-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.stage-card {
  padding: 24px;
  text-align: center;
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}

.stage-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 3px;
  background: linear-gradient(90deg, transparent, #667eea, transparent);
  opacity: 0;
  transition: opacity 0.3s;
}

.stage-card:hover::before {
  opacity: 1;
}

.stage-card.active {
  border-color: #667eea;
  transform: scale(1.02);
}

.stage-card.completed {
  border-color: #00f2fe;
}

.stage-card.completed::after {
  content: '✓';
  position: absolute;
  top: 10px;
  right: 10px;
  width: 24px;
  height: 24px;
  background: #00f2fe;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #000;
  font-size: 14px;
}

.stage-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.stage-card h3 {
  font-size: 16px;
  margin-bottom: 8px;
}

.stage-card p {
  font-size: 13px;
  color: #888;
}

.stage-result {
  margin-top: 16px;
  text-align: left;
}

.stage-result pre {
  font-size: 11px;
  color: #aaa;
  background: rgba(0,0,0,0.3);
  padding: 10px;
  border-radius: 8px;
  max-height: 200px;
  overflow: auto;
}

.stage-progress {
  margin-top: 16px;
}

.spinner {
  width: 30px;
  height: 30px;
  border: 3px solid rgba(255,255,255,0.1);
  border-top-color: #667eea;
  border-radius: 50%;
  margin: 0 auto;
  animation: spin 1s linear infinite;
}

/* 知识图谱面板 */
.kg-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px 0;
}

.kg-node {
  padding: 10px 20px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
}

.kg-node.topic {
  background: linear-gradient(135deg, #667eea, #764ba2);
}

.kg-node.paper {
  background: rgba(79, 172, 254, 0.3);
  border: 1px solid #4facfe;
}

.kg-node.claim {
  background: rgba(0, 242, 254, 0.3);
  border: 1px solid #00f2fe;
}

.kg-node.evidence {
  background: rgba(245, 87, 108, 0.3);
  border: 1px solid #f5576c;
}

.kg-line {
  width: 2px;
  height: 20px;
  background: linear-gradient(to bottom, rgba(255,255,255,0.3), transparent);
}

.kg-layers {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid rgba(255,255,255,0.1);
}

.kg-layer {
  font-size: 12px;
  color: #666;
  text-align: center;
}

/* 底部状态栏 */
.glass-footer {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: center;
  gap: 40px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(20px);
  font-size: 13px;
  color: #888;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.online {
  background: #00f2fe;
  box-shadow: 0 0 10px #00f2fe;
}
</style>
