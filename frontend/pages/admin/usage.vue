<template>
  <view class="page"><view class="safe" />
    <view class="topbar"><view class="back" @tap="back">‹</view><view class="top-title"><text class="eyebrow">ADMIN CONSOLE</text><view>调用统计</view></view><view class="spacer" /></view>
    <view class="content">
      <view class="admin-tabs"><view class="admin-tab" @tap="toUsers">用户管理</view><view class="admin-tab active">调用统计</view><view class="admin-tab" @tap="toKnowledge">知识库</view><view class="admin-tab" @tap="toAnnouncements">公告</view></view>

      <view class="periods"><view v-for="item in periods" :key="item" :class="['period', { active: days === item }]" @tap="changeDays(item)">近 {{ item }} 天</view></view>

      <view class="metrics">
        <view class="metric primary"><text class="metric-label">DeepSeek 总 Token</text><text class="metric-value">{{ formatTokens(summary.total_tokens) }}</text><text class="metric-note">输入 {{ formatTokens(summary.prompt_tokens) }} · 输出 {{ formatTokens(summary.completion_tokens) }}</text></view>
        <view class="metric"><text class="metric-label">模型调用</text><text class="metric-value">{{ summary.calls }}</text><text class="metric-note">成功 {{ summary.successful_calls }} 次</text></view>
        <view class="metric"><text class="metric-label">调用成功率</text><text class="metric-value">{{ successRate }}%</text><text class="metric-note">失败 {{ summary.failed_calls }} 次</text></view>
      </view>

      <view class="section-card">
        <view class="section-head"><view><text class="section-index">01</text><text class="section-title">每日消耗</text></view><text class="section-note">Token / 调用次数</text></view>
        <view v-if="summaryLoading" class="empty">正在整理统计数据...</view>
        <view v-else-if="!summary.daily.length" class="empty">所选时间内暂无调用记录</view>
        <view v-for="item in summary.daily" :key="item.date" class="daily-row">
          <text class="daily-date">{{ formatDay(item.date) }}</text>
          <view class="daily-track"><view class="daily-bar" :style="{ width: dailyWidth(item.total_tokens) }" /></view>
          <view class="daily-data"><text>{{ formatTokens(item.total_tokens) }}</text><text>{{ item.calls }} 次</text></view>
        </view>
      </view>

      <view class="section-card calls-card">
        <view class="section-head calls-head"><view><text class="section-index">02</text><text class="section-title">调用明细</text></view><view class="user-filter"><input v-model.trim="userFilter" type="number" placeholder="用户 ID" @confirm="applyFilter" /><text @tap="applyFilter">筛选</text></view></view>
        <view v-if="callsLoading" class="empty">正在加载调用记录...</view>
        <view v-else-if="!calls.length" class="empty">暂无符合条件的调用记录</view>
        <view v-for="item in calls" :key="item.id" class="call-row">
          <view :class="['call-status', item.success ? 'success' : 'failed']"><view class="status-dot" />{{ item.success ? '成功' : '失败' }}</view>
          <view class="call-main"><view class="call-title"><text>用户 #{{ item.user_id }}</text><text class="endpoint">{{ endpointName(item.endpoint) }}</text></view><text class="call-time">{{ formatDateTime(item.created_at) }} · {{ item.model }}</text><text v-if="item.error_type" class="error-type">{{ item.error_type }}</text></view>
          <view class="token-detail"><text>{{ formatTokens(item.total_tokens) }}</text><text>Token</text></view>
        </view>
        <view v-if="totalPages > 1" class="pagination"><button :disabled="page <= 1 || callsLoading" @tap="changePage(-1)">上一页</button><text>{{ page }} / {{ totalPages }}</text><button :disabled="page >= totalPages || callsLoading" @tap="changePage(1)">下一页</button></view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { api } from '../../utils/request.js'

const periods = [7, 30, 90]
const days = ref(30), summaryLoading = ref(false), callsLoading = ref(false)
const summary = reactive({ calls: 0, successful_calls: 0, failed_calls: 0, prompt_tokens: 0, completion_tokens: 0, total_tokens: 0, daily: [] })
const calls = ref([]), total = ref(0), page = ref(1), userFilter = ref('')
const pageSize = 20
const successRate = computed(() => summary.calls ? Math.round(summary.successful_calls * 100 / summary.calls) : 0)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const maxDailyTokens = computed(() => Math.max(1, ...summary.daily.map(item => item.total_tokens || 0)))

