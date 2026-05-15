const api = require('../../utils/api')
Page({
  data: { todos: [], showForm: false, title: '', scopes: ['一起做', '自己做'], scopeIdx: 0 },
  onShow() { this.load() },
  async load() { try { const todos = await api.getTodos(); this.setData({ todos }) } catch(e) {} },
  toggleForm() { this.setData({ showForm: !this.data.showForm, title: '' }) },
  onScopeChange(e) { this.setData({ scopeIdx: e.detail.value }) },
  async create() {
    if (!this.data.title) return
    await api.createTodo({ title: this.data.title, scope: this.data.scopeIdx === 0 ? 'together' : 'alone' })
    this.toggleForm(); this.load()
  },
  async checkin(e) { await api.checkinTodo(e.currentTarget.dataset.id); this.load() }
})