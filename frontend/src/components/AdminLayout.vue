<template>
  <div class="min-h-screen bg-slate-100">
    <header class="border-b border-slate-200 bg-slate-900 px-8 py-4 text-white">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-xl font-bold">SpreadFleet 管理台</h1>
          <p class="mt-1 text-sm text-slate-300">平台运营与套餐管理</p>
        </div>
        <button class="rounded-lg bg-white/10 px-3 py-2 text-sm hover:bg-white/20" @click="logout">退出</button>
      </div>
    </header>

    <div v-if="!auth.isAuthenticated" class="p-8">
      <p class="text-slate-600">请先在主站登录管理员账号，再打开此页面。</p>
      <a href="/spreadfleet/login" class="btn-primary mt-4 inline-flex">去登录</a>
    </div>

    <div v-else-if="!auth.user?.is_admin" class="p-8 text-red-600">当前账号无管理员权限</div>

    <div v-else class="flex">
      <aside class="w-56 shrink-0 border-r border-slate-200 bg-white p-4">
        <nav class="space-y-1 text-sm">
          <RouterLink
            v-for="item in nav"
            :key="item.to"
            :to="item.to"
            class="block rounded-lg px-3 py-2"
            :class="route.path === item.to ? 'bg-brand-50 font-medium text-brand-700' : 'text-slate-600 hover:bg-slate-50'"
          >
            {{ item.label }}
          </RouterLink>
        </nav>
      </aside>
      <main class="min-w-0 flex-1 p-8">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/api/client'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const nav = [
  { to: '/admin', label: '总览' },
  { to: '/admin/workspaces', label: '团队空间' },
  { to: '/admin/plans', label: '套餐管理' },
]

onMounted(async () => {
  if (auth.token) {
    try {
      auth.user = await api.me(auth.token)
      localStorage.setItem('spread_fleet_user', JSON.stringify(auth.user))
    } catch {
      auth.logout()
    }
  }
})

function logout() {
  auth.logout()
  router.push('/login')
}
</script>
