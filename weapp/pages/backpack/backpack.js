// pages/backpack/backpack.js — 背包 & 图鉴
const api = require('../../utils/api')

Page({
  data: {
    tab: 'backpack',
    items: [],
    groupedItems: [],
    pokedex: [],
    obtainedCount: 0
  },

  onShow() {
    this.load()
  },

  async load() {
    try {
      const [inventoryRes, petsRes] = await Promise.all([
        api.getInventory().catch(() => []),
        api.getPets().catch(() => ({ pets: [], active_pet: null }))
      ])

      const items = Array.isArray(inventoryRes) ? inventoryRes : (inventoryRes.items || [])
      const pets = (petsRes.pets || [])

      // 标记物品是否可使用（消耗品可点击使用）
      const markedItems = items.map(item => ({
        ...item,
        usable: (item.type === 'consumable' || item.type === 'food' || item.type === 'exp' || !item.type)
      }))

      // 按类型分组
      const groupedItems = this.groupItems(markedItems)

      // 构建图鉴数据
      const pokedex = this.buildPokedex(pets)
      const obtainedCount = pokedex.filter(p => p.obtained).length

      this.setData({ items: markedItems, groupedItems, pokedex, obtainedCount })
    } catch (e) { console.error('load backpack error:', e) }
  },

  /** 切换 TAB */
  switchTab(e) {
    const tab = e.currentTarget.dataset.tab
    this.setData({ tab })
  },

  /** 按类型分组物品 */
  groupItems(items) {
    const grouped = {}
    for (const item of items) {
      const type = item.type || 'other'
      if (!grouped[type]) grouped[type] = { type, list: [] }
      grouped[type].list.push(item)
    }

    // 排序：消耗品优先
    const order = ['consumable', 'food', 'exp', 'evolve', 'evolution', 'material', 'other']
    return order
      .filter(t => grouped[t])
      .map(t => grouped[t])
      .concat(Object.keys(grouped).filter(k => !order.includes(k)).map(k => grouped[k]))
  },

  /** 类型图标 */
  typeIcon(type) {
    const map = {
      consumable: '🍬',
      food: '🍎',
      exp: '⭐',
      evolve: '✨',
      evolution: '✨',
      material: '🧱',
      other: '📦'
    }
    return map[type] || '📦'
  },

  /** 类型中文名 */
  typeName(type) {
    const map = {
      consumable: '消耗品',
      food: '食物',
      exp: '经验道具',
      evolve: '进化道具',
      evolution: '进化道具',
      material: '材料',
      other: '其他'
    }
    return map[type] || type
  },

  /** 构建全图鉴数据 */
  buildPokedex(pets) {
    // 预定义所有可获得的宠物+形态
    const allPets = [
      { id: 'cat', name: '小猫咪', emoji: '🐱', forms: ['default', 'evolved_1', 'evolved_2'] },
      { id: 'dog', name: '小狗狗', emoji: '🐶', forms: ['default', 'evolved_1'] },
      { id: 'rabbit', name: '小兔子', emoji: '🐰', forms: ['default', 'evolved_1'] },
      { id: 'bear', name: '小熊熊', emoji: '🐻', forms: ['default', 'evolved_1'] },
      { id: 'fox', name: '小狐狸', emoji: '🦊', forms: ['default', 'evolved_1'] },
      { id: 'panda', name: '小熊猫', emoji: '🐼', forms: ['default'] },
      { id: 'owl', name: '猫头鹰', emoji: '🦉', forms: ['default', 'evolved_1'] },
      { id: 'dragon', name: '小龙', emoji: '🐉', forms: ['default', 'evolved_1', 'evolved_2', 'evolved_3'] },
    ]

    // 找出已获得的宠物 ID 集合
    const obtainedIds = new Set(pets.map(p => p.pet_id || p.id || p.name))

    const result = []
    for (const pet of allPets) {
      const obtained = obtainedIds.has(pet.id) || pets.some(p => (p.pet_id || p.id || p.name) === pet.id)
      result.push({
        ...pet,
        obtained,
        forms: pet.forms.map(form => ({
          form,
          obtained: obtained // 简化：拥有该宠物即视为该宠物所有形态已解锁
        }))
      })
    }
    return result
  },

  /** 使用物品 */
  async onUseItem(e) {
    const { id, name } = e.currentTarget.dataset
    if (!id) return

    // 找到物品检查是否可用
    const item = this.data.items.find(i => i.inventory_id === id)
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
          await api.useItem(id)
          wx.showToast({ title: '使用成功 ✨', icon: 'success' })
          this.load()
        } catch (e) {
          wx.showToast({ title: e.errMsg || '使用失败', icon: 'none' })
        }
      }
    })
  }
})
