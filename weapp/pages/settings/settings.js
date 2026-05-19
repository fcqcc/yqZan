// pages/settings/settings.js
const api = require('../../utils/api')
const theme = require('../../utils/theme')

function firstChar(name) {
  const s = (name || '').trim()
  if (!s) return '?'
  return s.slice(0, 1)
}

Page({
  data: {
    tabBarIndex: 2,
    userInfo: null,
    partner: null,
    inviteCodeInput: '',
    level: 1,
    expPercent: 0,
    myAvatar: '',
    partnerAvatar: '',
    myInitial: '?',
    partnerInitial: '?',
    coupleTitle: '',
    partnerLine: '等待绑定',
    progressActive: '#D65C8A',
    progressBg: 'rgba(214, 92, 138, 0.16)'
  },

  onShow() {
    const userInfo = wx.getStorageSync('userInfo') || null
    if (!userInfo) {
      wx.reLaunch({ url: '/pages/login/login' })
      return
    }
    this.setData({
      userInfo,
      myInitial: firstChar(userInfo && userInfo.nickname),
      coupleTitle: userInfo ? userInfo.nickname : '',
      ...theme.progressColors()
    })
    this.loadPartner()
    this.loadLevel()
  },

  async loadLevel() {
    try {
      const lvl = await api.getLevel()
      const pct = Math.min(100, Math.max(0, Number(lvl.progress_pct) || 0))
      this.setData({
        level: lvl.level != null ? lvl.level : 1,
        expPercent: pct
      })
    } catch (e) {
      this.setData({ level: 1, expPercent: 0 })
    }
  },

  async loadPartner() {
    const userInfo = this.data.userInfo || wx.getStorageSync('userInfo') || {}
    try {
      const partner = await api.getPartner()
      const partnerLine = partner ? partner.nickname : '等待绑定'
      const coupleTitle = partner
        ? `${userInfo.nickname || '我'} & ${partner.nickname}`
        : userInfo.nickname || '我'
      this.setData({
        partner,
        partnerLine,
        coupleTitle,
        partnerInitial: partner ? firstChar(partner.nickname) : '?',
        partnerAvatar: partner && partner.avatar_url ? partner.avatar_url : '',
        myAvatar: userInfo.avatar_url || ''
      })
    } catch (e) {
      this.setData({
        partner: null,
        partnerLine: '等待绑定',
        coupleTitle: userInfo.nickname || '我',
        partnerInitial: '?',
        partnerAvatar: '',
        myAvatar: userInfo.avatar_url || ''
      })
    }
  },

  editNickname() {
    const u = this.data.userInfo
    if (!u) return
    wx.showModal({
      title: '修改昵称',
      editable: true,
      placeholderText: u.nickname || '',
      success: (res) => {
        if (!res.confirm) return
        const name = (res.content || '').trim()
        if (!name) {
          wx.showToast({ title: '昵称不能为空', icon: 'none' })
          return
        }
        const userInfo = { ...u, nickname: name }
        wx.setStorageSync('userInfo', userInfo)
        getApp().globalData.userInfo = userInfo
        this.setData({
          userInfo,
          myInitial: firstChar(name),
          coupleTitle: this.data.partner ? `${name} & ${this.data.partner.nickname}` : name
        })
        wx.showToast({ title: '已保存', icon: 'success' })
      }
    })
  },

  copyInviteCode() {
    const code = this.data.userInfo && this.data.userInfo.invite_code
    if (!code) {
      wx.showToast({ title: '暂无邀请码', icon: 'none' })
      return
    }
    wx.setClipboardData({ data: String(code) })
  },

  viewPartner() {
    const { partner } = this.data
    if (!partner) {
      wx.showToast({ title: '请先绑定伴侣', icon: 'none' })
      return
    }
    wx.showModal({
      title: '我的伴侣',
      content: partner.nickname || 'Ta',
      showCancel: false
    })
  },

  goToAchievements() {
    wx.navigateTo({ url: '/pages/level/level' })
  },

  goToAnniversaries() {
    wx.navigateTo({ url: '/pages/anniversaries/anniversaries' })
  },

  goToWallet() {
    wx.navigateTo({ url: '/pages/plans/plans' })
  },

  goToAbout() {
    wx.showModal({
      title: '一起攒',
      content: '情侣共同存钱计划，攒下每一份心意。记录目标、追踪进度、一起实现。',
      showCancel: false
    })
  },

  async handleBind() {
    const code = (this.data.inviteCodeInput || '').trim().toUpperCase()
    if (!code) {
      wx.showToast({ title: '请输入对方的邀请码', icon: 'none' })
      return
    }
    if (code.length !== 6) {
      wx.showToast({ title: '邀请码为6位', icon: 'none' })
      return
    }
    wx.showLoading({ title: '绑定中' })
    try {
      const res = await api.bindPartner(code)
      wx.hideLoading()
      wx.showToast({ title: '🎉 绑定成功！', icon: 'none' })
      this.setData({ inviteCodeInput: '' })
      this.loadPartner()
      wx.switchTab({ url: '/pages/home/home' })
    } catch (e) {
      wx.hideLoading()
      // 后端返回的 detail 消息
      const msg = (e && (e.detail || e.message)) || '绑定失败，请检查邀请码'
      wx.showModal({
        title: '绑定失败',
        content: String(msg),
        showCancel: false
      })
    }
  },

  async unbindPartner() {
    const r = await wx.showModal({
      title: '确认解绑？',
      content: '⚠️ 解绑后双方数据分离，各自拥有新存钱空间。\n\n若以后重新绑定，之前的共享数据不会恢复。\n\n确定要解绑吗？',
    })
    if (!r.confirm) return
    try {
      await api.unbindPartner()
      wx.showToast({ title: '已解绑', icon: 'success' })
      this.loadPartner()
    } catch (e) {
      wx.showToast({ title: '操作失败', icon: 'none' })
    }
  },

  logout() {
    wx.removeStorageSync('token')
    wx.removeStorageSync('userInfo')
    getApp().globalData.token = ''
    getApp().globalData.userInfo = null
    wx.reLaunch({ url: '/pages/login/login' })
  }
})
