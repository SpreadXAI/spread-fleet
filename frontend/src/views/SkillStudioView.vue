<template>
  <div v-if="loading" class="text-slate-500">加载中…</div>
  <div v-else class="space-y-8">
    <section class="card space-y-4 p-6">
      <h2 class="text-lg font-semibold">创作新 Skill（必须先选账号）</h2>
      <p class="text-sm text-slate-500">
        在选定账号的 Cookie / 人设上下文中，使用平台内置 <code>skill-creator</code> + <code>skill-ops</code>
        创作养号 Skill。未选账号、未填 Cookie 不能开始。
      </p>

      <div>
        <label class="mb-1 block text-sm font-medium">目标账号 <span class="text-red-500">*</span></label>
        <select v-model.number="createAccountId" class="input max-w-md" required>
          <option :value="0" disabled>请选择账号…</option>
          <option v-for="a in accounts" :key="a.id" :value="a.id">
            @{{ a.handle }}{{ a.has_cookie ? '' : '（未填 Cookie）' }}
          </option>
        </select>
        <p v-if="selectedCreateAccount && !selectedCreateAccount.has_cookie" class="mt-1 text-xs text-amber-600">
          请先在账号详情页保存 Session Cookie
        </p>
      </div>

      <div v-if="platformAuthoring.length" class="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm">
        <div class="font-medium text-brand-700">平台创作 Skill 栈（只读）</div>
        <ul class="mt-2 space-y-1 text-xs text-slate-600">
          <li v-for="s in platformAuthoring" :key="s.id">{{ s.name }} · {{ s.slug }}</li>
        </ul>
      </div>

      <input v-model="createTitle" class="input" placeholder="Skill 名称" />
      <textarea
        v-model="createPrompt"
        class="input min-h-[120px] font-mono text-xs"
        placeholder="输入/输出契约 + 养号策略描述…"
      />
      <button class="btn-primary" :disabled="creating || !canCreate" @click="startCreate">
        {{ creating ? '派发中…' : '开始创作' }}
      </button>
      <p v-if="createMsg" class="text-sm" :class="createError ? 'text-red-600' : 'text-green-600'">{{ createMsg }}</p>
    </section>

    <section class="card space-y-4 p-6">
      <h2 class="text-lg font-semibold">批量安装到账号</h2>
      <p class="text-sm text-slate-500">仅可安装空间层 / 我的 Skill，平台创作栈不可批量安装。</p>
      <div class="grid gap-4 lg:grid-cols-2">
        <div>
          <label class="mb-1 block text-sm font-medium">选择 Skill</label>
          <select v-model="selectedSkillKey" class="input w-full">
            <option value="">请选择…</option>
            <optgroup label="空间 Skill">
              <option v-for="s in catalog.workspace" :key="'w' + s.id" :value="skillKey(s)">
                {{ s.name }} ({{ s.slug }})
              </option>
            </optgroup>
            <optgroup label="我的 Skill">
              <option v-for="s in catalog.mine" :key="'m' + s.id" :value="skillKey(s)">
                {{ s.name }} ({{ s.slug }})
              </option>
            </optgroup>
          </select>
        </div>
      </div>

      <div>
        <div class="mb-2 flex items-center justify-between">
          <label class="text-sm font-medium">目标账号</label>
          <button type="button" class="text-xs text-brand-600 hover:underline" @click="toggleAllAccounts">
            {{ allSelected ? '取消全选' : '全选' }}
          </button>
        </div>
        <div class="max-h-48 space-y-2 overflow-y-auto rounded-lg border border-slate-200 p-3">
          <label v-for="a in accounts" :key="a.id" class="flex cursor-pointer items-center gap-2 text-sm">
            <input v-model="selectedAccountIds" type="checkbox" :value="a.id" />
            <span>@{{ a.handle }}</span>
          </label>
        </div>
      </div>

      <button
        class="btn-primary"
        :disabled="installing || !selectedSkill || !selectedAccountIds.length"
        @click="batchInstall"
      >
        {{ installing ? '安装中…' : `安装到 ${selectedAccountIds.length} 个账号` }}
      </button>
      <p v-if="installMsg" class="text-sm" :class="installError ? 'text-red-600' : 'text-green-600'">{{ installMsg }}</p>
    </section>

    <section class="card space-y-3 p-6">
      <h2 class="text-lg font-semibold">全部 Skill（{{ catalog.all.length }}）</h2>
      <p class="text-sm text-slate-500">Spider 雷达统一展示平台 + 空间 + 我的 Skill。</p>
      <div v-if="!catalog.all.length" class="text-sm text-slate-500">暂无 Skill</div>
      <div v-else class="divide-y divide-slate-100">
        <div
          v-for="s in catalog.all"
          :key="`${s.layer}-${s.id}`"
          class="flex flex-wrap items-start justify-between gap-2 py-3 text-sm"
        >
          <div>
            <div class="font-medium">{{ s.name }}</div>
            <div class="text-xs text-slate-500">{{ s.slug }} · v{{ s.current_version || '—' }} · {{ s.layer }}</div>
            <p v-if="s.description" class="mt-1 text-slate-600">{{ s.description }}</p>
          </div>
          <span v-if="s.readonly" class="badge bg-brand-100 text-brand-700">平台只读</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { api, type SkillCatalog, type SkillCatalogItem, type SocialAccount } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const loading = ref(true)
