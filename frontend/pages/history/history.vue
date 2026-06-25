<template>
  <view class="page"><view class="safe" />
    <view class="topbar"><view class="back" @tap="back">‹</view><view class="top-title"><text class="eyebrow">MY INSPIRATION</text><view>历史与收藏</view></view><view class="spacer" /></view>
    <view class="content">
      <view class="tabs"><view :class="['tab', { active: tab === 'history' }]" @tap="switchTab('history')">起名历史<text v-if="historyTotal">{{ historyTotal }}</text></view><view :class="['tab', { active: tab === 'favorites' }]" @tap="switchTab('favorites')">我的收藏<text v-if="favoriteTotal">{{ favoriteTotal }}</text></view></view>

      <view v-if="tab === 'history'" class="filters"><view v-for="item in categories" :key="item.value" :class="['filter', { active: category === item.value }]" @tap="filterCategory(item.value)">{{ item.label }}</view></view>

      <view v-if="loading" class="empty"><view class="empty-mark">名</view><text>正在整理你的灵感...</text></view>

      <template v-else-if="tab === 'history'">
        <view v-if="!histories.length" class="empty"><view class="empty-mark document"><view class="document-sheet"><view class="document-line long" /><view class="document-line" /><view class="document-line short" /></view></view><text>还没有起名记录</text><text class="empty-tip">完成一次起名后，结果会自动保存在这里</text><button class="empty-btn" @tap="goNaming">开始起名</button></view>
        <view v-for="item in histories" :key="item.id" class="history-card" @tap="openDetail(item.id)">
          <view class="card-top"><view><text class="category">{{ item.category }}</text><text class="date">{{ formatDate(item.updated_at) }}</text></view><text class="round">{{ item.round_count }} 轮灵感</text></view>
          <view class="conditions">{{ conditionText(item.conditions) }}</view>
          <view class="names"><text v-for="name in item.latest_names" :key="name.name">{{ name.name }}</text></view>
          <view class="card-foot"><text class="expires">保留至 {{ formatShortDate(item.expires_at) }}</text><view class="actions"><text @tap.stop="exportItem(item.id)">导出</text><text @tap.stop="regenerate(item.id)">再生成</text><text class="danger" @tap.stop="removeHistory(item.id)">删除</text></view></view>
        </view>
      </template>

      <template v-else>
        <view v-if="!favorites.length" class="empty"><view class="empty-mark warm">藏</view><text>还没有收藏名字</text><text class="empty-tip">在起名结果中点击“收藏”，好名字就会留在这里</text></view>
        <view v-for="item in favorites" :key="item.id" class="favorite-card">
          <view class="favorite-main"><view class="favorite-name">{{ item.name }}</view><text class="favorite-category">{{ item.category }}</text></view>
          <view class="favorite-moral">{{ item.snapshot.moral }}</view>
          <view class="favorite-detail"><text>出处</text><view>{{ item.snapshot.reference }}</view></view>
          <view v-if="item.snapshot.analysis" class="favorite-detail"><text>推演</text><view>{{ item.snapshot.analysis }}</view></view>
          <view v-if="item.snapshot.domain" class="favorite-detail"><text>域名</text><view>{{ item.snapshot.domain }}</view></view>
          <view class="favorite-foot"><text>{{ formatDate(item.created_at) }}</text><view class="favorite-actions"><text @tap="exportFavorite(item)">导出</text><text class="remove-favorite" @tap="removeFavorite(item.id)">移出收藏</text></view></view>
        </view>
      </template>

      <button v-if="hasMore && !loading" class="more" @tap="loadMore">加载更多</button>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { api } from '../../utils/request.js'
import { safeBack } from '../../utils/navigation.js'

const categories = [{ label: '全部', value: '' }, { label: '人名', value: '人名' }, { label: '企业名', value: '企业名' }, { label: '宠物名', value: '宠物名' }, { label: '虚拟IP', value: '虚拟IP' }]
const tab = ref('history'), category = ref(''), histories = ref([]), favorites = ref([]), loading = ref(false)
const historyTotal = ref(0), favoriteTotal = ref(0), page = ref(1), hasMore = ref(false)
const pageSize = 10

onLoad(options => { if (options?.tab === 'favorites') tab.value = 'favorites' })
onShow(() => refresh())

