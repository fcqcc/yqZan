const app = getApp()

// 请求封装
function request(url, method = 'GET', data = {}) {
  return new Promise((resolve, reject) => {
    const token = app.globalData.token || wx.getStorageSync('token')
    const header = { 'Content-Type': 'application/json' }
    if (token) header['Authorization'] = 'Bearer ' + token

    wx.request({
      url: app.globalData.baseUrl + url,
      method,
      data,
      header,
      success(res) {
        if (res.statusCode === 401) {
          // token过期，跳转登录
          wx.removeStorageSync('token')
          wx.removeStorageSync('userInfo')
          wx.reLaunch({ url: '/pages/login/login' })
          return
        }
        if (res.statusCode >= 400) {
          reject(res.data)
        } else {
          resolve(res.data)
        }
      },
      fail(err) {
        reject(err)
      }
    })
  })
}

// ===== 用户 =====
const register = (data) => request('/api/register', 'POST', data)
const login = (data) => request('/api/login', 'POST', data)
const getMe = () => request('/api/me')
const getPartner = () => request('/api/partner')
const bindPartner = (inviteCode) => request('/api/bind', 'POST', { invite_code: inviteCode })
const unbindPartner = () => request('/api/unbind', 'POST')

// ===== 计划 =====
const getPlans = () => request('/api/plans')
const createPlan = (data) => request('/api/plans', 'POST', data)
const deletePlan = (id) => request('/api/plans/' + id, 'DELETE')
const deliverPlan = (id, amount, note) => request('/api/plans/' + id + '/deliver', 'POST', { amount, note })

// ===== 心愿 =====
const getWishes = () => request('/api/wishes')
const createWish = (data) => request('/api/wishes', 'POST', data)
const updateWish = (id, data) => request('/api/wishes/' + id, 'PUT', data)
const deleteWish = (id) => request('/api/wishes/' + id, 'DELETE')

// ===== 要做的事 =====
const getTodos = () => request('/api/todos')
const createTodo = (data) => request('/api/todos', 'POST', data)
const checkinTodo = (id) => request('/api/todos/' + id + '/checkin', 'POST')
const deleteTodo = (id) => request('/api/todos/' + id, 'DELETE')

// ===== 纪念日 =====
const getAnniversaries = () => request('/api/anniversaries')
const createAnniversary = (data) => request('/api/anniversaries', 'POST', data)
const deleteAnniversary = (id) => request('/api/anniversaries/' + id, 'DELETE')

// ===== 礼物 =====
const getGifts = () => request('/api/gifts')
const createGift = (data) => request('/api/gifts', 'POST', data)
const deleteGift = (id) => request('/api/gifts/' + id, 'DELETE')

// ===== 便利贴 =====
const getNotes = () => request('/api/notes')
const createNote = (content) => request('/api/notes', 'POST', { content })
const likeNote = (id) => request('/api/notes/' + id + '/like', 'POST')
const deleteNote = (id) => request('/api/notes/' + id, 'DELETE')

// ===== 等级 =====
const getLevel = () => request('/api/level')
const getLevelLogs = () => request('/api/level/logs')

// ===== 贺卡 =====
const getCardTemplates = () => request('/api/card/templates')
const getCardSnapshot = () => request('/api/card/snapshot')
const generateCard = (data) => request('/api/card/generate', 'POST', data)
const getCards = () => request('/api/cards')


// ===== 任务 =====
const getTasks = () => request('/api/tasks')
const getTaskEvents = () => request('/api/tasks/events')
const createTask = (data) => request('/api/tasks', 'POST', data)
const acceptTaskEvent = (eventCode) => request('/api/tasks/accept', 'POST', { event_code: eventCode })
const verifyTask = (id) => request('/api/tasks/' + id + '/verify', 'POST')
const deleteTask = (id) => request('/api/tasks/' + id, 'DELETE')

module.exports = {
  register, login, getMe, getPartner, bindPartner, unbindPartner,
  getPlans, createPlan, deletePlan, deliverPlan,
  getWishes, createWish, updateWish, deleteWish,
  getTodos, createTodo, checkinTodo, deleteTodo,
  getAnniversaries, createAnniversary, deleteAnniversary,
  getGifts, createGift, deleteGift,
  getNotes, createNote, likeNote, deleteNote,
  getLevel, getLevelLogs,
  getCardTemplates, getCardSnapshot, generateCard, getTasks, getTaskEvents, createTask, acceptTaskEvent, verifyTask, deleteTask,
  getCards
}
