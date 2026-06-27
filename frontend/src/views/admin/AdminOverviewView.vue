<template>
  <div v-if="loading" class="text-slate-500">加载中…</div>
  <div v-else-if="overview" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
    <div v-for="item in cards" :key="item.label" class="card p-5">
      <div class="text-sm text-slate-500">{{ item.label }}</div>
      <div class="mt-2 text-3xl font-bold">{{ item.value }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api, type AdminOverview } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const overview = ref<AdminOverview | null>(null)
const loading = ref(true)

const cards = computed(() => {
  if (!overview.value) return []
  const o = overview.value
  return [
    { label: '注册用户', value: o.total_users },
    { label: '团队空间', value: o.total_workspaces },
    { label: '社媒账号总数', value: o.total_social_accounts },
    { label: '市场可售', value: o.accounts_available },
    { label: '已分配账号', value: o.accounts_assigned },
    { label: '套餐数量', value: o.total_plans },
  ]
})

onMounted(async () => {
  if (!auth.token) return
  overview.value = await api.adminOverview(auth.token)
  loading.value = false
})
</script>