async function refresh() { page.value = 1; histories.value = []; favorites.value = []; await load() }
async function load() {
  loading.value = true
  try {
    if (tab.value === 'history') {
      const res = await api.history({ category: category.value, page: page.value, pageSize })
      histories.value = page.value === 1 ? res.items : [...histories.value, ...res.items]
      historyTotal.value = res.total
      hasMore.value = histories.value.length < res.total
    } else {
      const res = await api.favorites({ page: page.value, pageSize })
      favorites.value = page.value === 1 ? res.items : [...favorites.value, ...res.items]
      favoriteTotal.value = res.total
      hasMore.value = favorites.value.length < res.total
    }
  } catch (e) { toast(e.message) }
  finally { loading.value = false }
}
function switchTab(value) { if (tab.value === value) return; tab.value = value; refresh() }
function filterCategory(value) { if (category.value === value) return; category.value = value; refresh() }
function loadMore() { page.value += 1; load() }
function openDetail(id) { uni.navigateTo({ url: `/pages/history/detail?id=${id}` }) }
function goNaming() { uni.navigateTo({ url: '/pages/index/index', fail: () => uni.reLaunch({ url: '/pages/index/index' }) }) }
function back() { safeBack('/pages/index/index') }
function conditionText(value) {
  return [
    value.surname ? `姓氏 ${value.surname}` : '',
    value.gender !== '不限' ? value.gender : '',
    value.length !== '不限' ? value.length : '',
    value.use_bazi ? '八字五行' : '',
    value.brand_tone ? `调性 ${value.brand_tone}` : '',
    value.target_audience ? `客群 ${value.target_audience}` : '',
    value.ip_setting ? '含角色设定' : '',
    value.other || ''
  ].filter(Boolean).join(' · ') || '未设置额外条件'
}
function formatDate(value) { const d = new Date(value); return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}` }
function formatShortDate(value) { const d = new Date(value); return `${d.getMonth() + 1}月${d.getDate()}日` }
function toast(title) { uni.showToast({ title, icon: 'none', duration: 2800 }) }
function removeHistory(id) { uni.showModal({ title: '删除起名历史', content: '收藏的名字不会受到影响，确定删除吗？', confirmColor: '#a84f44', success: async ({ confirm }) => { if (!confirm) return; try { await api.deleteHistory(id); histories.value = histories.value.filter(item => item.id !== id); historyTotal.value -= 1; toast('历史已删除') } catch (e) { toast(e.message) } } }) }
async function regenerate(id) { uni.showLoading({ title: '重新寻名中', mask: true }); try { const res = await api.regenerateHistory(id); uni.hideLoading(); uni.showToast({ title: '已生成新方案' }); setTimeout(() => uni.navigateTo({ url: `/pages/history/detail?id=${res.thread_id}` }), 500) } catch (e) { uni.hideLoading(); toast(e.message) } }
function exportItem(id) { uni.showActionSheet({ itemList: ['导出 JSON', '导出 CSV'], success: ({ tapIndex }) => exportFile(id, tapIndex === 0 ? 'json' : 'csv') }) }
async function exportFile(id, format) { uni.showLoading({ title: '正在导出' }); try { const path = await api.downloadHistory(id, format); uni.hideLoading(); uni.openDocument({ filePath: path, showMenu: true, fail: () => toast('文件已导出，请在下载记录中查看') }) } catch (e) { uni.hideLoading(); toast(e.message) } }
function exportFavorite(item) {
  const formats = item.category === '企业名'
    ? [{ label: '生成企业命名报告', value: 'report' }]
    : [{ label: '导出 PDF', value: 'pdf' }, { label: '导出图片', value: 'png' }]
  uni.showActionSheet({
    itemList: formats.map(item => item.label),
    success: ({ tapIndex }) => exportFavoriteFile(item, formats[tapIndex].value)
  })
}
async function exportFavoriteFile(item, format) {
  uni.showLoading({ title: '正在导出' })
  try {
    const path = await api.downloadFavorite(item.id, format)
    uni.hideLoading()
    if (format === 'png') {
      return uni.previewImage({ urls: [path], current: path, fail: () => toast('图片已导出，请在下载记录中查看') })
    }
    uni.openDocument({ filePath: path, showMenu: true, fail: () => toast('文件已导出，请在下载记录中查看') })
  } catch (e) {
    uni.hideLoading()
    toast(e.message)
  }
}
function removeFavorite(id) { uni.showModal({ title: '移出收藏', content: '确定不再收藏这个名字吗？', confirmColor: '#a84f44', success: async ({ confirm }) => { if (!confirm) return; try { await api.deleteFavorite(id); favorites.value = favorites.value.filter(item => item.id !== id); favoriteTotal.value -= 1; toast('已移出收藏') } catch (e) { toast(e.message) } } }) }
</script>

<style scoped>
.page{min-height:100vh;background:#f4f0e8;color:#29312d}.safe{height:var(--status-bar-height)}.topbar{height:130rpx;display:flex;align-items:center;padding:0 34rpx;border-bottom:1px solid rgba(47,59,51,.1)}.back,.spacer{width:76rpx}.back{font-size:58rpx;color:#315c4c}.top-title{flex:1;text-align:center;font-size:34rpx;font-weight:650}.eyebrow{display:block;font-size:16rpx;letter-spacing:3rpx;color:#a76d3c;margin-bottom:4rpx}.content{width:100%;max-width:900px;padding:34rpx 28rpx 80rpx;margin:auto}.tabs{display:flex;padding:8rpx;background:#e8e6de;border-radius:18rpx;margin-bottom:28rpx}.tab{flex:1;padding:21rpx;text-align:center;color:#737770;font-size:26rpx;border-radius:14rpx}.tab text{margin-left:10rpx;font-size:19rpx;color:#a27b58}.tab.active{background:#fff;color:#315c4c;font-weight:650;box-shadow:0 5rpx 18rpx rgba(56,63,57,.08)}.filters{display:flex;gap:12rpx;overflow-x:auto;padding:2rpx 0 24rpx}.filter{flex:none;padding:13rpx 25rpx;border:1px solid #d9d7cf;border-radius:100rpx;color:#777b75;font-size:22rpx}.filter.active{border-color:#315c4c;background:#e4ebe7;color:#315c4c}.history-card,.favorite-card{margin-bottom:22rpx;padding:30rpx;background:rgba(255,255,255,.77);border-radius:24rpx;box-shadow:0 14rpx 44rpx rgba(66,61,50,.065)}.history-card:active{transform:scale(.992)}.card-top,.card-foot,.favorite-main,.favorite-foot{display:flex;align-items:center;justify-content:space-between;gap:18rpx}.category{padding:6rpx 14rpx;border-radius:100rpx;background:#e1ebe5;color:#315c4c;font-size:19rpx}.date{margin-left:14rpx;color:#9b9b94;font-size:20rpx}.round{color:#a16f48;font-size:21rpx}.conditions{margin:22rpx 0 16rpx;color:#7b7d77;font-size:22rpx;line-height:1.6}.names{display:flex;flex-wrap:wrap;gap:12rpx}.names text{padding:12rpx 18rpx;background:#f4f2ec;border-radius:12rpx;color:#34463e;font:600 27rpx serif}.card-foot{margin-top:25rpx;padding-top:22rpx;border-top:1px solid #e9e6de}.expires{color:#aaa79f;font-size:19rpx}.actions{display:flex;gap:25rpx;color:#527264;font-size:21rpx}.actions .danger{color:#a05448}.favorite-main{justify-content:flex-start}.favorite-name{font:600 42rpx serif;letter-spacing:5rpx;color:#294136}.favorite-category{padding:5rpx 13rpx;border-radius:100rpx;background:#eee8df;color:#9a6b43;font-size:18rpx}.favorite-moral{margin:18rpx 0;color:#5e655f;font-size:24rpx;line-height:1.75}.favorite-detail{display:flex;gap:18rpx;margin-top:10rpx;color:#7f827c;font-size:21rpx;line-height:1.6}.favorite-detail>text{flex:none;color:#a16f48}.favorite-foot{margin-top:23rpx;padding-top:18rpx;border-top:1px solid #e8e5dd;color:#aaa69e;font-size:19rpx}.remove-favorite{color:#a05448}.empty{min-height:480rpx;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#6f746e;font-size:27rpx}.empty-mark{width:88rpx;height:88rpx;border-radius:28rpx;background:#315c4c;color:#fff;display:flex;align-items:center;justify-content:center;font:600 38rpx serif;margin-bottom:24rpx}.empty-mark.warm{background:#a16f48}.empty-tip{max-width:500rpx;margin-top:12rpx;text-align:center;color:#999b95;font-size:21rpx;line-height:1.6}.empty-btn,.more{height:76rpx;line-height:76rpx;padding:0 35rpx;border-radius:15rpx;background:#315c4c;color:#fff;font-size:23rpx}.empty-btn{margin-top:28rpx}.more{width:260rpx;margin:30rpx auto 0;background:#e2eae5;color:#315c4c}@media(max-width:480px){.topbar{height:112rpx;padding:0 20rpx}.back,.spacer{width:58rpx}.top-title{font-size:30rpx}.content{padding:24rpx 16rpx 60rpx}.history-card,.favorite-card{padding:25rpx 22rpx}.card-top{align-items:flex-start}.card-top>view{display:flex;flex-direction:column;align-items:flex-start;gap:7rpx}.date{margin-left:0}.card-foot{align-items:flex-start;flex-direction:column}.actions{align-self:stretch;justify-content:space-between}.favorite-name{font-size:37rpx}}
.empty-mark.document{background:#e2ebe6;box-shadow:inset 0 0 0 1px rgba(49,92,76,.08)}
.document-sheet{box-sizing:border-box;width:43rpx;height:52rpx;padding:10rpx 8rpx;border:3rpx solid #315c4c;border-radius:7rpx;background:rgba(255,255,255,.35)}
.document-line{width:20rpx;height:3rpx;margin-top:6rpx;border-radius:10rpx;background:#6e8e80}
.document-line:first-child{margin-top:0}.document-line.long{width:23rpx;background:#315c4c}.document-line.short{width:14rpx}
.favorite-actions{display:flex;gap:24rpx;color:#527264}
@media(max-width:480px){.favorite-foot{align-items:flex-start;flex-direction:column}.favorite-actions{align-self:stretch;justify-content:space-between}}
</style>
