<template>
  <el-config-provider :locale="zhCn">
    <div class="app-container">
      <aside class="sidebar">
        <div class="logo">
          <span class="logo-icon">✦</span>
          <span class="logo-text">EMPI</span>
        </div>
        <nav class="nav-menu">
          <router-link v-for="item in navItems" :key="item.path" :to="item.path" class="nav-item" :class="{ active: $route.path === item.path }">
            <span class="nav-icon">{{ item.icon }}</span>
            <span class="nav-label">{{ item.label }}</span>
          </router-link>
        </nav>
        <div class="sidebar-footer">
          <span class="version">v1.0</span>
        </div>
      </aside>

      <main class="main-content">
        <header class="top-bar">
          <div class="page-title">{{ currentPageTitle }}</div>
          <div class="top-bar-actions">
            <span class="time">{{ currentTime }}</span>
          </div>
        </header>
        <div class="page-content">
          <router-view />
        </div>
      </main>
    </div>
  </el-config-provider>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElConfigProvider } from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

const route = useRoute()
const currentTime = ref('')

const navItems = [
  { path: '/', label: '仪表盘', icon: '◈' },
  { path: '/config', label: '配置', icon: '◎' },
  { path: '/pending', label: '待审核', icon: '◉' },
  { path: '/merged', label: '已合并', icon: '◐' },
  { path: '/patients', label: '患者查询', icon: '◇' }
]

const pageTitleMap = {
  '/': '仪表盘',
  '/config': '系统配置',
  '/pending': '待审核合并',
  '/merged': '合并历史',
  '/patients': '患者查询'
}

const currentPageTitle = computed(() => pageTitleMap[route.path] || 'EMPI')

let timer
onMounted(() => {
  const updateTime = () => {
    const now = new Date()
    currentTime.value = now.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }
  updateTime()
  timer = setInterval(updateTime, 60000)
})
onUnmounted(() => clearInterval(timer))
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Serif+Display&display=swap');

:root {
  --bg-primary: #0a0f1a;
  --bg-secondary: #111827;
  --bg-card: rgba(17, 24, 39, 0.7);
  --accent-emerald: #10b981;
  --accent-emerald-dim: rgba(16, 185, 129, 0.15);
  --accent-indigo: #6366f1;
  --accent-amber: #f59e0b;
  --text-primary: #f9fafb;
  --text-secondary: #9ca3af;
  --text-muted: #6b7280;
  --border-color: rgba(255, 255, 255, 0.08);
  --shadow-soft: 0 4px 24px rgba(0, 0, 0, 0.4);
  --radius-lg: 16px;
  --radius-md: 10px;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  min-height: 100vh;
}

.app-container {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 220px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  padding: 24px 0;
  position: fixed;
  height: 100vh;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 24px;
  margin-bottom: 40px;
}

.logo-icon {
  font-size: 24px;
  color: var(--accent-emerald);
}

.logo-text {
  font-family: 'DM Serif Display', serif;
  font-size: 20px;
  font-weight: 400;
  letter-spacing: 2px;
}

.nav-menu {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 0 12px;
  flex: 1;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  text-decoration: none;
  transition: all 0.2s ease;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--accent-emerald-dim);
  color: var(--accent-emerald);
}

.nav-icon {
  font-size: 18px;
  opacity: 0.7;
}

.nav-item.active .nav-icon {
  opacity: 1;
}

.nav-label {
  font-size: 14px;
  font-weight: 500;
}

.sidebar-footer {
  padding: 0 24px;
}

.version {
  font-size: 11px;
  color: var(--text-muted);
  letter-spacing: 1px;
}

.main-content {
  flex: 1;
  margin-left: 220px;
  display: flex;
  flex-direction: column;
}

.top-bar {
  height: 64px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  background: rgba(10, 15, 26, 0.6);
  backdrop-filter: blur(12px);
  position: sticky;
  top: 0;
  z-index: 10;
}

.page-title {
  font-family: 'DM Serif Display', serif;
  font-size: 18px;
  font-weight: 400;
}

.top-bar-actions {
  display: flex;
  align-items: center;
  gap: 24px;
}

.time {
  font-size: 13px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.page-content {
  padding: 32px;
  flex: 1;
}
</style>