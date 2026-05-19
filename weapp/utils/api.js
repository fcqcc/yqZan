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
          reject(res.data)
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

// ===== 计划完成祝贺 =====
const congratulatePlan = (id) => request('/api/plans/' + id + '/congratulate', 'POST')

// ===== 宠物 =====
const getActivePet = () => request('/api/pets/active')
const getPets = () => request('/api/pets')
const switchPet = (petId) => request('/api/pets/switch', 'POST', { pet_id: petId })
const switchPetForm = (petId, form) => request('/api/pets/' + petId + '/form', 'POST', { form })
const feedPet = (petId) => request('/api/pets/' + petId + '/feed', 'POST')
const evolvePet = (petId, itemId) => request('/api/pets/' + petId + '/evolve', 'POST', { item_id: itemId })

// ===== 抽卡 =====
const getTickets = () => request('/api/gacha/tickets')
const drawSingle = () => request('/api/gacha/draw', 'POST')
const drawTen = () => request('/api/gacha/draw10', 'POST')
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
const getAchievements = () => request('/api/achievements')

module.exports = {
  register, login, getMe, getPartner, bindPartner, unbindPartner,
  getPlans, createPlan, deletePlan, deliverPlan, getPlanDeliveries,
  getWishes, createWish, updateWish, deleteWish,
  getTodos, createTodo, checkinTodo, deleteTodo,
  getAnniversaries, createAnniversary, deleteAnniversary, importHolidays, getHolidayList,
  getGifts, createGift, deleteGift,
  getNotes, createNote, likeNote, deleteNote,
  getLevel, getLevelLogs,
   getCardTemplates, getCardSnapshot, generateCard, getCards,
   getTasks, getTaskEvents, createTask, acceptTaskEvent, verifyTask, deleteTask,
   congratulatePlan,
  getActivePet, getPets, switchPet, switchPetForm, feedPet, evolvePet,
  getTickets, drawSingle, drawTen, buyTickets,
  getInventory, useItem, getBestiary,
  doCheckin, getCheckinStatus, getSpark,
  getAchievements
}
