<template>
  <view class="page"><view class="safe" />
    <view class="topbar"><view class="back" @tap="back">‹</view><view class="top-title"><text class="eyebrow">INSPIRATION JOURNEY</text><view>历史详情</view></view><view class="spacer" /></view>
    <view v-if="loading" class="loading">正在展开这段灵感旅程...</view>
    <view v-else-if="detail" class="content">
      <view class="overview">
        <view class="overview-top"><text class="category">{{ detail.category }}</text><text class="date">{{ formatDate(detail.created_at) }}</text></view>
        <view class="overview-title">{{ detail.round_count }} 轮命名灵感</view>
        <view class="conditions"><text v-if="detail.conditions.surname">姓氏 {{ detail.conditions.surname }}</text><text>{{ detail.conditions.gender }}</text><text>{{ detail.conditions.length }}</text><text v-if="detail.conditions.use_bazi">八字五行</text><text v-if="detail.conditions.brand_tone">调性 {{ detail.conditions.brand_tone }}</text><text v-if="detail.conditions.target_audience">客群 {{ detail.conditions.target_audience }}</text><text v-if="detail.conditions.ip_setting">含角色设定</text><text v-if="detail.conditions.other">{{ detail.conditions.other }}</text></view>
        <view class="retention">该记录将保留至 {{ formatDate(detail.expires_at) }}</view>
      </view>

      <view class="timeline">
        <view v-for="round in detail.rounds" :key="round.id" class="round-block">
          <view class="timeline-side"><view class="round-dot">{{ round.round_number }}</view><view class="timeline-line" /></view>
          <view class="round-content">
            <view class="round-head"><view class="round-title">{{ round.round_number === 1 ? '初次灵感' : `第 ${round.round_number} 轮调整` }}</view><text>{{ formatDateTime(round.created_at) }}</text></view>
            <view v-if="round.feedback" class="feedback"><text>调整意见</text><view>{{ round.feedback }}</view></view>
            <view v-for="(item, index) in round.names" :key="`${round.round_number}-${item.name}`" class="name-card">
              <view class="name-head"><view class="name">{{ item.name }}</view><view :class="['favorite', { active: favoriteId(round.round_number, item.name) }]" @tap="toggleFavorite(round.round_number, index, item.name)">{{ favoriteId(round.round_number, item.name) ? '已收藏' : '收藏' }}</view></view>
              <view class="moral">{{ item.moral }}</view>
              <view class="detail-row"><text>出处</text><view>{{ item.reference }}</view></view>
              <view v-if="item.analysis" class="detail-row"><text>推演</text><view>{{ item.analysis }}</view></view>
              <view v-if="item.domain" class="detail-row"><text>域名</text><view>{{ item.domain }} · {{ item.domain_status }}</view></view>
            </view>
          </view>
        </view>
      </view>

      <view class="actions"><button class="primary" :disabled="regenerating" @tap="regenerate">{{ regenerating ? '正在生成...' : '按原条件重新生成' }}</button><view class="sub-actions"><button @tap="exportItem">导出结果</button><button class="danger" @tap="remove">删除历史</button></view></view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { api } from '../../utils/request.js'
import { safeBack } from '../../utils/navigation.js'

const historyId = ref(''), detail = ref(null), loading = ref(true), regenerating = ref(false), favoriteMap = ref({})

onLoad(options => { historyId.value = options.id || ''; load() })

