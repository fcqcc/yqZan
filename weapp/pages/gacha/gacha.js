// pages/gacha/gacha.js — 扭蛋机抽卡
const api = require('../../utils/api')

Page({
  data: {
    tickets: 0,
    drawing: false,
    animating: false,
    showResult: false,
    currentResult: {},
    resultAnimClass: '',
    tenResults: [],
    summaryList: [],
    showProbModal: false,
    probList: []
  },

  onLoad() {
    // 概率数据（硬编码，和后端一致）
    const probList = [
      { rarity: 'SSR+', name: '金元宝龙🐉', pct: '0.3' },
      { rarity: 'SSR+', name: '原谅我吧🥺', pct: '0.2' },
      { rarity: 'SSR', name: '独角兽🦄', pct: '1' },
      { rarity: 'SSR', name: '为我服务👑', pct: '0.8' },
      { rarity: 'SSR', name: '机械核心⚙️', pct: '1.5' },
      { rarity: 'SSR', name: '星尘🌌', pct: '1.5' },
      { rarity: 'SR', name: '招财猫🐱', pct: '5' },
      { rarity: 'SR', name: '火花卡🔥', pct: '5' },
      { rarity: 'SR', name: '星光背景🌟', pct: '2' },
      { rarity: 'SR', name: '金元宝🪙/爱心箭🏹/月光石🌙/招财铃🎴', pct: '各4' },
      { rarity: 'R', name: '小狐狸🦊', pct: '10' },
      { rarity: 'R', name: '樱花背景🌸', pct: '3' },
      { rarity: 'R', name: '家务卡/我不要😤', pct: '1.5-3' },
      { rarity: 'N', name: '幸运饼干🍪', pct: '18' },
      { rarity: 'N', name: '切换卡🔄', pct: '14' },
      { rarity: 'N', name: '亲密糖果🍬', pct: '12' },
    ]
    this.setData({ probList })
  },

  onShow() {
    const userInfo = wx.getStorageSync('userInfo')
    if (!userInfo) { wx.reLaunch({ url: '/pages/login/login' }); return }
    this.loadTickets()
    this.setData({ userInfo })
  },

  /** 加载抽卡券数量 */
  async loadTickets() {
    try {
      const res = await api.getTickets()
      this.setData({ tickets: res.tickets || res.count || 0 })
    } catch (e) {
      console.error('加载抽卡券失败', e)
    }
  },

  /** 单抽 */
  async onDrawSingle() {
    if (this.data.drawing || this.data.tickets < 1) return
    this.setData({ drawing: true, animating: true, tenResults: [] })

    try {
      const res = await api.drawSingle()
      // 返回格式: { item: { name, rarity, desc }, tickets }
      const result = res.item || res
      this.showResult(result)

      // 更新券数
      this.setData({ tickets: res.tickets || this.data.tickets - 1 })
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
    if (this.data.drawing || this.data.tickets < 10) return
    this.setData({ drawing: true, animating: true })

    try {
      const res = await api.drawTen()
      // 返回格式: { items: [{ name, rarity, desc }...], tickets }
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
        tickets: res.tickets || this.data.tickets - 9
      })
    } catch (e) {
      console.error('十连失败', e)
      wx.showToast({ title: '抽卡失败，请重试', icon: 'none' })
    } finally {
      this.setData({ drawing: false })
      setTimeout(() => this.setData({ animating: false }), 800)
    }
  },

  /** 显示抽卡结果弹窗 */
  showResult(item) {
    const rarity = (item.rarity || 'N').toUpperCase()
    let animClass = 'resultAnimN'
    if (rarity === 'R') animClass = 'resultAnimR'
    else if (rarity === 'SR') animClass = 'resultAnimSR'
    else if (rarity === 'SSR') animClass = 'resultAnimSSR'
    else if (rarity === 'SSR+') animClass = 'resultAnimSSRP'

    this.setData({
      showResult: true,
      currentResult: { ...item, rarity, rarityClass: rarity === 'SSR+' ? 'SSRP' : rarity },
      resultAnimClass: animClass
    })
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
  }
})
