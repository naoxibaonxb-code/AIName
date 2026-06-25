import { API_BASE_URL } from '../config.js'

function errorMessage(body, fallback) {
  const detail = body?.detail || body?.message
  if (Array.isArray(detail)) {
    return detail.map(item => item?.msg).filter(Boolean).join('；') || fallback
  }
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object') return detail.message || fallback
  return fallback
}

function uploadKnowledge(filePath, onProgress, scope = 'private') {
  const token = uni.getStorageSync('token')
  return new Promise((resolve, reject) => {
    const task = uni.uploadFile({
      url: `${API_BASE_URL}/knowledge/upload?scope=${encodeURIComponent(scope)}`,
      filePath,
      name: 'file',
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success: ({ statusCode, data }) => {
        let body
        try { body = typeof data === 'string' ? JSON.parse(data) : data }
        catch { return reject(new Error('服务器返回了无法识别的数据')) }
        if (statusCode >= 200 && statusCode < 300) return resolve(body)
        reject(new Error(errorMessage(body, '文件上传失败，请稍后重试')))
      },
      fail: ({ errMsg = '' }) => reject(new Error(
        /timeout/i.test(errMsg) ? '上传超时，请稍后重试' : '文件上传失败，请检查网络'
      ))
    })
    if (task?.onProgressUpdate && onProgress) {
      task.onProgressUpdate(({ progress }) => onProgress(progress))
    }
  })
}

function downloadHistory(historyId, format) {
  const token = uni.getStorageSync('token')
  return new Promise((resolve, reject) => {
    uni.downloadFile({
      url: `${API_BASE_URL}/name/history/${historyId}/export?format=${format}`,
      header: token ? { Authorization: `Bearer ${token}` } : {},
      timeout: 30000,
      success: ({ statusCode, tempFilePath }) => {
        if (statusCode >= 200 && statusCode < 300) return resolve(tempFilePath)
        reject(new Error('导出失败，请稍后重试'))
      },
      fail: () => reject(new Error('导出失败，请检查网络'))
    })
  })
}

function downloadFavorite(favoriteId, format) {
  const token = uni.getStorageSync('token')
  return new Promise((resolve, reject) => {
    uni.downloadFile({
      url: `${API_BASE_URL}/name/favorites/${favoriteId}/export?format=${format}`,
      header: token ? { Authorization: `Bearer ${token}` } : {},
      timeout: 30000,
      success: ({ statusCode, tempFilePath }) => {
        if (statusCode >= 200 && statusCode < 300) return resolve(tempFilePath)
        reject(new Error('收藏方案导出失败，请稍后重试'))
      },
      fail: () => reject(new Error('收藏方案导出失败，请检查网络'))
    })
  })
}

export function request({ url, method = 'GET', data, auth = false, timeout = 30000, failureMessage = '' }) {
  const token = uni.getStorageSync('token')
  const header = { 'Content-Type': 'application/json' }
  if (auth && token) header.Authorization = `Bearer ${token}`

  return new Promise((resolve, reject) => {
    uni.request({
      url: `${API_BASE_URL}${url}`,
      method,
      data,
      header,
      timeout,
      success: ({ statusCode, data: body }) => {
        if (statusCode >= 200 && statusCode < 300) return resolve(body)
        const message = errorMessage(body, '请求失败，请稍后再试')
        const authExpired = statusCode === 401 || (
          statusCode === 403 && /Token|Access Token|账号已被禁用/.test(message)
        )
        if (authExpired) {
          uni.removeStorageSync('token')
          uni.removeStorageSync('user')
          uni.reLaunch({ url: '/pages/login/login' })
        }
        const error = new Error(message)
        error.statusCode = statusCode
        reject(error)
      },
      fail: ({ errMsg = '' }) => {
        const message = failureMessage || (
          /timeout/i.test(errMsg)
            ? '请求超时，请稍后重试'
            : '无法连接服务器，请检查后端地址和网络'
        )
        reject(new Error(message))
      }
    })
  })
}

