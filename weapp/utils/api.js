     1|const app = getApp()
     2|
     3|// 请求封装
     4|function request(url, method = 'GET', data = {}) {
     5|  return new Promise((resolve, reject) => {
     6|    const token = app.globalData.token || wx.getStorageSync('token')
     7|    const header = { 'Content-Type': 'application/json' }
     8|    if (token) header['Authorization'] = 'Bearer ' + token
     9|
    10|    wx.request({
    11|      url: app.globalData.baseUrl + url,
    12|      method,
    13|      data,
    14|      header,
    15|      success(res) {
    16|        if (res.statusCode === 401) {
    17|          // token过期，跳转登录
    18|          wx.removeStorageSync('token')
    19|          wx.removeStorageSync('userInfo')
    20|          wx.reLaunch({ url: '/pages/login/login' })
    21|          return
    22|        }
    23|        if (res.statusCode >= 400) {
    24|          reject(res.data)
    25|        } else {
    26|          resolve(res.data)
    27|        }
    28|      },
    29|      fail(err) {
    30|        reject(err)
    31|      }
    32|    })
    33|  })
    34|}
    35|
    36|// ===== 用户 =====
    37|const register = (data) => request('/api/register', 'POST', data)
    38|const login = (data) => request('/api/login', 'POST', data)
    39|const getMe = () => request('/api/me')
    40|const getPartner = () => request('/api/partner')
    41|const bindPartner = (inviteCode) => request('/api/bind', 'POST', { invite_code: inviteCode })
    42|const unbindPartner = () => request('/api/unbind', 'POST')
    43|
    44|// ===== 计划 =====
    45|const getPlans = () => request('/api/plans')
    46|const createPlan = (data) => request('/api/plans', 'POST', data)
    47|const deletePlan = (id) => request('/api/plans/' + id, 'DELETE')
    48|const deliverPlan = (id, amount, note) => request('/api/plans/' + id + '/deliver', 'POST', { amount, note })
    49|
    50|// ===== 心愿 =====
    51|const getWishes = () => request('/api/wishes')
    52|const createWish = (data) => request('/api/wishes', 'POST', data)
    53|const updateWish = (id, data) => request('/api/wishes/' + id, 'PUT', data)
    54|const deleteWish = (id) => request('/api/wishes/' + id, 'DELETE')
    55|
    56|// ===== 要做的事 =====
    57|const getTodos = () => request('/api/todos')
    58|const createTodo = (data) => request('/api/todos', 'POST', data)
    59|const checkinTodo = (id) => request('/api/todos/' + id + '/checkin', 'POST')
    60|const deleteTodo = (id) => request('/api/todos/' + id, 'DELETE')
    61|
    62|// ===== 纪念日 =====
    63|const getAnniversaries = () => request('/api/anniversaries')
    64|const createAnniversary = (data) => request('/api/anniversaries', 'POST', data)
    65|const deleteAnniversary = (id) => request('/api/anniversaries/' + id, 'DELETE')
    66|
    67|// ===== 礼物 =====
    68|const getGifts = () => request('/api/gifts')
    69|const createGift = (data) => request('/api/gifts', 'POST', data)
    70|const deleteGift = (id) => request('/api/gifts/' + id, 'DELETE')
    71|
    72|// ===== 便利贴 =====
    73|const getNotes = () => request('/api/notes')
    74|const createNote = (content) => request('/api/notes', 'POST', { content })
    75|const likeNote = (id) => request('/api/notes/' + id + '/like', 'POST')
    76|const deleteNote = (id) => request('/api/notes/' + id, 'DELETE')
    77|
    78|// ===== 等级 =====
    79|const getLevel = () => request('/api/level')
    80|const getLevelLogs = () => request('/api/level/logs')
    81|
    82|// ===== 贺卡 =====
    83|const getCardTemplates = () => request('/api/card/templates')
    84|const getCardSnapshot = () => request('/api/card/snapshot')
    85|const generateCard = (data) => request('/api/card/generate', 'POST', data)
    86|const getTasks, getTaskEvents, createTask, acceptTaskEvent, verifyTask, deleteTask,
  getCards = () => request('/api/cards')
    87|
    88|
// ===== 任务 =====
const getTasks = () => request('/api/tasks')
const getTaskEvents = () => request('/api/tasks/events')
const createTask = (data) => request('/api/tasks', 'POST', data)
const acceptTaskEvent = (eventCode) => request('/api/tasks/accept', 'POST', { event_code: eventCode })
const verifyTask = (id) => request('/api/tasks/' + id + '/verify', 'POST')
const deleteTask = (id) => request('/api/tasks/' + id, 'DELETE')

module.exports = {
    89|  register, login, getMe, getPartner, bindPartner, unbindPartner,
    90|  getPlans, createPlan, deletePlan, deliverPlan,
    91|  getWishes, createWish, updateWish, deleteWish,
    92|  getTodos, createTodo, checkinTodo, deleteTodo,
    93|  getAnniversaries, createAnniversary, deleteAnniversary,
    94|  getGifts, createGift, deleteGift,
    95|  getNotes, createNote, likeNote, deleteNote,
    96|  getLevel, getLevelLogs,
    97|  getCardTemplates, getCardSnapshot, generateCard, getTasks, getTaskEvents, createTask, acceptTaskEvent, verifyTask, deleteTask,
  getCards
    98|}
    99|