<template>
  <div>
    <h2 class="mb-4 text-lg font-semibold">套餐管理</h2>
    <div v-if="loading" class="text-slate-500">加载中…</div>
    <div v-else class="grid gap-4 lg:grid-cols-3">
      <div v-for="p in plans" :key="p.id" class="card space-y-3 p-5">
        <div class="flex items-center justify-between">
          <h3 class="font-semibold">{{ p.name }}</h3>
          <span class="badge" :class="p.enabled ? 'bg-green-100 text-green-700' : 'bg-slate-100'">
            {{ p.enabled ? '启用' : '停用' }}
          </span>
        </div>
        <p class="text-sm text-slate-500">{{ p.description }}</p>
        <dl class="space-y-1 text-sm">
          <div class="flex justify-between"><dt class="text-slate-500">账号上限</dt><dd>{{ p.max_accounts }}</dd></div>
          <div class="flex justify-between"><dt class="text-slate-500">成员上限</dt><dd>{{ p.max_members }}</dd></div>
          <div class="flex justify-between"><dt class="text-slate-500">月费</dt><dd>¥{{ p.price_monthly }}</dd></div>
        </dl>
        <div class="border-t border-slate-100 pt-3 space-y-2">
          <label class="text-xs text-slate-500">月费（元）</label>
          <input v-model.number="edits[p.id].price_monthly" class="input" type="number" min="0" step="1" />
          <label class="text-xs text-slate-500">账号上限</label>
          <input v-model.number="edits[p.id].max_accounts" class="input" type="number" min="1" />
          <button class="btn-primary w-full" @click="save(p.id)">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { api, type WorkspacePlan } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const plans = ref<WorkspacePlan[]>([])
const loading = ref(true)
const edits = reactive<Record<number, { price_monthly: number; max_accounts: number }>>({})

onMounted(async () => {
  if (!auth.token) return
  plans.value = await api.adminPlans(auth.token)
  for (const p of plans.value) {
    edits[p.id] = { price_monthly: p.price_monthly, max_accounts: p.max_accounts }
  }
  loading.value = false
})

async function save(id: number) {
  if (!auth.token) return
  const body = edits[id]
  const updated = await api.adminUpdatePlan(auth.token, id, body)
  const idx = plans.value.findIndex((p) => p.id === id)
  if (idx >= 0) plans.value[idx] = updated
}
</script>
