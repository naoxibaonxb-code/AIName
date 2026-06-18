<template>
  <view class="page"><view class="safe" /><view class="wrap">
    <view class="brand"><view class="seal">名</view><text class="brand-name">知名</text></view>
    <text class="eyebrow">AI NAMING STUDIO</text><view class="title">好名字，<br>从一次灵感开始</view>
    <view class="subtitle">登录后开启你的专属起名之旅</view>
    <view class="form">
      <view class="field"><text class="label">邮箱</text><input v-model.trim="form.email" class="input" type="text" placeholder="请输入邮箱地址" /></view>
      <view class="field"><text class="label">密码</text><input v-model="form.password" class="input" password placeholder="请输入密码" /></view>
      <button class="primary" :disabled="loading" @tap="submit">{{ loading ? '登录中...' : '登录' }}</button>
    </view>
    <view class="switch">还没有账号？<text class="link" @tap="toRegister">立即注册</text></view>
  </view></view>
</template>
<script setup>
import { reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { api } from '../../utils/request.js'
const form = reactive({ email: '', password: '' })
const loading = ref(false)
const emailOk = (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)
onLoad(() => {
  if (uni.getStorageSync('token')) uni.reLaunch({ url: '/pages/index/index' })
})
async function submit() {
  if (!emailOk(form.email)) return uni.showToast({ title: '请输入正确的邮箱', icon: 'none' })
  if (form.password.length < 6) return uni.showToast({ title: '密码至少 6 位', icon: 'none' })
  loading.value = true
  try {
    const res = await api.login(form)
    uni.setStorageSync('token', res.token); uni.setStorageSync('user', res.user)
    uni.reLaunch({ url: '/pages/index/index' })
  } catch (e) { uni.showToast({ title: e.message, icon: 'none' }) }
  finally { loading.value = false }
}
function toRegister() { uni.navigateTo({ url: '/pages/register/register' }) }
</script>
<style src="../../styles/auth.css"></style>