onLoad(() => {
  const user = uni.getStorageSync('user') || {}
  if (user.role !== 'admin') {
    uni.showToast({ title: '需要管理员权限', icon: 'none' })
    return setTimeout(() => uni.navigateBack(), 500)
  }
  loadSummary()
  loadCalls()
})

async function loadSummary() {
  summaryLoading.value = true
  try { Object.assign(summary, await api.adminUsageSummary(days.value)) }
  catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
  finally { summaryLoading.value = false }
}
async function loadCalls() {
  callsLoading.value = true
  try {
    const res = await api.adminUsageCalls({ page: page.value, pageSize, userId: userFilter.value })
    calls.value = res.items || []
    total.value = res.total || 0
  } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
  finally { callsLoading.value = false }
}
function changeDays(value) { if (days.value !== value) { days.value = value; loadSummary() } }
function applyFilter() { page.value = 1; loadCalls() }
function changePage(step) { page.value += step; loadCalls() }
function dailyWidth(tokens) { return `${Math.max(4, Math.round((tokens || 0) * 100 / maxDailyTokens.value))}%` }
function formatTokens(value = 0) { if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`; if (value >= 1000) return `${(value / 1000).toFixed(1)}K`; return String(value) }
function formatDay(value) { const d = new Date(`${value}T00:00:00`); return `${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}` }
function formatDateTime(value) { const d = new Date(value); return `${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}` }
function endpointName(value) { return ({ generate: '首次生成', feedback: '反馈调整', regenerate: '重新生成' })[value] || value }
function toUsers() { uni.redirectTo({ url: '/pages/admin/users' }) }
function toKnowledge() { uni.redirectTo({ url: '/pages/knowledge/manage' }) }
function toAnnouncements() { uni.redirectTo({ url: '/pages/admin/announcements' }) }
function back() { uni.navigateBack() }
</script>

<style scoped>
.page{min-height:100vh;background:#f4f0e8;color:#29312d}.safe{height:var(--status-bar-height)}.topbar{height:130rpx;display:flex;align-items:center;padding:0 34rpx;border-bottom:1px solid rgba(47,59,51,.1)}.back,.spacer{width:76rpx}.back{font-size:58rpx;color:#315c4c}.top-title{flex:1;text-align:center;font-size:34rpx;font-weight:650}.eyebrow{display:block;margin-bottom:4rpx;color:#a76d3c;font-size:16rpx;letter-spacing:3rpx}.content{box-sizing:border-box;width:100%;max-width:1000px;margin:auto;padding:34rpx 28rpx 70rpx}.admin-tabs{display:flex;padding:7rpx;margin-bottom:24rpx;border-radius:17rpx;background:#e7e5dd}.admin-tab{flex:1;padding:18rpx;text-align:center;border-radius:13rpx;color:#777b75;font-size:24rpx}.admin-tab.active{background:#fff;color:#315c4c;font-weight:650;box-shadow:0 4rpx 16rpx rgba(55,60,53,.07)}.periods{display:flex;gap:12rpx;margin-bottom:24rpx}.period{padding:12rpx 22rpx;border:1px solid #d9d7cf;border-radius:100rpx;color:#777b75;font-size:21rpx}.period.active{border-color:#315c4c;background:#e4ebe7;color:#315c4c}.metrics{display:grid;grid-template-columns:1.5fr 1fr 1fr;gap:18rpx}.metric{min-width:0;padding:28rpx;border-radius:23rpx;background:rgba(255,255,255,.8);box-shadow:0 12rpx 36rpx rgba(66,61,50,.06)}.metric.primary{background:linear-gradient(135deg,#315c4c,#496f60);color:#fff}.metric-label,.metric-value,.metric-note{display:block}.metric-label{color:#7e837d;font-size:21rpx}.primary .metric-label,.primary .metric-note{color:#d6e3dc}.metric-value{margin:12rpx 0 8rpx;font:600 43rpx serif}.metric-note{overflow:hidden;color:#9a9c96;font-size:18rpx;text-overflow:ellipsis;white-space:nowrap}.section-card{margin-top:24rpx;padding:30rpx;border-radius:24rpx;background:rgba(255,255,255,.78);box-shadow:0 14rpx 44rpx rgba(66,61,50,.065)}.section-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:24rpx}.section-index{margin-right:13rpx;color:#b97a49;font:italic 19rpx serif}.section-title{font-size:28rpx;font-weight:650}.section-note{color:#9b9d97;font-size:19rpx}.daily-row{display:flex;align-items:center;gap:18rpx;padding:15rpx 0}.daily-date{width:72rpx;color:#737872;font-size:21rpx}.daily-track{flex:1;height:14rpx;overflow:hidden;border-radius:100rpx;background:#e8ebe7}.daily-bar{height:100%;border-radius:100rpx;background:linear-gradient(90deg,#759383,#315c4c)}.daily-data{width:145rpx;text-align:right}.daily-data text{display:block}.daily-data text:first-child{color:#315c4c;font-size:22rpx;font-weight:650}.daily-data text:last-child{margin-top:2rpx;color:#aaa79f;font-size:17rpx}.user-filter{display:flex;align-items:center;gap:10rpx}.user-filter input{width:140rpx;height:58rpx;padding:0 15rpx;border-radius:11rpx;background:#f2f1ec;font-size:20rpx}.user-filter text{color:#315c4c;font-size:21rpx}.call-row{display:flex;align-items:center;gap:20rpx;padding:24rpx 0;border-top:1px solid #e8e5dd}.call-status{flex:none;width:82rpx;font-size:20rpx}.call-status.success{color:#3d7557}.call-status.failed{color:#a75045}.status-dot{display:inline-block;width:11rpx;height:11rpx;margin-right:8rpx;border-radius:50%;background:currentColor}.call-main{flex:1;min-width:0}.call-title{display:flex;align-items:center;gap:12rpx;font-size:24rpx;font-weight:650}.endpoint{padding:4rpx 11rpx;border-radius:100rpx;background:#eceae3;color:#7d7164;font-size:17rpx;font-weight:400}.call-time,.error-type{display:block;margin-top:6rpx;color:#969890;font-size:18rpx}.error-type{color:#ae6559}.token-detail{flex:none;text-align:right}.token-detail text{display:block}.token-detail text:first-child{font:600 28rpx serif;color:#315c4c}.token-detail text:last-child{color:#aaa79f;font-size:16rpx}.empty{padding:60rpx 20rpx;text-align:center;color:#999b95;font-size:23rpx}.pagination{display:flex;align-items:center;justify-content:center;gap:20rpx;margin-top:24rpx}.pagination button{width:130rpx;height:62rpx;line-height:62rpx;padding:0;border-radius:12rpx;background:#e5ece7;color:#315c4c;font-size:20rpx}.pagination button[disabled]{background:#eceae4;color:#aaa}.pagination text{color:#7e817b;font-size:20rpx}
@media(max-width:600px){.topbar{height:112rpx;padding:0 20rpx}.back,.spacer{width:58rpx}.top-title{font-size:30rpx}.content{padding:25rpx 18rpx 60rpx}.metrics{grid-template-columns:1fr 1fr}.metric.primary{grid-column:1 / -1}.metric{padding:24rpx 22rpx}.section-card{padding:26rpx 21rpx}.calls-head{align-items:flex-start;gap:16rpx}.call-row{align-items:flex-start;flex-wrap:wrap;gap:13rpx}.call-main{flex:1 1 calc(100% - 100rpx)}.token-detail{margin-left:95rpx;text-align:left}.daily-row{gap:11rpx}.daily-data{width:110rpx}.user-filter input{width:112rpx}}
@media(max-width:360px){.metrics{grid-template-columns:1fr}.metric.primary{grid-column:auto}.calls-head{flex-direction:column}.user-filter{width:100%}.user-filter input{flex:1}.daily-track{display:none}.daily-data{margin-left:auto}.token-detail{margin-left:0;width:100%}}
@media(min-width:768px){.content{padding:28px 28px 60px}.metric{padding:24px}.section-card{padding:28px 32px}.call-row{padding:19px 0}}
</style>
