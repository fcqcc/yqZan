const api = require('../../utils/api')

const STICKERS = ['😀','😍','🥰','😘','😚','🤗','😋','🥺','😢','😭','😡','😤','🤔','😴','🤤','🥳']
const CARD_COLORS = ['pink', 'yellow', 'purple', 'blue', 'orange']
const AVATAR_COLORS = { pink: '#F9A85C', yellow: '#C49B00', purple: '#B19CD9', blue: '#7BC4E8', orange: '#FF8E53' }

function pad(n) { return n < 10 ? '0' + n : '' + n }

function formatTime(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr.slice(11, 16) || ''
  const now = new Date()
  const diffMin = Math.round((now - d) / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return diffMin + ' 分钟前'
  if (diffMin < 1440) return Math.floor(diffMin / 60) + ' 小时前'
  return `${pad(d.getMonth()+1)}月${pad(d.getDate())}日 ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

Page({
  data: {
    notes: [],
    todayNotes: [],
    yesterdayNotes: [],
    olderNotes: [],
    yesterdayDateStr: '',
    content: '',
    showSticker: false,
    stickers: STICKERS,
    userInfo: {},
    uiTheme: getApp().globalData.uiTheme || 'handdrawn',
  },

  onShow() {
    this.setData({ uiTheme: getApp().globalData.uiTheme || 'handdrawn' })
    const userInfo = wx.getStorageSync('userInfo') || {}
    this.setData({ userInfo })
    this.load()
  },

  /** 点击输入栏 → 弹出表情面板 */
  onInputBarTap() {
    this.setData({ showSticker: true })
  },

  /** 输入框聚焦 → 弹出表情面板 */
  onInputFocus() {
    this.setData({ showSticker: true })
  },

  toggleSticker() {
    this.setData({ showSticker: !this.data.showSticker })
  },

  onPickSticker(e) {
    const sticker = e.currentTarget.dataset.sticker
    this.setData({ content: this.data.content + sticker })
  },

  async fetchNotes() {
    const userInfo = wx.getStorageSync('userInfo') || {}
    const uid = userInfo && userInfo.id
    const r = await api.getNotes()
    const rawList = Array.isArray(r) ? r : (r.notes || [])
    const now = new Date()
    const todayStr = `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())}`
    const yesterdayD = new Date(now)
    yesterdayD.setDate(yesterdayD.getDate() - 1)
    const yesterdayStr = `${yesterdayD.getFullYear()}-${pad(yesterdayD.getMonth()+1)}-${pad(yesterdayD.getDate())}`

    const withMeta = rawList.map((n, i) => {
      const created = n.created_at || ''
      const datePart = String(created).slice(0, 10)
      const timeLabel = formatTime(created)
      const colorIdx = (n.id || i) % CARD_COLORS.length
      const colorClass = CARD_COLORS[colorIdx]
      return {
        ...n,
        isMine: n.user_id === uid,
        datePart,
        timeLabel,
        colorClass,
        avatarColor: AVATAR_COLORS[colorClass],
        liked: n.liked || false,
        likes: n.likes || 0,
      }
    })

    // 按日期分组
    const todayNotes = withMeta.filter(n => n.datePart === todayStr)
    const yesterdayNotes = withMeta.filter(n => n.datePart === yesterdayStr)
    const olderNotes = withMeta.filter(n => n.datePart !== todayStr && n.datePart !== yesterdayStr)

    this.setData({
      notes: withMeta,
      todayNotes,
      yesterdayNotes,
      olderNotes,
      yesterdayDateStr: `${yesterdayD.getMonth()+1}月${yesterdayD.getDate()}日`,
      showSticker: false,
    })
  },

  async load() {
    try {
      await this.fetchNotes()
    } catch (e) {}
  },

  async send() {
    const content = this.data.content.trim()
    if (!content) return
    wx.showLoading({ title: '贴上去...' })
    try {
      await api.createNote(content)
      await this.fetchNotes()
      wx.hideLoading()
      this.setData({ content: '' })
      try { wx.vibrateShort({ type: 'light' }) } catch (e) {}
      wx.showToast({ title: '已贴上 💕', icon: 'none' })
    } catch (e) { wx.hideLoading() }
  },

  async like(e) {
    await api.likeNote(e.currentTarget.dataset.id)
    this.load()
  },

  async del(e) {
    const id = e.currentTarget.dataset.id
    const r = await wx.showModal({ title: '删除', content: '确定删除这条留言？' })
    if (!r.confirm) return
    try {
      await api.deleteNote(id)
      wx.showToast({ title: '已删除', icon: 'none' })
      this.load()
    } catch (e) { wx.showToast({ title: '删除失败', icon: 'none' }) }
  },
})
