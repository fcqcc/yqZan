// pages/pets/pets.js — 宠物管理
const api = require('../../utils/api')

function getFullImageUrl(path) {
  if (!path) return ''
  return getApp().globalData.baseUrl + path
}

/** 宠物类型 → 进化道具 ID 映射 */
const EVOLUTION_ITEM_FOR_PET = {
  star_fox: 'star_ribbon',
  bamboo_dragon: 'bamboo_sword',
  wave_cat: 'sea_crown',
  honey_bear: 'rainbow_cape',
}

Page({
  data: {
    pets: [],
    activePet: null,
    intimacyPct: 0,
    forms: [],
    canEvolve: false,
    inventory: [],
    intimacyStageName: '初识',
    intimacyStageDesc: '',
    petCatalog: null,  // 后端获取的宠物配置
    petHappyClass: '',  // 互动动画class
    lastInteractTime: 0,  // 防抖时间戳
    todayInteractTotal: 0,
    showEvoEffect: false,  // 进化粒子特效
    uiTheme: getApp().globalData.uiTheme || 'handdrawn',
    petTalkBubble: '',
  },

  onShow() {
    this.setData({ uiTheme: getApp().globalData.uiTheme || 'handdrawn' })
    this.load()
    this.loadCatalog()
  },

  async loadCatalog() {
    try {
      const cat = await api.getPetCatalog()
      this.setData({ petCatalog: cat.pet_types || [] })
    } catch (e) {}
  },

  async load() {
    try {
      const [petsRes, inventory] = await Promise.all([
        api.getPets().catch(() => ({ pets: [], active_pet: null })),
        api.getInventory().catch(() => [])
      ])

      const petsArr = Array.isArray(petsRes) ? petsRes : (petsRes.pets || [])
      const activePetFromApi = Array.isArray(petsRes) ? null : (petsRes.active_pet || null)

      const pets = petsArr.map(p => ({
        ...p,
        active: p.is_active,
        full_image_url: getFullImageUrl(p.image_url),
      }))
      let activePet = activePetFromApi
        ? { ...activePetFromApi, full_image_url: getFullImageUrl(activePetFromApi.image_url) }
        : null
      if (!activePet) {
        activePet = pets.find(p => p.is_active) || pets[0] || null
      }
      const intimacyPct = activePet ? Math.min(100, Math.round(activePet.intimacy || 0)) : 0

      // 构建形态列表（从所有宠物中提取已解锁的形态）
      const forms = this.buildForms(pets, activePet)

      const items = Array.isArray(inventory) ? inventory : (inventory.items || [])

      // 判断是否已达到最终形态
      const isSSR = activePet?.rarity === 'SSR'
      const isSR = activePet?.rarity === 'SR'
      const isR = activePet?.rarity === 'R'
      const curForm = activePet?.current_form || ''
      const isSSRAtFinal = isSSR && (curForm === 'deluxe' || curForm === 'legend')
      const isSRAtFinal = isSR && curForm === 'adult'
      const isRAtFinal = isR && curForm === 'teen'
      const atFinalForm = isSSRAtFinal || isSRAtFinal || isRAtFinal

      // 🔥 道具进化：SSR ≥ 15级 + 有进化道具 + 未到最终形态
      const canItemEvolve = activePet
        && isSSR
        && !atFinalForm
        && activePet.level >= 15
        && items.some(item => item.item_type === 'evolution_item')

      // 🔥 等级进化：evolution_ready，但SSR满15级没有等级进化，且未到最终形态
      const canLevelEvolve = activePet
        && activePet.evolution_ready
        && !atFinalForm
        && !(isSSR && activePet.level >= 15)

      // 当前显示的进化按钮（仅用于兼容旧引用）
      const canEvolve = canItemEvolve

      // 计算亲密度阶段
      let stageName = '初识'
      let stageDesc = '继续培养感情吧～'
      if (activePet) {
        const lvl = activePet.intimacy_level || ''
        if (lvl === 'low') { stageName = '初识🤝'; stageDesc = '还有点陌生，多互动会慢慢熟悉' }
        else if (lvl === 'normal') { stageName = '熟悉😊'; stageDesc = '已经开始依赖你了，继续保持' }
        else if (lvl === 'happy') { stageName = '亲密🥰'; stageDesc = '你们之间有了深厚的感情' }
        else if (lvl === 'love') { stageName = '挚爱💕'; stageDesc = '心意相通，默契无间！' }
      }

      this.setData({
        pets, activePet, intimacyPct, forms, canEvolve, canItemEvolve, canLevelEvolve,
        inventory: items, intimacyStageName: stageName, intimacyStageDesc: stageDesc,
        todayInteractTotal: activePet ? (activePet.today_interact_count || 0) : 0,
      })
    } catch (e) { console.error('load pets error:', e) }
  },

  /**
   * 从宠物数据中构建形态列表
   * 假设宠物数据结构中有 forms 字段，或者从宠物列表推断
   */
  buildForms(pets, activePet) {
    if (!pets || pets.length === 0) return []
    // 构建稳定形态列表（固定emoji映射，切换形态时不闪烁）
    const EMOJI_MAP = {
      'baby': '🐣', 'teen': '🌟', 'adult': '✨', 'deluxe': '💎', 'legend': '👑'
    }
    // 直接从 activePet.forms（后端返回的表单列表）取名称
    if (activePet && activePet.forms && activePet.forms.length > 0) {
      const apiForms = {}
      for (const f of activePet.forms) {
        apiForms[f.form] = { name: f.name, unlocked: f.unlocked }
      }
      const unlocked = activePet.unlocked_forms || ['baby']
      return unlocked.map(f => {
        const info = apiForms[f] || {}
        const name = info.name || f
        const isBranch = f.startsWith('branch_')
        const emoji = isBranch ? '🔀' : (EMOJI_MAP[f] || activePet.emoji || '🐾')
        return { form: f, name, emoji, unlocked: info.unlocked !== false }
      })
    }
    return pets.map(p => ({
      form: p.current_form || 'baby',
      name: p.form_label || p.current_form,
      emoji: p.emoji || '🐾',
      unlocked: true,
    }))
  },

  /** 格式化形态显示名 */
  formLabel(form) {
    // 已废弃，保留兼容
    return form
  },

  /** 切换活跃宠物 */
  async onSwitchPet(e) {
    const petId = e.currentTarget.dataset.id
    if (!petId) return
    try {
      await api.switchPet(petId)
      wx.showToast({ title: '切换成功', icon: 'success' })
      this.load()
    } catch (e) {
      wx.showToast({ title: e.detail || e.errMsg || '切换失败', icon: 'none' })
    }
  },

  /** 切换宠物形态 */
  async onSwitchForm(e) {
    const form = e.currentTarget.dataset.form
    const activePet = this.data.activePet
    if (!activePet || !form || form === activePet.current_form) return
    try {
      await api.switchPetForm(activePet.id, form)
      wx.showToast({ title: '形态切换成功', icon: 'success' })
      this.load()
    } catch (e) {
      wx.showToast({ title: e.errMsg || '切换失败', icon: 'none' })
    }
  },

  /** 喂食宠物 */
  async onFeed() {
    const pet = this.data.activePet
    if (!pet) return
    try {
      await api.feedPet(pet.id)
      wx.showToast({ title: '喂食成功 ❤️', icon: 'success' })
      this.load()
    } catch (e) {
      const msg = e._statusCode === 429 ? (e.detail || '今天已经喂过了') : (e.detail || e.errMsg || '喂食失败')
      wx.showToast({ title: msg, icon: 'none' })
    }
  },

  /** 玩耍宠物 */
  async onPlay() {
    const pet = this.data.activePet
    if (!pet) return
    this.setData({ petHappyClass: 'pet-happy' })
    setTimeout(() => this.setData({ petHappyClass: '' }), 700)
    try {
      await api.petPet(pet.id)
      wx.showToast({ title: '🎾 玩得很开心！', icon: 'none' })
      this.load()
    } catch (e) {
      const msg = e._statusCode === 429 ? (e.detail || '今天已经玩过了') : (e.detail || e.errMsg || '玩耍失败')
      wx.showToast({ title: msg, icon: 'none' })
    }
  },

  /** 走动宠物 */
  async onWalkPet() {
    const pet = this.data.activePet
    if (!pet) return
    this.setData({ petHappyClass: 'pet-walk-anim' })
    setTimeout(() => this.setData({ petHappyClass: '' }), 800)
    try {
      await api.walkPet(pet.id)
      wx.showToast({ title: '🚶 散步归来~', icon: 'none' })
      this.load()
    } catch (e) {
      const msg = e._statusCode === 429 ? (e.detail || '今天已经走过了') : (e.detail || e.errMsg || '走动失败')
      wx.showToast({ title: msg, icon: 'none' })
    }
  },

  /** 进化宠物 + 粒子特效 */
  async onEvolve() {
    const pet = this.data.activePet
    if (!pet) return

    // 找到对应宠物类型的进化道具
    const expectedItemId = EVOLUTION_ITEM_FOR_PET[pet.pet_type]
    if (!expectedItemId) {
      wx.showToast({ title: '该宠物无法进化', icon: 'none' })
      return
    }
    const evolveItem = this.data.inventory.find(item =>
      item.item_type === 'evolution_item' && item.item_id === expectedItemId
    )
    if (!evolveItem) {
      wx.showToast({ title: '没有对应的进化道具', icon: 'none' })
      return
    }

    wx.showModal({
      title: '确认进化',
      content: `消耗 1 个「${evolveItem.name || '进化道具'}」，进化 ${pet.form_label || '宠物'}？`,
      success: async (res) => {
        if (!res.confirm) return
        // 🎆 先播进化动画
        this.setData({ showEvoEffect: true })
        await new Promise(r => setTimeout(r, 3000))
        this.setData({ showEvoEffect: false })
        try {
          await api.evolvePet(pet.id, evolveItem.item_id)
          wx.showToast({ title: '✨ 进化成功！', icon: 'none' })
          this.load()
        } catch (e) {
          this.setData({ showEvoEffect: false })
          wx.showToast({ title: e.detail || e.errMsg || '进化失败', icon: 'none' })
        }
      }
    })
  },
  /** 点击技能标签 → 展示技能效果描述 */
  onSkillTap() {
    const pet = this.data.activePet
    if (!pet || !pet.passive_skill) return
    wx.showModal({
      title: `🎯 ${pet.passive_skill}`,
      content: pet.passive_skill_desc || '每天首次登录时触发冒险，带回收益',
      confirmText: '知道了',
      showCancel: false,
    })
  },

  /** 点击宠物卡片→随机互动特效（纯前端，不调后端） */
  onPetTap() {
    const pet = this.data.activePet
    if (!pet) return
    const now = Date.now()
    if (now - this.data.lastInteractTime < 600) return
    const anims = ['pet-happy', 'pet-fan-shake', 'pet-violent-shake', 'pet-wild-move', 'pet-talk-anim']
    const anim = anims[Math.floor(Math.random() * anims.length)]
    this.setData({ petHappyClass: anim, lastInteractTime: now })
    setTimeout(() => { this.setData({ petHappyClass: '' }) }, 700)
    // 触发对话
    api.talkPet(pet.id).then(res => {
      if (res && res.talk) {
        this.setData({ petTalkBubble: res.talk })
        this._talkTimer && clearTimeout(this._talkTimer)
        this._talkTimer = setTimeout(() => {
          this.setData({ petTalkBubble: '' })
        }, 3500)
      }
    }).catch(() => {})
  },

  /** 等级进化（每5级手动确认）+ 粒子特效 */
  async onLevelEvolve() {
    const pet = this.data.activePet
    if (!pet || !pet.evolution_ready) return
    // 🎆 先播进化动画（5秒）
    this.setData({ showEvoEffect: true })
    await new Promise(r => setTimeout(r, 3000))
    this.setData({ showEvoEffect: false })
    try {
      await api.request(`/api/pets/${pet.id}/level-evolve`, 'POST')
      wx.showToast({ title: '✨ 进化成功！', icon: 'none' })
      this.load()
    } catch (e) {
      this.setData({ showEvoEffect: false })
      wx.showToast({ title: e.detail || e.errMsg || '进化失败', icon: 'none' })
    }
  },
})
