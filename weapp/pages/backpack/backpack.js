// pages/backpack/backpack.js — 背包 & 图鉴
const api = require('../../utils/api')

const CATEGORIES = ['全部', '消耗品', '卡牌', '进化道具', '配饰', '背景']

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
    // 成就数据
    achievements: [],
    achievementsUnlocked: 0,
  },

  onShow() {
    this.load()
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

  // ===== 辅助 =====

  filterByCategory(items, cat) {
    if (!cat || cat === '全部') return items
    return items.filter(i => (i.type_display || '') === cat)
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
})
