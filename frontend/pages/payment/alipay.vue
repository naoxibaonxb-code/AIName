<template>
  <view class="page"><view class="safe" />
    <view class="topbar"><view class="back" @tap="back">‹</view><view class="top-title"><text class="eyebrow">SANDBOX PAY</text><view>支付宝沙箱支付</view></view><view class="spacer" /></view>
    <view class="content">
      <view class="notice">
        <text class="notice-title">沙箱权益</text>
        <text class="notice-text">支付宝沙箱支付 0.01 元可购买 1 次生成机会。仅用于实验环境，支付成功后自动发放到当前账号。</text>
      </view>

      <view class="card">
        <view class="card-head"><view><text class="card-index">01</text><text class="card-title">购买生成机会</text></view><text class="card-note">1 次 / 0.01 元</text></view>
        <view class="sku"><view><text class="sku-title">AIName 生成机会</text><text class="sku-sub">免费额度用完后自动消耗</text></view><text class="sku-price">¥0.01</text></view>
        <button class="primary" :disabled="creating" @tap="createOrder">{{ creating ? '创建中...' : '购买并打开沙箱收银台' }}</button>
      </view>

      <view v-if="currentOrder" class="card">
        <view class="card-head"><view><text class="card-index">02</text><text class="card-title">当前订单</text></view><text :class="['status', currentOrder.status]">{{ statusText(currentOrder.status, currentOrder) }}</text></view>
        <view class="order-row"><text>商户订单号</text><view>{{ currentOrder.out_trade_no }}</view></view>
        <view class="order-row"><text>支付宝交易号</text><view>{{ currentOrder.trade_no || '等待回调' }}</view></view>
        <view class="order-row"><text>金额</text><view>{{ currentOrder.total_amount }} 元</view></view>
        <view class="order-row"><text>发放权益</text><view>{{ currentOrder.benefit_granted_at ? `${currentOrder.credit_amount || 1} 次已发放` : '等待支付成功' }}</view></view>
        <button class="ghost" :disabled="checking" @tap="refreshOrder">{{ checking ? '刷新中...' : '刷新订单状态' }}</button>
      </view>

      <view class="card">
        <view class="card-head"><view><text class="card-index">03</text><text class="card-title">最近订单</text></view><text class="card-note">最多 10 条</text></view>
        <view v-if="!orders.length" class="empty">暂无沙箱订单</view>
        <view v-for="item in orders" :key="item.out_trade_no" class="order-item" @tap="currentOrder = item">
          <view><text class="order-title">{{ item.subject }}</text><text class="order-no">{{ item.out_trade_no }}</text></view>
          <view class="order-side"><text>{{ item.total_amount }} 元</text><text :class="['status', item.status]">{{ statusText(item.status, item) }}</text></view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { api } from '../../utils/request.js'
import { safeBack } from '../../utils/navigation.js'

const form = reactive({ subject: 'AIName 生成机会 x1', total_amount: '0.01' })
const orders = ref([]), currentOrder = ref(null), creating = ref(false), checking = ref(false)

onLoad(loadOrders)

async function createOrder() {
  const amount = Number(form.total_amount)
  if (!form.subject) return toast('请填写订单标题')
  if (!amount || amount <= 0) return toast('请输入有效金额')
  creating.value = true
  try {
    const result = await api.createAlipaySandboxOrder({ subject: form.subject, total_amount: amount.toFixed(2) })
    currentOrder.value = result.order
    await loadOrders()
    openPayUrl(result.pay_url)
  } catch (e) { toast(e.message) }
  finally { creating.value = false }
}

function openPayUrl(url) {
  // #ifdef H5
  const payWindow = window.open(url, '_blank')
  if (!payWindow) window.location.href = url
  // #endif
  // #ifndef H5
  uni.setClipboardData({
    data: url,
    success: () => uni.showModal({
      title: '支付链接已复制',
      content: '当前端暂不直接打开外部网页，请在浏览器中粘贴打开支付宝沙箱收银台。',
      showCancel: false,
      confirmColor: '#315c4c'
    })
  })
  // #endif
}

async function refreshOrder() {
  if (!currentOrder.value?.out_trade_no) return
  checking.value = true
  try {
    currentOrder.value = await api.alipaySandboxOrder(currentOrder.value.out_trade_no)
    await loadOrders()
    uni.showToast({ title: currentOrder.value.benefit_granted_at ? '权益已到账' : '状态已刷新', icon: 'none' })
  } catch (e) { toast(e.message) }
  finally { checking.value = false }
}