export const api = {
  sendCode: (email) => request({ url: `/auth/code?email=${encodeURIComponent(email)}` }),
  register: (data) => request({ url: '/auth/register', method: 'POST', data }),
  login: (data) => request({ url: '/auth/login', method: 'POST', data }),
  generate: (data) => request({
    url: '/name/generate',
    method: 'POST',
    data,
    auth: true,
    timeout: 90000,
    failureMessage: '当前访问人数较多，生成服务暂时繁忙，请稍后重新尝试。'
  }),
  feedback: (data) => request({
    url: '/name/feedback',
    method: 'POST',
    data,
    auth: true,
    timeout: 90000,
    failureMessage: '当前访问人数较多，生成服务暂时繁忙，请稍后重新尝试。'
  }),
  quota: () => request({ url: '/name/quota', auth: true }),
  activeAnnouncements: () => request({ url: '/announcements/active' }),
  knowledgeFiles: (scope = 'private') => request({ url: `/knowledge/files?scope=${scope}`, auth: true }),
  knowledgeStats: () => request({ url: '/knowledge/stats', auth: true }),
  updateKnowledgeFile: (fileId, data) => request({ url: `/knowledge/files/${fileId}`, method: 'PATCH', data, auth: true }),
  deleteKnowledgeFile: (fileId) => request({ url: `/knowledge/files/${fileId}`, method: 'DELETE', auth: true }),
  uploadKnowledge,
  history: ({ category = '', page = 1, pageSize = 20 } = {}) => request({
    url: `/name/history?page=${page}&page_size=${pageSize}${category ? `&category=${encodeURIComponent(category)}` : ''}`,
    auth: true
  }),
  historyDetail: (historyId) => request({ url: `/name/history/${historyId}`, auth: true }),
  deleteHistory: (historyId) => request({ url: `/name/history/${historyId}`, method: 'DELETE', auth: true }),
  regenerateHistory: (historyId) => request({
    url: `/name/history/${historyId}/regenerate`,
    method: 'POST',
    auth: true,
    timeout: 90000,
    failureMessage: '当前访问人数较多，生成服务暂时繁忙，请稍后重新尝试。'
  }),
  downloadHistory,
  downloadFavorite,
  favorites: ({ page = 1, pageSize = 20 } = {}) => request({
    url: `/name/favorites?page=${page}&page_size=${pageSize}`,
    auth: true
  }),
  addFavorite: (data) => request({ url: '/name/favorites', method: 'POST', data, auth: true }),
  deleteFavorite: (favoriteId) => request({ url: `/name/favorites/${favoriteId}`, method: 'DELETE', auth: true }),
  userCenter: () => request({ url: '/users/me', auth: true }),
  loginRecords: () => request({ url: '/users/me/login-records', auth: true }),
  updateProfile: (data) => request({ url: '/users/me/profile', method: 'PATCH', data, auth: true }),
  updatePassword: (data) => request({ url: '/users/me/password', method: 'PATCH', data, auth: true }),
  cancelAccount: (data) => request({ url: '/users/me', method: 'DELETE', data, auth: true }),
  adminUsers: ({ search = '', page = 1, pageSize = 20 }) => request({
    url: `/admin/users?search=${encodeURIComponent(search)}&page=${page}&page_size=${pageSize}`,
    auth: true
  }),
  setUserActive: (userId, isActive) => request({
    url: `/admin/users/${userId}/status`,
    method: 'PATCH',
    data: { is_active: isActive },
    auth: true
  }),
  adminUsageSummary: (days = 30) => request({
    url: `/admin/usage/summary?days=${days}`,
    auth: true
  }),
  adminUsageCalls: ({ page = 1, pageSize = 20, userId = '' } = {}) => request({
    url: `/admin/usage/calls?page=${page}&page_size=${pageSize}${userId ? `&user_id=${userId}` : ''}`,
    auth: true
  }),
  adminAnnouncements: ({ page = 1, pageSize = 20 } = {}) => request({
    url: `/admin/announcements?page=${page}&page_size=${pageSize}`,
    auth: true
  }),
  createAnnouncement: (data) => request({ url: '/admin/announcements', method: 'POST', data, auth: true }),
  updateAnnouncement: (id, data) => request({ url: `/admin/announcements/${id}`, method: 'PATCH', data, auth: true }),
  deleteAnnouncement: (id) => request({ url: `/admin/announcements/${id}`, method: 'DELETE', auth: true }),
  createAlipaySandboxOrder: (data) => request({
    url: '/payments/alipay/sandbox/orders',
    method: 'POST',
    data,
    auth: true
  }),
  alipaySandboxOrders: () => request({ url: '/payments/alipay/sandbox/orders', auth: true }),
  alipaySandboxOrder: (outTradeNo) => request({
    url: `/payments/alipay/sandbox/orders/${encodeURIComponent(outTradeNo)}`,
    auth: true
  })
}
