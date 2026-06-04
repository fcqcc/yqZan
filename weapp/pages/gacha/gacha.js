// pages/gacha/gacha.js — 扭蛋机抽卡
const api = require('../../utils/api')

Page({
  data: {
    tickets: 0,
    shards: 0,
    drawing: false,
    animating: false,
    showBall: false,
    resultEmoji: '',
    showResult: false,
    currentResult: {},
    resultAnimClass: '',
    tenResults: [],
    summaryList: [],
    showProbModal: false,
    probList: [],
    useBoost: false,
    pityCount: 0,
    uiTheme: getApp().globalData.uiTheme || 'handdrawn',
  },

  onLoad() {
    this.loadPool()
  },

  async loadPool() {
    try {
      const pool = await api.getGachaPool()
      this.setData({ probList: pool })
    } catch (e) {
      // 降级：后端不可用时用硬编码
      this.setData({ probList: [
        { rarity: 'SSR+', name: '金元宝龙🐉/原谅我吧🥺', pct: '0.5' },
        { rarity: 'SSR', name: '独角兽🦄/为我服务👑/机械核心/星尘', pct: '4.8' },
        { rarity: 'SR', name: '招财猫🐱/金元宝🪙/月光石🌙...', pct: '17' },
        { rarity: 'R', name: '小狐狸🦊/家务卡/樱花背景...', pct: '28' },
        { rarity: 'N', name: '幸运饼干🍪/切换卡🔄/亲密糖果🍬', pct: '44' },
      ]})
    }
  },

  onShow() {
    this.setData({ uiTheme: getApp().globalData.uiTheme || 'handdrawn' })
    const userInfo = wx.getStorageSync('userInfo')
    if (!userInfo) { wx.reLaunch({ url: '/pages/login/login' }); return }
    this.loadTickets()
    this.setData({ userInfo })
  },

  /** 加载抽卡券数量 */
  async loadTickets() {
    try {
      const res = await api.getTickets()
      this.setData({ tickets: res.tickets || 0, shards: res.shards || 0, pityCount: res.gacha_pity || 0 })
    } catch (e) {
      console.error('加载抽卡券失败', e)
    }
  },

  /** 切换积分加注 */
  toggleBoost() {
    this.setData({ useBoost: !this.data.useBoost })
  },

  /** 单抽 */
  async onDrawSingle() {
    if (this.data.drawing) return
    if (this.data.tickets < 1) {
      this.askBuyTickets(1)
      return
    }
    this.setData({ drawing: true, animating: true, tenResults: [] })

    try {
      const res = await api.drawSingle()
      // 返回格式: { item: { name, rarity, desc }, tickets }
      const result = res.item || res
      this.showResult(result)

      // 更新券数和保底
      this.setData({
        tickets: res.tickets || this.data.tickets - 1,
        pityCount: res.pity_count || 0,
      })
    } catch (e) {
      console.error('单抽失败', e)
      wx.showToast({ title: '抽卡失败，请重试', icon: 'none' })
    } finally {
      this.setData({ drawing: false })
      setTimeout(() => this.setData({ animating: false }), 800)
    }
  },

  /** 十连 */
  async onDrawTen() {
    if (this.data.drawing) return
    if (this.data.tickets < 10) {
      this.askBuyTickets(10)
      return
    }
    this.setData({ drawing: true, animating: true })

    try {
      const boost = this.data.useBoost
      const res = await api.drawTen(boost)
      const items = res.items || []
      const itemsWithClass = items.map(i => ({
        ...i,
        rarity: (i.rarity || 'N').toUpperCase(),
        rarityClass: (i.rarity || 'N').toUpperCase() === 'SSR+' ? 'SSRP' : (i.rarity || 'N').toUpperCase()
      }))
      const summary = this.buildSummary(itemsWithClass)
      const highlight = this.findHighlight(itemsWithClass)
      if (highlight) {
        this.showResult(highlight)
      }

      this.setData({
        tenResults: itemsWithClass,
        summaryList: summary,
        tickets: res.tickets || this.data.tickets - 9,
        shards: res.shards_remaining != null ? res.shards_remaining : this.data.shards,
        pityCount: res.pity_count || 0,
        useBoost: false,
      })
    } catch (e) {
      console.error('十连失败', e)
      wx.showToast({ title: '抽卡失败，请重试', icon: 'none' })
    } finally {
      this.setData({ drawing: false })
      setTimeout(() => this.setData({ animating: false }), 800)
    }
  },

  /** 显示抽卡结果弹窗（带扭蛋弹出动画） */
  showResult(item) {
    const rarity = (item.rarity || 'N').toUpperCase()
    let animClass = 'resultAnimN'
    if (rarity === 'R') animClass = 'resultAnimR'
    else if (rarity === 'SR') animClass = 'resultAnimSR'
    else if (rarity === 'SSR') animClass = 'resultAnimSSR'
    else if (rarity === 'SSR+') animClass = 'resultAnimSSRP'

    // 弹出扭蛋动画
    const emojiMap = { 'N': '⚪', 'R': '🔵', 'SR': '🟣', 'SSR': '🟡', 'SSR+': '🌟' }
    this.setData({
      showBall: true,
      resultEmoji: emojiMap[rarity] || '🎯'
    })
    // 延迟显示结果
    setTimeout(() => {
      this.setData({
        showResult: true,
        showBall: false,
        currentResult: { ...item, rarity, rarityClass: rarity === 'SSR+' ? 'SSRP' : rarity },
        resultAnimClass: animClass
      })
    }, 1200)
  },

  /** 关闭结果弹窗 */
  onCloseResult() {
    this.setData({ showResult: false, currentResult: {} })
  },

  /** 查看十连中的某个详情 */
  onShowItemDetail(e) {
    const index = e.currentTarget.dataset.index
    const item = this.data.tenResults[index]
    if (item) this.showResult(item)
  },

  /** 构建十连统计摘要 */
  buildSummary(items) {
    const map = {}
    for (const item of items) {
      const r = (item.rarity || 'N').toUpperCase()
      if (!map[r]) map[r] = { label: r, count: 0 }
      map[r].count++
    }
    // 按稀有度排序: SSR+ > SSR > SR > R > N
    const order = ['SSR+', 'SSR', 'SR', 'R', 'N']
    return order.filter(k => map[k]).map(k => map[k])
  },

  /** 找到十连中最高稀有度的物品 */
  findHighlight(items) {
    const order = ['SSR+', 'SSR', 'SR', 'R', 'N']
    for (const r of order) {
      const found = items.find(i => (i.rarity || '').toUpperCase() === r)
      if (found) return found
    }
    return items[0]
  },

  preventMove() {},
  catchTap() {},

  /** 显示概率弹窗 */
  showProb() {
    this.setData({ showProbModal: true })
  },
  hideProb() {
    this.setData({ showProbModal: false })
  },

  /** 积分购买弹窗 */
  askBuyTickets(amount) {
    const label = amount === 1 ? '单抽' : '十连'
    const cost = amount === 10 ? 1000 : 100
    const shards = this.data.shards
    const hasEnough = shards >= cost
    wx.showModal({
      title: `抽卡券不足，用积分兑换？`,
      content: `🎟️ ${amount} 张抽卡券  =  💎 ${cost} 积分\n📊 当前积分：${shards} ${hasEnough ? '' : '（不足）'}`,
      cancelText: '不了',
      confirmText: hasEnough ? `兑换并${label}` : '积分不足',
      confirmColor: hasEnough ? undefined : '#ccc',
      success: async (res) => {
        if (!res.confirm || !hasEnough) return
        wx.showLoading({ title: '兑换中' })
        try {
          const result = await api.buyTickets(amount)
          wx.hideLoading()
          this.setData({ tickets: result.tickets, shards: result.shards })
          wx.showToast({ title: `兑换成功 ✨`, icon: 'none' })
          if (amount === 1) this.onDrawSingle()
          else this.onDrawTen()
        } catch (e) {
          wx.hideLoading()
          wx.showToast({ title: '兑换失败', icon: 'none' })
        }
      }
    })
  }
})