const catalog = ref<SkillCatalog>({ platform: [], workspace: [], mine: [], all: [] })
const accounts = ref<SocialAccount[]>([])

const createTitle = ref('养号 Skill')
const createPrompt = ref('')
const createAccountId = ref(0)
const creating = ref(false)
const createMsg = ref('')
const createError = ref(false)

const selectedSkillKey = ref('')
const selectedAccountIds = ref<number[]>([])
const installing = ref(false)
const installMsg = ref('')
const installError = ref(false)

const platformAuthoring = computed(() =>
  catalog.value.platform.filter((s) => s.readonly && /creator|ops/i.test(s.slug)),
)

const selectedCreateAccount = computed(() => accounts.value.find((a) => a.id === createAccountId.value) ?? null)

const canCreate = computed(
  () =>
    createAccountId.value > 0 &&
    !!selectedCreateAccount.value?.has_cookie &&
    createPrompt.value.trim().length >= 10,
)

const installableSkills = computed(() => [...catalog.value.workspace, ...catalog.value.mine])

const skillMap = computed(() => {
  const m = new Map<string, SkillCatalogItem>()
  for (const s of installableSkills.value) m.set(skillKey(s), s)
  return m
})

const selectedSkill = computed(() => skillMap.value.get(selectedSkillKey.value) ?? null)
const allSelected = computed(
  () => accounts.value.length > 0 && selectedAccountIds.value.length === accounts.value.length,
)

function skillKey(s: SkillCatalogItem) {
  return `${s.id}:${s.current_version_id ?? 0}`
}

function toggleAllAccounts() {
  selectedAccountIds.value = allSelected.value ? [] : accounts.value.map((a) => a.id)
}

watch(accounts, (list) => {
  if (list.length && createAccountId.value === 0) {
    const withCookie = list.find((a) => a.has_cookie)
    createAccountId.value = withCookie?.id ?? list[0].id
  }
})

async function load() {
  if (!auth.token) return
  const [cat, accs] = await Promise.all([api.skillCatalog(auth.token), api.myAccounts(auth.token)])
  catalog.value = cat
  accounts.value = accs
  loading.value = false
}

async function startCreate() {
  if (!auth.token || !canCreate.value) return
  creating.value = true
  createMsg.value = ''
  createError.value = false
  try {
    const res = await api.createSkillSession(auth.token, {
      account_id: createAccountId.value,
      title: createTitle.value,
      prompt: createPrompt.value,
    })
    createMsg.value = `${res.message} · work_id=${res.tactile_work_id} · @${res.account_handle}`
  } catch (e) {
    createError.value = true
    createMsg.value = e instanceof Error ? e.message : '创作派发失败'
  }
  creating.value = false
}

async function batchInstall() {
  if (!auth.token || !selectedSkill.value) return
  const skill = selectedSkill.value
  if (!skill.current_version_id) {
    installError.value = true
    installMsg.value = 'Skill 缺少 version_id'
    return
  }
  installing.value = true
  installMsg.value = ''
  installError.value = false
  try {
    const res = await api.batchInstallSkill(auth.token, {
      skill_id: skill.id,
      version_id: skill.current_version_id,
      account_ids: selectedAccountIds.value,
      slug: skill.slug,
      name: skill.name,
    })
    installMsg.value = `已安装到 ${res.installed_count} 个账号`
  } catch (e) {
    installError.value = true
    installMsg.value = e instanceof Error ? e.message : '批量安装失败'
  }
  installing.value = false
}

onMounted(load)
</script>
