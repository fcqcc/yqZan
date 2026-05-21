// pages/backpack/backpack.js — 背包 & 图鉴
const api = require('../../utils/api')

const CATEGORIES = ['全部', '消耗品', '卡牌', '进化道具', '配饰', '背景']
const ACH_CATEGORIES = ['全部', '打卡', '存钱', '宠物', '抽卡', '隐藏']

Page({
  data: {
    tab: 'backpack',
    backpackTab: '全部',
    categories: CATEGORIES,
    items: [],
    filteredItems: [],
    // 图鉴数据
    pokedexTab: 'pets',
    petsList: [],
    evolutionsList: [],
    itemsList: [],
    petsObtained: 0, petsTotal: 0,
    itemsObtained: 0, itemsTotal: 0,
    // 成就
    achCategories: ACH_CATEGORIES,
    achTab: '全部',
    achievements: [],
    filteredAch: [],
    achievementsUnlocked: 0,
    crystalBalance: 0,
    exchangeList: [],
  },

  onShow() {
    this.load()
    this.loadCrystals()
  },

  async load() {
    try {
      const [inventoryRes, bestiaryRes] = await Promise.all([
        api.getInventory().catch(() => []),
        api.getBestiary().catch(() => ({})),
      ])

      const inventory = Array.isArray(inventoryRes) ? inventoryRes : (inventoryRes.items || [])
      const bestiary = bestiaryRes

      const marked = inventory.map(item => ({
        ...item,
        usable: item.item_type === 'consumable' && item.item_id !== 'switch_card',
      }))
      const filtered = this.filterByCategory(marked, this.data.backpackTab)

      // 成就
      let achievements = []
      if (bestiary.achievements && bestiary.achievements.length > 0) {
        achievements = bestiary.achievements
      } else {
        try {
          const achRes = await api.getAchievements()
          achievements = achRes.achievements || []
        } catch(e) {}
      }

      const sortByRarity = (a, b) => {
        const order = { N: 0, R: 1, SR: 2, SSR: 3, 'SSR+': 4 }
        return (order[a.rarity] || 0) - (order[b.rarity] || 0)
      }
      const petsList = (bestiary.pets || []).sort(sortByRarity)
      const itemsList = (bestiary.items || []).sort(sortByRarity)

      const filteredAch = this.filterAch(achievements, this.data.achTab)

      this.setData({
        items: marked,
        filteredItems: filtered,
        petsList,
        evolutionsList: bestiary.evolutions || [],
        itemsList,
        petsObtained: petsList.filter(p => p.obtained).length,
        petsTotal: petsList.length,
        itemsObtained: itemsList.filter(i => i.obtained).length,
        itemsTotal: itemsList.length,
        achievements,
        filteredAch,
        achievementsUnlocked: achievements.filter(a => a.unlocked).length,
      })
    } catch (e) { console.error('load backpack error:', e) }
  },

  // ===== TAB 切换 =====

  switchTab(e) {
    this.setData({ tab: e.currentTarget.dataset.tab })
  },

  switchBackpackTab(e) {
    const cat = e.currentTarget.dataset.cat
    const filtered = this.filterByCategory(this.data.items, cat)
    this.setData({ backpackTab: cat, filteredItems: filtered })
  },

  switchPokedexTab(e) {
    this.setData({ pokedexTab: e.currentTarget.dataset.tab })
  },

  switchAchTab(e) {
    const cat = e.currentTarget.dataset.cat
    const filteredAch = this.filterAch(this.data.achievements, cat)
    this.setData({ achTab: cat, filteredAch })
  },

  // ===== 辅助 =====

  filterByCategory(items, cat) {
    if (!cat || cat === '全部') return items
    return items.filter(i => (i.type_display || '') === cat)
  },

  filterAch(achievements, cat) {
    if (!cat || cat === '全部') return achievements
    return achievements.filter(a => (a.category || '') === cat)
  },

  // ===== 使用物品 =====

  async onUseItem(e) {
    const itemId = e.currentTarget.dataset.id
    const name = e.currentTarget.dataset.name
    if (!itemId) return

    const item = this.data.items.find(i => i.id === itemId)
    if (!item || !item.usable) {
      wx.showToast({ title: '该物品无法直接使用', icon: 'none' })
      return
    }

    wx.showModal({
      title: '使用物品',
      content: `确定使用「${name || item.name}」吗？`,
      success: async (res) => {
        if (!res.confirm) return
        try {
          const result = await api.useItem(itemId)
          const msg = result.effect || result.message || '使用成功 ✨'
          wx.showToast({ title: msg, icon: 'none', duration: 2000 })
          this.load()
        } catch (e) {
          wx.showToast({ title: e.errMsg || '使用失败', icon: 'none' })
        }
      },
    })
  },
  switchTab(e) {
    this.setData({ tab: e.currentTarget.dataset.tab })
    if (e.currentTarget.dataset.tab === 'crystals') this.loadCrystals()
  },

  async loadCrystals() {
    try {
      const res = await api.request('/api/gacha/crystals')
      this.setData({ crystalBalance: res.balance || 0, exchangeList: res.exchange_list || [] })
    } catch (e) {
      console.error('加载晶石失败', e)
    }
  },

  onExchange(e) {
    const { item_id, name, cost } = e.currentTarget.dataset
    if (this.data.crystalBalance < cost) {
      wx.showToast({ title: '晶石不足', icon: 'none' })
      return
    }
    wx.showModal({
      title: '确认兑换',
      content: `消耗 ${cost} 晶石兑换「${name}」？`,
      success: async (res) => {
        if (!res.confirm) return
        try {
          const result = await api.request('/api/gacha/crystals/exchange', 'POST', { item_id })
          wx.showToast({ title: `兑换成功！获得「${result.item_name}」`, icon: 'none' })
          this.loadCrystals()
          this.load()
        } catch (e) {
          wx.showToast({ title: e.detail || e.errMsg || '兑换失败', icon: 'none' })
        }
      },
    })
  },
})
