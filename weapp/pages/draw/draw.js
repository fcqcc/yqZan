// pages/draw/draw.js — 今日签
const api = require('../../utils/api')

Page({
  data: {
    categories: [],
    selectedCatId: null,
    selectedCatName: '',
    selectedCatIcon: '',
    items: [],
    // 抽签状态
    drawing: false,
    showResult: false,
    resultContent: '',
    resultCatName: '',
    resultCatIcon: '',
    drawAnimClass: '',
    // 管理弹窗
    showAddForm: false,
    formContent: '',
    addTargetCatId: null,
    // 新建分类弹窗
    showAddCat: false,
    catFormName: '',
    catFormIcon: '📦',
    uiTheme: getApp().globalData.uiTheme || 'handdrawn',
  },

  onShow() {
    this.setData({ uiTheme: getApp().globalData.uiTheme || 'handdrawn' })
    this.loadCategories()
  },

  async loadCategories() {
    try {
      const cats = await api.request('/api/draw/categories')
      const list = Array.isArray(cats) ? cats : []
      this.setData({ categories: list })
      // 默认选中第一个
      if (list.length > 0 && !this.data.selectedCatId) {
        this.selectCategory(list[0])
      }
    } catch (e) {
      this.setData({ categories: [] })
    }
  },

  async selectCategory(cat) {
    this.setData({
      selectedCatId: cat.id,
      selectedCatName: cat.name,
      selectedCatIcon: cat.icon || '🎯',
      showResult: false,
      resultContent: '',
    })
    this.loadItems(cat.id)
  },

  onSelectCat(e) {
    const cat = this.data.categories.find(c => c.id === e.currentTarget.dataset.id)
    if (cat) this.selectCategory(cat)
  },

  async loadItems(categoryId) {
    try {
      const items = await api.request(`/api/draw/items?category_id=${categoryId}`)
      this.setData({ items: Array.isArray(items) ? items : [] })
    } catch (e) {
      this.setData({ items: [] })
    }
  },

  // ===== 抽签 =====
  async onDraw() {
    if (this.data.drawing || !this.data.selectedCatId) return
    this.setData({ drawing: true, drawAnimClass: 'draw-shake', showResult: false })

    // 抽签动画持续1.2秒
    await new Promise(r => setTimeout(r, 1200))

    try {
      const res = await api.request('/api/draw', 'POST', { category_id: this.data.selectedCatId })
      if (res && res.item) {
        this.setData({
          drawing: false,
          drawAnimClass: '',
          showResult: true,
          resultContent: res.item.content,
          resultCatName: res.item.category_name,
          resultCatIcon: res.item.category_icon || '🎯',
        })
        // 刷新条目列表（used_count可能变了）
        this.loadItems(this.data.selectedCatId)
        // 4秒后自动隐藏
        setTimeout(() => {
          if (this.data.showResult) {
            this.setData({ showResult: false })
          }
        }, 4000)
      }
    } catch (e) {
      this.setData({ drawing: false, drawAnimClass: '' })
      wx.showToast({ title: e.detail || '抽签失败', icon: 'none' })
    }
  },

  onHideResult() {
    this.setData({ showResult: false })
  },

  // ===== 添加条目 =====
  onShowAddForm() {
    if (!this.data.selectedCatId) {
      wx.showToast({ title: '请先选择一个分类', icon: 'none' })
      return
    }
    this.setData({
      showAddForm: true,
      formContent: '',
      addTargetCatId: this.data.selectedCatId,
    })
  },

  onHideAddForm() {
    this.setData({ showAddForm: false, formContent: '' })
  },

  async onAddItem() {
    const { formContent, addTargetCatId } = this.data
    if (!formContent.trim()) {
      wx.showToast({ title: '请填写内容', icon: 'none' })
      return
    }
    try {
      await api.request('/api/draw/items', 'POST', {
        category_id: addTargetCatId,
        content: formContent.trim(),
      })
      this.onHideAddForm()
      this.loadItems(addTargetCatId)
      wx.showToast({ title: '已添加 ✨', icon: 'none' })
    } catch (e) {
      wx.showToast({ title: e.detail || '添加失败', icon: 'none' })
    }
  },

  async onDeleteItem(e) {
    const id = e.currentTarget.dataset.id
    const item = this.data.items.find(i => i.id === id)
    if (!item) return
    if (!item.is_custom) {
      wx.showToast({ title: '预置条目不能删除', icon: 'none' })
      return
    }
    const r = await wx.showModal({ title: '删除', content: `删除「${item.content}」？` })
    if (!r.confirm) return
    try {
      await api.request(`/api/draw/items/${id}`, 'DELETE')
      this.loadItems(this.data.selectedCatId)
    } catch (e) {
      wx.showToast({ title: e.detail || '删除失败', icon: 'none' })
    }
  },

  // ===== 新建分类 =====
  onShowAddCat() {
    this.setData({ showAddCat: true, catFormName: '', catFormIcon: '📦' })
  },

  onHideAddCat() {
    this.setData({ showAddCat: false })
  },

  async onAddCategory() {
    const { catFormName, catFormIcon } = this.data
    if (!catFormName.trim()) {
      wx.showToast({ title: '请填写分类名称', icon: 'none' })
      return
    }
    try {
      await api.request('/api/draw/categories', 'POST', {
        name: catFormName.trim(),
        icon: catFormIcon.trim() || '📦',
      })
      this.onHideAddCat()
      this.loadCategories()
      wx.showToast({ title: '分类已创建 ✨', icon: 'none' })
    } catch (e) {
      wx.showToast({ title: e.detail || '创建失败', icon: 'none' })
    }
  },

  // catch tap to stop propagation
  catchTap() {},
})
