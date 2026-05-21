// pages/home/home.js
const api = require('../../utils/api')

function fmtMoney(n) {
  if (n >= 100000000) return '¥' + (n/100000000).toFixed(1) + '亿'
  if (n >= 10000) return '¥' + (n/10000).toFixed(1) + '万'
  return '¥' + n.toLocaleString()
}

// ---------- 宠物辅助（已移除亲密度映射，使用后端真实形象） ----------

function getFullImageUrl(path) {
  if (!path) return ''
  const base = getApp().globalData.baseUrl
  return base + path
}

function wrapPlan(p) {
  const cur = Number(p.current_amount) || 0
  const tar = Math.max(Number(p.target_amount) || 1, 1)
  return {
    ...p,
    progressPct: Math.min(100, (cur / tar) * 100),
    _curText: fmtMoney(cur),
    _tarText: fmtMoney(tar)
  }
}

Page({
  data: {
    tabBarIndex: 0,
    userInfo: null, partner: null,
    level: 1, current_exp: 0, next_level_exp: 1, progress_pct: 0,
    delivered_text: '¥0', target_text: '¥0',
    current_amount: 0, target_amount: 0, plan_progress: 0,
    nearestAnni: null,
    todayAnni: null,
    hasOtherAnni: false,
    plans: [],
    plan_count: 0, anni_count: 0, gift_count: 0, together_days: 0,
    // 宠物 & 扭蛋
    pet: null,
    petEmoji: '🥚',
    petImageUrl: '',
    petAnimationClass: 'pet-sleep',
    petName: '小蛋蛋',
    intimacyLevel: 0,
    intimacyPct: 0,
    petDescription: '刚刚孵化的小家伙，需要你的关爱才能长大……',
    petId: null,
    tickets: 0,
    showPetModal: false,
    sparkCount: 0,
    sparkStatus: 'active',
    maxSpark: 0,
    streakDays: 0,
    // 卡片任务
    cardTasksAsAssigner: [],
    cardTasksAsAssignee: [],
    // 升级动画
    showLevelUp: false,
    levelUpNewLevel: 1,
    // 冒险弹窗
    showAdventure: false,
    adventureData: null,
    petActionClass: '',       // 当前互动动画class
    petFeedClass: '',
    showFeedBowl: false,
    bowlFoodHeight: 100,
    feedAnimTimer: null,
    lastInteractTime: 0,      // 防抖时间戳
    showActionEmoji: false,   // 互动反馈emoji
    actionEmoji: '',
    actionEmojiClass: '',
  },

  onShow() {
    const userInfo = wx.getStorageSync('userInfo')
    if (!userInfo) { wx.reLaunch({ url: '/pages/login/login' }); return }
    this.setData({ userInfo })
    this.loadData()
    this.loadPetData()
    // 自动签到
    api.doCheckin().catch(() => {})
    this.loadSpark()
    this.loadCardTasks()
    // 每日冒险
    this.loadDailyAdventure()
  },

  async loadSpark() {
    try {
      const s = await api.getSpark()
      this.setData({
        sparkCount: s.spark_count || 0,
        sparkStatus: s.spark_status || 'active',
        maxSpark: s.max_spark_count || 0,
        streakDays: s.streak_days || 0,
      })
    } catch(e) {}
  },

  async loadData() {
    try {
      const [plans, anniversaries, level, snapshot, partner] = await Promise.all([
        api.getPlans().catch(() => []),
        api.getAnniversaries().catch(() => []),
        api.getLevel().catch(() => ({ level: 1, progress_pct: 0, current_exp: 0, next_level_exp: 1 })),
        api.getCardSnapshot().catch(() => ({})),
        api.getPartner().catch(() => null)
      ])

      // 存钱进度 - 所有计划汇总
      const validPlans = Array.isArray(plans) ? plans : []
      const planList = validPlans.map(wrapPlan)
      const totalCur = planList.reduce((s, p) => s + (Number(p.current_amount) || 0), 0)
      const totalTar = planList.reduce((s, p) => s + (Number(p.target_amount) || 0), 0)
      const activePlan = planList.find(p => !p.done) || planList[0]
      const cur = activePlan ? activePlan.current_amount || 0 : 0
      const tar = activePlan ? activePlan.target_amount || 1 : 1

      this.setData({
        partner,
        plans: planList,
        level: level.level || 1,
        current_exp: level.current_exp || 0,
        next_level_exp: level.next_level_exp || 1,
        progress_pct: level.progress_pct || 0,
        delivered_text: fmtMoney(snapshot.total_delivered || totalCur),
        target_text: fmtMoney(snapshot.total_target || totalTar),
        current_amount: totalCur,
        target_amount: totalTar,
        plan_progress: Math.min(totalCur / Math.max(totalTar, 1) * 100, 100),
        nearestAnni: this.findNearestAnni(anniversaries),
        todayAnni: this.findTodayAnni(anniversaries),
        plan_count: planList.length,
        anni_count: anniversaries.length,
        gift_count: snapshot.gift_count || 0,
        together_days: snapshot.together_days || 0
      })
      // 计算是否有"今天之外"的下一个纪念日
      this.setOtherAnniFlag()
      // 检测升级弹窗
      this.checkLevelUp(level)
    } catch(e) { console.error(e) }
  },

  findNearestAnni(anniversaries) {
    const now = new Date()
    let nearest = null
    for (const a of anniversaries) {
      const p = a.date_val.split('-')
      if (p.length < 3) continue
      const d = new Date(now.getFullYear(), parseInt(p[1]) - 1, parseInt(p[2]))
      if (d < now) d.setFullYear(d.getFullYear() + 1)
      const days = Math.ceil((d - now) / 86400000)
      if (!nearest || days < nearest.days) nearest = { title: a.title, days, date: a.date_val }
    }
    return nearest
  },

  findTodayAnni(anniversaries) {
    const now = new Date()
    const todayStr = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`
    const found = anniversaries.filter(a => a.date_val === todayStr)
    return found.length > 0 ? found : null
  },

  setOtherAnniFlag() {
    const { nearestAnni, todayAnni } = this.data
    if (!nearestAnni || !todayAnni) {
      this.setData({ hasOtherAnni: !!nearestAnni })
      return
    }
    const isSame = todayAnni.some(t => t.title === nearestAnni.title)
    this.setData({ hasOtherAnni: !isSame })
  },

  // ===== 升级动画 =====

  async loadDailyAdventure() {
    try {
      const res = await api.getDailyAdventure()
      if (res.triggered && !res.already_done) {
        this.setData({ showAdventure: true, adventureData: res })
        setTimeout(() => this.setData({ showAdventure: false }), 4000)
      }
    } catch (e) { /* 静默 */ }
  },

  hideAdventure() {
    this.setData({ showAdventure: false })
  },

  checkLevelUp(levelData) {
    const pending = levelData.pending_levelups || 0
    if (pending <= 0) return
    // 连续升级只弹最高等级
    this.setData({
      showLevelUp: true,
      levelUpNewLevel: levelData.level,
    })
    // 自动关闭 + 消费
    setTimeout(() => {
      this.setData({ showLevelUp: false })
      api.consumeLevelPending().catch(() => {})
    }, 3000)
  },

  go(e) { 
    const url = e.currentTarget.dataset.url
    if (url === '/pages/plans/plans') {
      wx.switchTab({ url })
    } else {
      wx.navigateTo({ url })
    }
  },
  goTab(e) { wx.switchTab({ url: e.currentTarget.dataset.url }) },
  goBind() { wx.switchTab({ url: '/pages/settings/settings' }) },

  // ===== 宠物 & 扭蛋 =====

  async loadPetData() {
    try {
      const [petRes, ticketsRes] = await Promise.all([
        api.getActivePet().catch(() => null),
        api.getTickets().catch(() => ({ tickets: 0 }))
      ])
      this.updatePetUI(petRes)
      this.setData({ tickets: ticketsRes.tickets || 0 })
    } catch (e) { console.error('loadPetData', e) }
  },

  updatePetUI(pet) {
    if (!pet) {
      this.setData({
        pet: null, petId: null,
        petEmoji: '🐾', petAnimationClass: 'pet-sleep',
        petName: '暂无宠物', intimacyLevel: 0, intimacyPct: 0,
        petDescription: '还没有宠物，去抽卡获取吧！',
        intimacyStageName: '', petPassiveSkill: '',
      })
      return
    }
    const intimacy = pet.intimacy ?? 0
    // 亲密度阶段
    const lvl = pet.intimacy_level || ''
    let stageName = '初识🤝'
    if (lvl === 'low') stageName = '初识🤝'
    else if (lvl === 'normal') stageName = '熟悉😊'
    else if (lvl === 'happy') stageName = '亲密🥰'
    else if (lvl === 'love') stageName = '挚爱💕'
    // 动画：根据形态阶段或亲密度决定
    const form = pet.form || ''
    let anim = 'pet-bounce'
    if (form === 'teen' || form.startsWith('branch_')) anim = 'pet-walk-slow'
    else if (form === 'adult') anim = 'pet-walk'
    else if (form === 'deluxe') anim = 'pet-excited'
    else if (form === 'legend') anim = 'pet-magic'
    this.setData({
      pet,
      petId: pet.id,
      petEmoji: pet.emoji || '🐾',
      petImageUrl: getFullImageUrl(pet.image_url),
      petAnimationClass: anim,
      petName: pet.form_label || '宠物',
      intimacyLevel: intimacy,
      intimacyPct: Math.min(100, Math.round(intimacy)),
      petDescription: `形态：${pet.form_label || pet.form} | 亲密度：${intimacy}/100`,
      intimacyStageName: stageName,
      petPassiveSkill: pet.passive_skill || '',
    })
  },

  showPetModal() {
    this.setData({ showPetModal: true })
  },

  hidePetModal() {
    this.setData({ showPetModal: false })
  },

  goPetPage() {
    this.setData({ showPetModal: false })
    wx.navigateTo({ url: '/pages/pets/pets' })
  },

  stopPropagation() {},

  /** 展示互动反馈emoji（漂浮动画） */
  showActionEmojiWithAnim(emoji, animClass) {
    this.setData({ showActionEmoji: true, actionEmoji: emoji, actionEmojiClass: animClass })
    setTimeout(() => {
      this.setData({ showActionEmoji: false, actionEmojiClass: '' })
    }, 1200)
  },

  /** 点击宠物→抚摸：扇形抖动动画+抚摸API（动画先于接口） */
  async onPetTap() {
    const { petId, lastInteractTime } = this.data
    if (!petId) return
    const now = Date.now()
    if (now - lastInteractTime < 1500) return
    this.setData({ petActionClass: 'pet-fan-shake', lastInteractTime: now })
    this.showActionEmojiWithAnim('🤗', 'emoji-float-up')
    setTimeout(() => {
      this.setData({ petActionClass: '' })
    }, 800)
    try {
      await api.petPet(petId)
    } catch (e) { /* 静默，日限由后端处理 */ }
  },

  /** 喂食按钮：剧烈抖动+饭盆emoji→调用喂食API（动画先于接口） */
  async onFeed() {
    const { petId, lastInteractTime } = this.data
    if (!petId) return
    const now = Date.now()
    if (now - lastInteractTime < 2000) {
      wx.showToast({ title: '🔄 等一等…', icon: 'none' })
      return
    }
    this.setData({ lastInteractTime: now })
    // 先播动画
    this.startFeedAnimation()
    this.showActionEmojiWithAnim('🍚', 'emoji-pop')
    // 再调接口
    try {
      const res = await api.feedPet(petId)
      wx.showToast({ title: '🍼 喂食成功！', icon: 'none' })
      this.loadPetData()
      this.loadData()
    } catch (e) {
      const msg = ((e && e.detail) || e.errMsg || '').toLowerCase()
      if (msg.includes('429') || msg.includes('喂过') || msg.includes('明天')) {
        wx.showToast({ title: '🐷 小宠物吃饱了，明天再来吧~', icon: 'none' })
      } else {
        wx.showToast({ title: e.detail || e.errMsg || '喂食失败', icon: 'none' })
      }
    }
  },

  /** 散步按钮：四处蹦跳动画→调用散步API（动画先于接口） */
  async onWalk() {
    const { petId, lastInteractTime } = this.data
    if (!petId) return
    const now = Date.now()
    if (now - lastInteractTime < 2000) {
      wx.showToast({ title: '🔄 等一等…', icon: 'none' })
      return
    }
    this.setData({ petActionClass: 'pet-bounce-all', lastInteractTime: now })
    this.showActionEmojiWithAnim('🚶', 'emoji-float-up')
    setTimeout(() => {
      this.setData({ petActionClass: '' })
    }, 1200)
    try {
      await api.walkPet(petId)
      wx.showToast({ title: '🚶 散步成功 +2 ❤️', icon: 'none' })
      this.loadPetData()
    } catch (e) {
      const msg = ((e && e.detail) || e.errMsg || '').toLowerCase()
      if (msg.includes('429') || msg.includes('散步')) {
        wx.showToast({ title: '🚶 今天已经散过步了~', icon: 'none' })
      }
    }
  },

  /** 玩耍按钮：上下跳动动画（纯前端，不调接口） */
  onPlay() {
    const { petId, lastInteractTime } = this.data
    if (!petId) return
    const now = Date.now()
    if (now - lastInteractTime < 1000) return
    this.setData({ petActionClass: 'pet-jump-up', lastInteractTime: now })
    this.showActionEmojiWithAnim('🎮', 'emoji-float-up')
    setTimeout(() => { this.setData({ petActionClass: '' }) }, 800)
  },

  /** 聊天按钮：左右摆动动画（纯前端，不调接口） */
  onTalk() {
    const { petId, lastInteractTime } = this.data
    if (!petId) return
    const now = Date.now()
    if (now - lastInteractTime < 1000) return
    this.setData({ petActionClass: 'pet-sway', lastInteractTime: now })
    this.showActionEmojiWithAnim('💬', 'emoji-float-up')
    setTimeout(() => { this.setData({ petActionClass: '' }) }, 1000)
  },

  /** 点击宠物容器 → 宠物管理页面（唯一入口） */
  goPetPage() {
    wx.navigateTo({ url: '/pages/pets/pets' })
  },

  async feedCurrentPet() {
    const { petId } = this.data
    if (!petId) {
      wx.showToast({ title: '还没有宠物', icon: 'none' })
      return
    }
    // 动画先播放，不论是否已喂过
    this.startFeedAnimation()
    try {
      wx.showLoading({ title: '投喂中…' })
      const res = await api.feedPet(petId)
      wx.hideLoading()
      wx.showToast({ title: '🍼 投喂成功！', icon: 'none' })
      // 投喂后刷新宠物状态
      this.loadPetData()
      this.loadData()
    } catch (e) {
      wx.hideLoading()
      const msg = ((e && e.detail) || e.errMsg || '').toLowerCase()
      if (msg.includes('429') || msg.includes('喂过') || msg.includes('消化') || msg.includes('明天')) {
        wx.showToast({ title: '🐷 小宠物吃饱了，明天再来吧~', icon: 'none' })
      } else {
        wx.showToast({ title: e.detail || e.errMsg || '投喂失败', icon: 'none' })
      }
    }
  },

  /** 开始喂食动画：宠物剧烈抖动 + 饭盆被啃食 */
  startFeedAnimation() {
    const oldTimer = this.data.feedAnimTimer
    if (oldTimer) clearInterval(oldTimer)
    this.setData({
      petFeedClass: 'pet-shake',
      showFeedBowl: true,
      bowlFoodHeight: 100,
    })
    // 饭盆食物逐渐减少（每帧减5%，约2秒吃完）
    let pct = 100
    const timer = setInterval(() => {
      pct -= 5
      if (pct <= 0) {
        pct = 0
        clearInterval(timer)
        this.setData({ showFeedBowl: false, petFeedClass: '', feedAnimTimer: null })
      }
      this.setData({ bowlFoodHeight: pct })
    }, 100)
    this.setData({ feedAnimTimer: timer })
  },

  // ===== 卡片任务 =====

  async loadCardTasks() {
    try {
      const res = await api.getCardTasks()
      this.setData({
        cardTasksAsAssigner: res.as_assigner || [],
        cardTasksAsAssignee: res.as_assignee || [],
      })
    } catch (e) { /* 伴侣未绑定时静默 */ }
  },

  async onCardForgive(e) {
    const taskId = e.currentTarget.dataset.id
    const mode = e.currentTarget.dataset.mode
    // 已完成任务的确认操作
    if (mode === 'ack') {
      wx.showModal({
        title: '确认原谅',
        content: '对方已经原谅了你 💕',
        success: async (res) => {
          if (!res.confirm) return
          try {
            await api.dismissCardTask(taskId)
            wx.showToast({ title: '💕 你们和好了！', icon: 'none' })
          } catch (e) {
            wx.showToast({ title: '操作失败', icon: 'none' })
          }
          this.loadCardTasks()
        }
      })
      return
    }
    wx.showModal({
      title: '愿意原谅',
      content: '你真的愿意原谅TA吗？💕',
      success: async (res) => {
        if (!res.confirm) return
        try {
          await api.forgiveCardTask(taskId)
          wx.showToast({ title: '你原谅了对方 💕', icon: 'none' })
          this.loadCardTasks()
        } catch (e) {
          wx.showToast({ title: e.errMsg || '操作失败', icon: 'none' })
        }
      }
    })
  },

  onCardReject(e) {
    const taskId = e.currentTarget.dataset.id
    wx.showModal({
      title: '不愿意',
      content: '暂时不想原谅TA吗？🥺',
      success: async (res) => {
        if (!res.confirm) return
        try {
          await api.rejectForgive(taskId)
          wx.showToast({ title: '已收到，TA还会再来请求的', icon: 'none' })
          this.loadCardTasks()
        } catch (e) {
          wx.showToast({ title: e.errMsg || '操作失败', icon: 'none' })
        }
      }
    })
  },

  onCardRetry(e) {
    const taskId = e.currentTarget.dataset.id
    wx.showModal({
      title: '再次请求原谅',
      content: '再给对方发送一次请求吗？🥺',
      success: async (res) => {
        if (!res.confirm) return
        try {
          await api.retryForgive(taskId)
          wx.showToast({ title: '已发送，等待对方的回应…', icon: 'none' })
          this.loadCardTasks()
        } catch (e) {
          wx.showToast({ title: e.errMsg || '操作失败', icon: 'none' })
        }
      }
    })
  },

  onAckForgive(e) {
    const taskId = e.currentTarget.dataset.id
    wx.showToast({ title: '💕 你们和好了！', icon: 'none' })
    // 简单刷新，任务会在5分钟后自动从列表消失
    this.loadCardTasks()
  },

  onCardComplete(e) {
    const taskId = e.currentTarget.dataset.id
    wx.showModal({
      title: '完成任务',
      content: '确认已完成该任务？',
      success: async (res) => {
        if (!res.confirm) return
        try {
          await api.completeCardTask(taskId)
          wx.showToast({ title: '已完成，等待对方确认', icon: 'none' })
          this.loadCardTasks()
        } catch (e) {
          wx.showToast({ title: e.errMsg || '操作失败', icon: 'none' })
        }
      }
    })
  },

  onCardConfirm(e) {
    const taskId = e.currentTarget.dataset.id
    wx.showModal({
      title: '确认完成',
      content: '确认对方已完成任务？',
      success: async (res) => {
        if (!res.confirm) return
        try {
          await api.confirmCardTask(taskId)
          wx.showToast({ title: '任务已完成 ✅', icon: 'none' })
          this.loadCardTasks()
        } catch (e) {
          wx.showToast({ title: e.errMsg || '操作失败', icon: 'none' })
        }
      }
    })
  },

  onCardDispute(e) {
    const taskId = e.currentTarget.dataset.id
    wx.showModal({
      title: '退回任务',
      content: '确认任务未完成，退回给对方？',
      success: async (res) => {
        if (!res.confirm) return
        try {
          await api.disputeCardTask(taskId)
          wx.showToast({ title: '已退回，等待对方重新完成', icon: 'none' })
          this.loadCardTasks()
        } catch (e) {
          wx.showToast({ title: e.errMsg || '操作失败', icon: 'none' })
        }
      }
    })
  },

  onCardDecline(e) {
    const taskId = e.currentTarget.dataset.id
    wx.showModal({
      title: '使用「我不要卡」',
      content: '消耗一张「我不要卡」拒绝此任务？',
      success: async (res) => {
        if (!res.confirm) return
        try {
          await api.declineCardTask(taskId)
          wx.showToast({ title: '已拒绝任务 😤', icon: 'none' })
          this.loadCardTasks()
        } catch (e) {
          wx.showToast({ title: e.errMsg || '拒绝失败', icon: 'none' })
        }
      }
    })
  },
})