async function loadOrders() {
  try { orders.value = await api.alipaySandboxOrders() }
  catch (e) { orders.value = [] }
}

function statusText(status, item = null) {
  if (item?.benefit_granted_at) return '已发放'
  return ({ created: '已创建', waiting: '待支付', paid: '已支付', finished: '已完成', closed: '已关闭' })[status] || status
}
function toast(message) { uni.showToast({ title: message, icon: 'none', duration: 2800 }) }
function back() { safeBack('/pages/profile/profile') }
</script>

<style scoped>
.page{min-height:100vh;background:#f4f0e8;color:#29312d}.safe{height:var(--status-bar-height)}
.topbar{height:130rpx;display:flex;align-items:center;padding:0 34rpx;border-bottom:1px solid rgba(47,59,51,.1)}.back,.spacer{width:76rpx}.back{font-size:58rpx;color:#315c4c}.top-title{flex:1;text-align:center;font-size:34rpx;font-weight:650}.eyebrow{display:block;font-size:16rpx;letter-spacing:3rpx;color:#a76d3c;margin-bottom:4rpx}
.content{width:100%;max-width:880px;padding:34rpx 28rpx 80rpx;margin:auto}.notice{padding:26rpx 28rpx;border:1px solid #e3d1bd;border-radius:22rpx;background:#fbf3e9}.notice-title,.notice-text{display:block}.notice-title{font-size:27rpx;font-weight:700;color:#9a6b43}.notice-text{margin-top:8rpx;color:#756f67;font-size:22rpx;line-height:1.6}
.card{margin-top:26rpx;padding:34rpx 30rpx;border-radius:26rpx;background:rgba(255,255,255,.76);box-shadow:0 14rpx 44rpx rgba(66,61,50,.07)}.card-head{display:flex;align-items:center;justify-content:space-between;gap:18rpx;margin-bottom:28rpx}.card-index{color:#b97a49;font:italic 20rpx serif;margin-right:14rpx}.card-title{font-size:29rpx;font-weight:650}.card-note{font-size:20rpx;color:#9a9b94}
.field{margin-bottom:24rpx}.label{display:block;font-size:24rpx;font-weight:600;margin-bottom:13rpx}.input{box-sizing:border-box;width:100%;height:86rpx;padding:0 23rpx;background:#f5f4ef;border:1px solid #e1dfd7;border-radius:15rpx;font-size:26rpx}.sku{display:flex;align-items:center;justify-content:space-between;gap:20rpx;margin-bottom:28rpx;padding:25rpx 26rpx;border:1px solid #d9e4de;border-radius:18rpx;background:#eff5f1}.sku-title,.sku-sub{display:block}.sku-title{font-size:28rpx;font-weight:700;color:#315c4c}.sku-sub{margin-top:7rpx;color:#737b75;font-size:21rpx}.sku-price{font:700 42rpx serif;color:#9a6b43;white-space:nowrap}.primary,.ghost{width:100%;height:88rpx;line-height:88rpx;border-radius:16rpx;font-size:26rpx}.primary{background:#315c4c;color:#fff}.ghost{margin-top:24rpx;background:#e4ece7;color:#315c4c}
.order-row,.order-item{display:flex;justify-content:space-between;gap:20rpx}.order-row{padding:17rpx 0;border-top:1px solid #e8e5dd;color:#777;font-size:22rpx}.order-row view{flex:1;text-align:right;overflow-wrap:anywhere;color:#29312d}.order-item{align-items:center;padding:22rpx 0;border-top:1px solid #e8e5dd}.order-title,.order-no,.order-side text{display:block}.order-title{font-size:24rpx;font-weight:650}.order-no{margin-top:6rpx;color:#999;font-size:19rpx}.order-side{text-align:right}.order-side text:first-child{font-size:22rpx;color:#6d716c;margin-bottom:7rpx}.status{flex:none;padding:7rpx 14rpx;border-radius:100rpx;background:#eee8df;color:#9a6b43;font-size:19rpx}.status.paid,.status.finished{background:#dcebe2;color:#397155}.status.closed{background:#f3dfdb;color:#a04c42}.empty{text-align:center;color:#999;padding:44rpx 0;font-size:23rpx}
@media(max-width:480px){.topbar{height:112rpx;padding:0 20rpx}.back,.spacer{width:58rpx}.top-title{font-size:30rpx}.content{padding:24rpx 16rpx 60rpx}.card{padding:28rpx 22rpx}.card-head{align-items:flex-start}.order-row{flex-direction:column}.order-row view{text-align:left}.order-item{align-items:flex-start}.order-side{flex:none}}
</style>
