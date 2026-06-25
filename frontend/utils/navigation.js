export function safeBack(fallbackUrl = '/pages/index/index') {
  const pages = typeof getCurrentPages === 'function' ? getCurrentPages() : []
  if (pages.length > 1) {
    return uni.navigateBack()
  }
  return uni.navigateTo({
    url: fallbackUrl,
    fail: () => uni.reLaunch({ url: fallbackUrl })
  })
}

export function goHome() {
  return uni.reLaunch({ url: '/pages/index/index' })
}