async function load() {
  if (!historyId.value) return back()
  loading.value = true
  try {
    const [history, favorites] = await Promise.all([api.historyDetail(historyId.value), api.favorites({ page: 1, pageSize: 100 })])
    detail.value = history
    const map = {}
    favorites.items.filter(item => item.source_session_id === historyId.value).forEach(item => { map[`${item.source_round_number}-${item.name}`] = item.id })
    favoriteMap.value = map
  } catch (e) { toast(e.message) }
  finally { loading.value = false }
}
function favoriteId(round, name) { return favoriteMap.value[`${round}-${name}`] }
async function toggleFavorite(round, index, name) {
  const key = `${round}-${name}`, id = favoriteMap.value[key]
  try {
    if (id) { await api.deleteFavorite(id); const next = { ...favoriteMap.value }; delete next[key]; favoriteMap.value = next; toast('已移出收藏') }
    else { const result = await api.addFavorite({ session_id: historyId.value, round_number: round, name_index: index }); favoriteMap.value = { ...favoriteMap.value, [key]: result.id }; uni.showToast({ title: '已加入收藏', icon: 'success' }) }
  } catch (e) { toast(e.message) }
}
async function regenerate() { if (regenerating.value) return; regenerating.value = true; try { const result = await api.regenerateHistory(historyId.value); uni.showToast({ title: '已生成新方案' }); setTimeout(() => uni.navigateTo({ url: `/pages/history/detail?id=${result.thread_id}` }), 500) } catch (e) { toast(e.message) } finally { regenerating.value = false } }
function exportItem() { uni.showActionSheet({ itemList: ['导出 JSON', '导出 CSV'], success: ({ tapIndex }) => exportFile(tapIndex === 0 ? 'json' : 'csv') }) }
async function exportFile(format) { uni.showLoading({ title: '正在导出' }); try { const path = await api.downloadHistory(historyId.value, format); uni.hideLoading(); uni.openDocument({ filePath: path, showMenu: true, fail: () => toast('文件已导出，请在下载记录中查看') }) } catch (e) { uni.hideLoading(); toast(e.message) } }
function remove() { uni.showModal({ title: '删除起名历史', content: '收藏的名字不会受到影响，确定删除吗？', confirmColor: '#a84f44', success: async ({ confirm }) => { if (!confirm) return; try { await api.deleteHistory(historyId.value); uni.showToast({ title: '历史已删除' }); setTimeout(() => safeBack('/pages/history/history'), 500) } catch (e) { toast(e.message) } } }) }
function formatDate(value) { const d = new Date(value); return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日` }
function formatDateTime(value) { const d = new Date(value); return `${d.getMonth() + 1}月${d.getDate()}日 ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}` }
function toast(title) { uni.showToast({ title, icon: 'none', duration: 2800 }) }
function back() { safeBack('/pages/history/history') }
</script>

<style scoped>
.page{min-height:100vh;background:#f4f0e8;color:#29312d}.safe{height:var(--status-bar-height)}.topbar{height:130rpx;display:flex;align-items:center;padding:0 34rpx;border-bottom:1px solid rgba(47,59,51,.1)}.back,.spacer{width:76rpx}.back{font-size:58rpx;color:#315c4c}.top-title{flex:1;text-align:center;font-size:34rpx;font-weight:650}.eyebrow{display:block;font-size:16rpx;letter-spacing:3rpx;color:#a76d3c;margin-bottom:4rpx}.loading{min-height:600rpx;display:flex;align-items:center;justify-content:center;color:#858981;font-size:25rpx}.content{width:100%;max-width:900px;padding:34rpx 28rpx 90rpx;margin:auto}.overview{padding:34rpx;background:linear-gradient(140deg,#315c4c,#496f60);border-radius:27rpx;color:#fff;box-shadow:0 16rpx 38rpx rgba(49,92,76,.18)}.overview-top{display:flex;justify-content:space-between;align-items:center}.category{padding:6rpx 14rpx;border-radius:100rpx;background:rgba(255,255,255,.15);font-size:19rpx}.date{color:#d5e0da;font-size:20rpx}.overview-title{font:600 42rpx serif;margin:25rpx 0 18rpx}.conditions{display:flex;flex-wrap:wrap;gap:10rpx}.conditions text{padding:8rpx 14rpx;border-radius:10rpx;background:rgba(255,255,255,.1);font-size:20rpx;color:#edf3ef}.retention{margin-top:21rpx;color:#c9d9d1;font-size:19rpx}.timeline{margin-top:34rpx}.round-block{display:flex;gap:20rpx}.timeline-side{width:58rpx;display:flex;flex-direction:column;align-items:center}.round-dot{flex:none;width:52rpx;height:52rpx;border-radius:50%;background:#a5754d;color:#fff;display:flex;align-items:center;justify-content:center;font:600 23rpx serif;box-shadow:0 0 0 8rpx #eee5da}.timeline-line{width:2rpx;flex:1;min-height:50rpx;background:#ddd6cc}.round-block:last-child .timeline-line{background:transparent}.round-content{flex:1;min-width:0;padding-bottom:36rpx}.round-head{height:54rpx;display:flex;align-items:center;justify-content:space-between}.round-title{font-size:28rpx;font-weight:650}.round-head text{color:#a5a49d;font-size:19rpx}.feedback{margin:18rpx 0;padding:20rpx 22rpx;border-left:5rpx solid #a5754d;border-radius:0 14rpx 14rpx 0;background:#eee7dd}.feedback text{display:block;color:#9a6b43;font-size:18rpx;margin-bottom:7rpx}.feedback view{color:#5e625d;font-size:22rpx;line-height:1.6}.name-card{margin-top:16rpx;padding:27rpx;background:rgba(255,255,255,.78);border-radius:21rpx;box-shadow:0 12rpx 36rpx rgba(66,61,50,.055)}.name-head{display:flex;align-items:center;justify-content:space-between}.name{font:600 39rpx serif;letter-spacing:6rpx;color:#294136}.favorite{padding:8rpx 16rpx;border:1px solid #dac5ab;border-radius:100rpx;color:#9a6a3e;font-size:19rpx}.favorite.active{background:#f0e3d5;color:#89552f}.moral{margin:15rpx 0;color:#5f655f;font-size:23rpx;line-height:1.7}.detail-row{display:flex;gap:16rpx;margin-top:8rpx;color:#81847e;font-size:20rpx;line-height:1.6}.detail-row text{flex:none;color:#a16f48}.actions{margin-left:78rpx;padding-top:8rpx}.primary{height:90rpx;line-height:90rpx;border-radius:17rpx;background:#315c4c;color:#fff;font-size:26rpx}.sub-actions{display:flex;gap:14rpx;margin-top:14rpx}.sub-actions button{flex:1;height:78rpx;line-height:78rpx;border-radius:15rpx;background:#fff;color:#53685e;font-size:23rpx}.sub-actions .danger{color:#a05448;background:#f5e9e5}@media(max-width:480px){.topbar{height:112rpx;padding:0 20rpx}.back,.spacer{width:58rpx}.top-title{font-size:30rpx}.content{padding:24rpx 16rpx 65rpx}.overview{padding:28rpx 24rpx}.round-block{gap:12rpx}.timeline-side{width:48rpx}.round-dot{width:44rpx;height:44rpx}.round-content{padding-bottom:28rpx}.round-head{height:46rpx}.round-head text{display:none}.name-card{padding:23rpx 20rpx}.name{font-size:35rpx}.actions{margin-left:60rpx}.sub-actions{flex-direction:column}.sub-actions button{width:100%;margin:0}}
</style>
