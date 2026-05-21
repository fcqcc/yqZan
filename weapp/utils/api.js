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
          wx.removeStorageSync('token')
          wx.removeStorageSync('userInfo')
          wx.reLaunch({ url: '/pages/login/login' })
          return
        }
        if (res.statusCode >= 400) {
          const err = typeof res.data === 'object' ? (res.data || {}) : { detail: String(res.data || '') }
          // 统一错误信息：从 detail 中提取字符串
          let detail = ''
          if (typeof err.detail === 'string') {
            detail = err.detail
          } else if (Array.isArray(err.detail)) {
            // 422 错误可能是数组，取第一条
            detail = err.detail[0]?.msg || err.detail[0] || '请求参数错误'
          } else if (err.detail && typeof err.detail === 'object') {
            detail = err.detail.msg || JSON.stringify(err.detail)
          }
          err.detail = detail || '请求失败'
          err._statusCode = res.statusCode
          reject(err)
        } else {
          resolve(res.data)
        }
      },
      fail(err) { reject(err) }
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
const deliverPlan = (id, amount, note, extra = {}) =>
  request('/api/plans/' + id + '/deliver', 'POST', { amount, note, ...extra })
/** 存入明细（后端需实现 GET /api/plans/:id/deliveries；失败时前端展示空列表） */
const getPlanDeliveries = (id) => request('/api/plans/' + id + '/deliveries')

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

const importHolidays = (titles) => request('/api/anniversaries/import-holidays', 'POST', { titles })
const getHolidayList = () => request('/api/anniversaries/holiday-list')
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
const stampNote = (id) => request('/api/notes/' + id + '/stamp', 'POST')

// ===== 等级 =====
const getLevel = () => request('/api/level')
const getLevelLogs = () => request('/api/level/logs')
const consumeLevelPending = () => request('/api/level/consume-pending', 'POST')

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

// ===== 计划完成祝贺 =====
const congratulatePlan = (id) => request('/api/plans/' + id + '/congratulate', 'POST')

// ===== 宠物 =====
const getActivePet = () => request('/api/pets/active')
const getPets = () => request('/api/pets')
const switchPet = (petId) => request('/api/pets/switch', 'POST', { pet_id: petId })
const switchPetForm = (petId, form) => request('/api/pets/' + petId + '/form', 'POST', { form })
const feedPet = (petId) => request('/api/pets/' + petId + '/feed', 'POST')
const petPet = (petId) => request('/api/pets/' + petId + '/pet', 'POST')
const walkPet = (petId) => request('/api/pets/' + petId + '/walk', 'POST')
const evolvePet = (petId, itemId) => request('/api/pets/' + petId + '/evolve', 'POST', { item_id: itemId })
const getDailyAdventure = () => request('/api/pets/daily-adventure')
const getPetCatalog = () => request('/api/pets/catalog')
const getGachaPool = () => request('/api/gacha/pool')
const getLevelUnlocks = () => request('/api/level/unlocks')

// ===== 抽卡 =====
const getTickets = () => request('/api/gacha/tickets')
const drawSingle = () => request('/api/gacha/draw', 'POST')
const drawTen = (boost = false) => request('/api/gacha/draw10', 'POST', { boost })
const buyTickets = (amount) => request('/api/gacha/buy-tickets', 'POST', { amount })

// ===== 背包 =====
const getInventory = () => request('/api/pets/inventory')
const useItem = (inventoryId) => request('/api/pets/inventory/use', 'POST', { inventory_id: inventoryId })
const getBestiary = () => request('/api/pets/bestiary')

// ===== 签到 =====
const doCheckin = () => request('/api/checkin', 'POST')
const getCheckinStatus = () => request('/api/checkin/status')
const getSpark = () => request('/api/checkin/spark')

// ===== 成就 =====
// ===== 卡片任务 =====
const useCard = (inventoryId) => request('/api/card-tasks/use', 'POST', { inventory_id: inventoryId })
const getCardTasks = () => request('/api/card-tasks/active')
const completeCardTask = (taskId) => request('/api/card-tasks/' + taskId + '/complete', 'POST')
const declineCardTask = (taskId) => request('/api/card-tasks/' + taskId + '/decline', 'POST')
const confirmCardTask = (taskId) => request('/api/card-tasks/' + taskId + '/confirm', 'POST')
const disputeCardTask = (taskId) => request('/api/card-tasks/' + taskId + '/dispute', 'POST')
const forgiveCardTask = (taskId) => request('/api/card-tasks/' + taskId + '/forgive', 'POST')
const rejectForgive = (taskId) => request('/api/card-tasks/' + taskId + '/reject', 'POST')
const retryForgive = (taskId) => request('/api/card-tasks/' + taskId + '/retry', 'POST')
const dismissCardTask = (taskId) => request('/api/card-tasks/' + taskId + '/dismiss', 'POST')
const getAchievements = () => request('/api/achievements')

module.exports = {
  request, register, login, getMe, getPartner, bindPartner, unbindPartner,
  getPlans, createPlan, deletePlan, deliverPlan, getPlanDeliveries,
  getWishes, createWish, updateWish, deleteWish,
  getTodos, createTodo, checkinTodo, deleteTodo,
  getAnniversaries, createAnniversary, deleteAnniversary, importHolidays, getHolidayList,
  getGifts, createGift, deleteGift,
  getNotes, createNote, likeNote, deleteNote, stampNote,
  getLevel, getLevelLogs, consumeLevelPending,
   getCardTemplates, getCardSnapshot, generateCard, getCards,
   getTasks, getTaskEvents, createTask, acceptTaskEvent, verifyTask, deleteTask,
   congratulatePlan,
  getActivePet, getPets, switchPet, switchPetForm, feedPet, petPet, walkPet, evolvePet, getDailyAdventure,
  getPetCatalog, getGachaPool,
  getLevelUnlocks,
  getTickets, drawSingle, drawTen, buyTickets,
  getInventory, useItem, getBestiary,
  doCheckin, getCheckinStatus, getSpark,
  useCard, getCardTasks, completeCardTask, declineCardTask, confirmCardTask, disputeCardTask,
  forgiveCardTask, rejectForgive, retryForgive, dismissCardTask,
  getAchievements
}
