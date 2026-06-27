<template>
  <div class="flex min-h-screen bg-slate-100">
    <aside class="flex w-64 shrink-0 flex-col border-r border-slate-200 bg-brand-900 text-white">
      <div class="border-b border-white/10 px-5 py-5">
        <div class="text-lg font-bold tracking-tight">Spider雷达</div>
        <div class="mt-1 text-xs text-slate-300">蜘蛛雷达 · 测试环境</div>
      </div>
      <nav class="flex-1 space-y-1 p-3">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition"
          :class="isActive(item.to) ? 'bg-white/15 font-medium' : 'text-slate-300 hover:bg-white/10 hover:text-white'"
        >
          <span>{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>
      <div class="border-t border-white/10 p-4">
        <div class="truncate text-sm font-medium">{{ auth.displayLabel }}</div>
        <div class="truncate text-xs text-slate-400">{{ auth.user?.email }}</div>
        <button class="mt-3 w-full rounded-lg bg-white/10 px-3 py-2 text-xs hover:bg-white/20" @click="onLogout">
          退出登录
        </button>
      </div>
    </aside>

    <div class="flex min-w-0 flex-1 flex-col">
      <header class="border-b border-slate-200 bg-white px-8 py-4">
        <h1 class="text-xl font-semibold text-slate-900">{{ title }}</h1>
        <p v-if="subtitle" class="mt-1 text-sm text-slate-500">{{ subtitle }}</p>
      </header>
      <main class="flex-1 overflow-auto p-8">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const navItems = [
  { to: '/', label: '总览', icon: '📊' },
  { to: '/team', label: '团队空间', icon: '👥' },
  { to: '/market', label: '账号市场', icon: '🛒' },
  { to: '/my-accounts', label: '我的账号', icon: '👤' },
  { to: '/batch-tasks', label: '批量任务', icon: '⚡' },
  { to: '/logs', label: '执行日志', icon: '📋' },
  { to: '/profile', label: '个人资料', icon: '⚙️' },
]

const titles: Record<string, { title: string; subtitle?: string }> = {
  dashboard: { title: '总览', subtitle: '账号与任务运行概况' },
  team: { title: '团队空间', subtitle: '成员协作与邮箱邀请' },
  'my-accounts': { title: '我的账号', subtitle: '已购账号与定时任务管理' },
  'account-detail': { title: '账号详情', subtitle: '人设、Prompt 与定时调度' },
  'batch-tasks': { title: '批量任务', subtitle: '多账号同时执行同一任务' },
  logs: { title: '执行日志', subtitle: '关键步骤与执行汇报' },
  profile: { title: '个人资料', subtitle: '设置昵称与查看邮箱' },
}

const title = computed(() => titles[String(route.name)]?.title ?? 'Spider雷达')
const subtitle = computed(() => titles[String(route.name)]?.subtitle)

function isActive(path: string) {
  if (path === '/') return route.path === '/' || route.path === ''
  return route.path.startsWith(path)
}

function onLogout() {
  auth.logout()
  router.push({ name: 'login' })
}
</script>
