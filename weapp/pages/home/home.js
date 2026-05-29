// pages/home/home.js
const api = require('../../utils/api')
const nav = require('../../utils/nav')

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
  const progressPct = Math.min(100, (cur / tar) * 100)
  return {
    ...p,
    progressPct,
    progressPctText: progressPct.toFixed(0),
    _curText: fmtMoney(cur),
    _tarText: fmtMoney(tar)
  }
}

Page({
  data: {
    tabBarIndex: 0,
    userInfo: { nickname: '' }, partner: null,
    level: 1, current_exp: 0, next_level_exp: 1, progress_pct: 0,
    delivered_text: '¥0', target_text: '¥0',
    current_amount: 0, target_amount: 0, plan_progress: 0,
    plan_progress_text: '0.0',
    nearestAnni: null,
    todayAnni: null,
    hasOtherAnni: false,
    plans: [],
    featuredPlan: null,
    active_plan_count: 0,
    coupleDisplayName: '',
    myInitial: '我',
    partnerInitial: '?',
    checkedInToday: false,
    checkinAnim: '',
    plan_count: 0, anni_count: 0, gift_count: 0, together_days: 0,
    // 宠物 & 扭蛋
    pet: null,
    petEmoji: '🥚',
    petImageUrl: '',
    petAnimationClass: 'pet-sleep',
    petName: '小蛋蛋',
    petRarity: 'R',
    intimacyLevel: 0,
    intimacyPct: 0,
    petLevel: 1,
    petMaxLevel: 10,
    petExp: 0,
    petExpNeeded: 4,
    petEvolutionReady: false,
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
    // 今日互动标识
    todayInteractRemaining: 3,
    todayInteractTotal: 0,
    intimacyDeg: 0,
    expDeg: 0,
  },

  onShow() {
    const userInfo = wx.getStorageSync('userInfo')
    if (!userInfo) { wx.reLaunch({ url: '/pages/login/login' }); return }
    const setHomeNav = () => wx.setNavigationBarColor({
      frontColor: '#ffffff',
      backgroundColor: '#FF8FAB',
      animation: { duration: 200, timingFunc: 'easeIn' }
    })
    setHomeNav()
    setTimeout(setHomeNav, 60)
    this.setData({
      userInfo,
      myInitial: (userInfo.nickname || '我').slice(0, 1),
    })
    this.loadData()
    this.loadPetData()
    // 自动签到
    api.doCheckin()
      .then(() => this.setData({ checkedInToday: true }))
      .catch(() => {})
    this.loadSpark()
    this.loadCardTasks()
    // 每日冒险
    this.loadDailyAdventure()
    // 新用户引导：没有计划且没有宠物时触发
    this.checkFirstTimeGuide()
  },

  checkFirstTimeGuide() {
    const guideDone = wx.getStorageSync('guide_done')
    if (guideDone) return
    const { plans, pet } = this.data
    // 首次：没有已有计划或宠物时显示引导
    if ((!plans || plans.length === 0) && !pet) {
      this.setData({ showGuide: true, guideStep: 1 })
    }
  },

  async loadSpark() {
    try {
      const [s, status] = await Promise.all([
        api.getSpark().catch(() => ({})),
        api.getCheckinStatus().catch(() => ({})),
      ])
      this.setData({
        sparkCount: s.spark_count || 0,
        sparkStatus: s.spark_status || 'active',
        maxSpark: s.max_spark_count || 0,
        streakDays: s.streak_days || 0,
        checkedInToday: !!(status.checked_in || status.already_checked),
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

      const activePlans = planList.filter(p => !p.done)
      const featuredPlan = activePlans[0] || planList[0] || null
      const userInfo = this.data.userInfo || wx.getStorageSync('userInfo') || {}
      const coupleDisplayName = partner
        ? `${userInfo.nickname || '我'} 💕 ${partner.nickname}`
        : (userInfo.nickname || '我')

      this.setData({
        partner,
        myInitial: (userInfo.nickname || '我').slice(0, 1),
        partnerInitial: partner ? (partner.nickname || 'Ta').slice(0, 1) : '?',
        plans: planList,
        featuredPlan,
        active_plan_count: activePlans.length,
        coupleDisplayName,
        level: level.level || 1,
        current_exp: level.current_exp || 0,
        next_level_exp: level.next_level_exp || 1,
        progress_pct: level.progress_pct || 0,
        delivered_text: fmtMoney(snapshot.total_delivered || totalCur),
        target_text: fmtMoney(snapshot.total_target || totalTar),
        current_amount: totalCur,
        target_amount: totalTar,
        plan_progress: Math.min(totalCur / Math.max(totalTar, 1) * 100, 100),
        plan_progress_text: Math.min(totalCur / Math.max(totalTar, 1) * 100, 100).toFixed(1),
        nearestAnni: this.findNearestAnni(anniversaries),
        todayAnni: this.findTodayAnni(anniversaries),
        plan_count: planList.length,
        anni_count: Array.isArray(anniversaries) ? anniversaries.length : 0,
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
    if (!Array.isArray(anniversaries)) return null
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
    if (!Array.isArray(anniversaries)) return null
    const now = new Date()
    const todayStr = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`
    return anniversaries.find(a => a && a.date_val === todayStr) || null
  },

  setOtherAnniFlag() {
    const { nearestAnni, todayAnni } = this.data
    if (!nearestAnni || !todayAnni) {
      this.setData({ hasOtherAnni: !!nearestAnni })
      return
    }
    const isSame = todayAnni.title === nearestAnni.title
    this.setData({ hasOtherAnni: !isSame })
  },

  // ===== 升级动画 =====

  async loadDailyAdventure() {
    try {
      const res = await api.getDailyAdventure()
      if (res.triggered && !res.already_done) {
        const reward = res.reward || {}
        this.setData({
          showAdventure: true,
          adventureData: {
            ...res,
            reward: {
              shards: reward.shards || 0,
              exp: reward.exp || 0,
              tickets: reward.tickets || 0,
            },
            week_summary: res.week_summary || null,
          },
        })
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
    nav.openPage(e.currentTarget.dataset.url)
  },
  goTab(e) {
    nav.openPage(e.currentTarget.dataset.url)
  },
  goBind() { nav.openPage('/pages/settings/settings') },

  onCheckinTap() {
    if (this.data.checkedInToday) {
      nav.openPage('/pages/level/level')
      return
    }
    // 先播动画
    this.setData({ checkinAnim: 'checkin-bounce' })
    setTimeout(() => { this.setData({ checkinAnim: '' }) }, 500)
    api.doCheckin()
      .then(() => {
        this.setData({ checkedInToday: true, checkinAnim: 'checkin-done-pop' })
        setTimeout(() => { this.setData({ checkinAnim: '' }) }, 600)
        wx.showToast({ title: '签到成功 +5积分', icon: 'none' })
        this.loadSpark()
      })
      .catch(() => wx.showToast({ title: '签到失败', icon: 'none' }))
  },

  // ===== 新用户引导 =====

  nextGuideStep() {
    const step = this.data.guideStep
    if (step < 3) {
      this.setData({ guideStep: step + 1 })
    }
  },

  dismissGuide() {
    this.setData({ showGuide: false, guideStep: 1 })
    wx.setStorageSync('guide_done', true)
  },

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
      petRarity: pet.rarity || 'R',
      intimacyLevel: intimacy,
      intimacyPct: Math.min(100, Math.round(intimacy)),
      petDescription: `形态：${pet.form_label || pet.form} | 亲密度：${intimacy}/100`,
      intimacyStageName: stageName,
      petPassiveSkill: pet.passive_skill || '',
      petLevel: pet.level || 1,
      petMaxLevel: pet.max_level || 10,
      petExp: pet.exp || 0,
      petExpNeeded: pet.exp_needed || 4,
      petEvolutionReady: pet.evolution_ready || false,
      // 计算今日互动状态（使用后端返回的统一每日次数）
      todayInteractRemaining: Math.max(0, (pet.max_daily_interact || 3) - (pet.today_interact_count || 0)),
      todayInteractTotal: pet.today_interact_count || 0,
      // 半圆环角度
      intimacyDeg: Math.round(1.8 * Math.min(100, Math.round(intimacy))),
      expDeg: pet.exp_needed > 0 ? Math.round(1.8 * Math.min(100, (pet.exp || 0) / pet.exp_needed * 100)) : 0,
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
    nav.openPage('/pages/pets/pets')
  },

  /** 展示互动反馈emoji（漂浮动画） */
  showActionEmojiWithAnim(emoji, animClass) {
    this.setData({ showActionEmoji: true, actionEmoji: emoji, actionEmojiClass: animClass })
    setTimeout(() => {
      this.setData({ showActionEmoji: false, actionEmojiClass: '' })
    }, 1200)
  },

  /** 点击宠物→抚摸：扇形摆动动画（已互动过也播动画，但不调接口） */
  async onPetTap() {
    const { petId, lastInteractTime, todayInteractRemaining } = this.data
    if (!petId) return
    const now = Date.now()
    if (now - lastInteractTime < 500) return
    this.setData({ petActionClass: 'pet-fan-shake', lastInteractTime: now })
    setTimeout(() => { this.setData({ petActionClass: '' }) }, 600)
    if (todayInteractRemaining <= 0) return
    try {
      await api.petPet(petId)
      this.setData({ todayInteractRemaining: this.data.todayInteractRemaining - 1, todayInteractTotal: this.data.todayInteractTotal + 1 })
    } catch (e) {
      if (e._statusCode === 429) {
        this.setData({ todayInteractRemaining: 0 })
      }
    }
  },

  /** 喂食按钮：剧烈抖动+饭盆（已互动过也播动画，但不调接口） */
  async onFeed() {
    const { petId, lastInteractTime, todayInteractRemaining } = this.data
    if (!petId) return
    const now = Date.now()
    if (now - lastInteractTime < 500) return
    this.setData({ lastInteractTime: now })
    this.startFeedAnimation()
    if (todayInteractRemaining <= 0) return
    try {
      const res = await api.feedPet(petId)
      this.setData({ todayInteractRemaining: this.data.todayInteractRemaining - 1, todayInteractTotal: this.data.todayInteractTotal + 1 })
      wx.showToast({ title: '🍼 喂食成功！', icon: 'none' })
      this.loadPetData()
      this.loadData()
    } catch (e) {
      if (e._statusCode === 429) {
        this.setData({ todayInteractRemaining: 0 })
        wx.showToast({ title: e.detail || '今天互动次数已用完~', icon: 'none' })
      } else {
        wx.showToast({ title: e.detail || e.errMsg || '喂食失败', icon: 'none' })
      }
    }
  },

  /** 散步按钮：左右蹦跳动画（已互动过也播动画，但不调接口） */
  async onWalk() {
    const { petId, lastInteractTime, todayInteractRemaining } = this.data
    if (!petId) return
    const now = Date.now()
    if (now - lastInteractTime < 500) return
    this.setData({ petActionClass: 'pet-walk-anim', lastInteractTime: now })
    this.showActionEmojiWithAnim('🚶', 'emoji-float-up')
    setTimeout(() => { this.setData({ petActionClass: '' }) }, 1000)
    if (todayInteractRemaining <= 0) return
    try {
      await api.walkPet(petId)
      this.setData({ todayInteractRemaining: this.data.todayInteractRemaining - 1, todayInteractTotal: this.data.todayInteractTotal + 1 })
      wx.showToast({ title: '🚶 散步成功 +2 ❤️', icon: 'none' })
      this.loadPetData()
    } catch (e) {
      if (e._statusCode === 429) {
        this.setData({ todayInteractRemaining: 0 })
        wx.showToast({ title: e.detail || '今天互动次数已用完~', icon: 'none' })
      }
    }
  },

  /** 玩耍按钮：八个方向无规则剧烈移动（纯前端，不调接口） */
  onPlay() {
    const { petId, lastInteractTime } = this.data
    if (!petId) return
    const now = Date.now()
    if (now - lastInteractTime < 300) return
    this.setData({ petActionClass: 'pet-wild-move', lastInteractTime: now })
    this.showActionEmojiWithAnim('😊', 'emoji-float-up')
    setTimeout(() => { this.setData({ petActionClass: '' }) }, 700)
  },

  /** 聊天按钮：轻快摇晃动画（纯前端，不调接口） */
  onTalk() {
    const { petId, lastInteractTime } = this.data
    if (!petId) return
    const now = Date.now()
    if (now - lastInteractTime < 300) return
    this.setData({ petActionClass: 'pet-talk-anim', lastInteractTime: now })
    this.showActionEmojiWithAnim('💬', 'emoji-float-up')
    setTimeout(() => { this.setData({ petActionClass: '' }) }, 700)
  },

  stopPropagation() {},

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
      if (e._statusCode === 429) {
        wx.showToast({ title: e.detail || '🐷 小宠物吃饱了，明天再来吧~', icon: 'none' })
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
      petFeedClass: 'pet-violent-shake',
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
        title: '🎉 太好了！',
        content: '对方原谅你了，快去主动找她吧 💕✨',
        success: async (res) => {
          if (!res.confirm) return
          try {
            const result = await api.dismissCardTask(taskId)
            if (result.is_please_forgive) {
              wx.showToast({ title: '💕✨ 太好了！快去找他当面认错吧！', icon: 'none', duration: 3000 })
            } else {
              wx.showToast({ title: '💕 太好了！你们和好了！', icon: 'none' })
            }
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
          const result = await api.forgiveCardTask(taskId)
          const msg = result.is_please_forgive ? '对方已经原谅你了，快去找他当面认错吧 💕✨' : '你原谅了对方 💕'
          wx.showToast({ title: msg, icon: 'none', duration: 3000 })
          this.loadCardTasks()
        } catch (e) {
          wx.showToast({ title: e.detail || '操作失败', icon: 'none' })
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
          wx.showToast({ title: e.detail || '操作失败', icon: 'none' })
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
          wx.showToast({ title: e.detail || '操作失败', icon: 'none' })
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
          wx.showToast({ title: e.detail || '操作失败', icon: 'none' })
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
          wx.showToast({ title: e.detail || '操作失败', icon: 'none' })
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
          wx.showToast({ title: e.detail || '操作失败', icon: 'none' })
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
          wx.showToast({ title: e.detail || '拒绝失败', icon: 'none' })
        }
      }
    })
  },

  /** 判断一个日期字符串/对象是否为今天 */
  isToday(dateVal) {
    if (!dateVal) return false
    try {
      const d = new Date(String(dateVal).slice(0, 10))
      const t = new Date()
      return d.getFullYear() === t.getFullYear() && d.getMonth() === t.getMonth() && d.getDate() === t.getDate()
    } catch (e) { return false }
  },

  /** 计算今日互动总数（使用后端返回的统一次数） */
  countTodayInteractions(pet) {
    return pet.today_interact_count || 0
  },
})
