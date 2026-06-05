// pages/calendar/calendar.js — 日历（对接后端数据）
const api = require('../../utils/api')

const WEEKDAYS = [
  { label: '日', isWeekend: true },
  { label: '一', isWeekend: false },
  { label: '二', isWeekend: false },
  { label: '三', isWeekend: false },
  { label: '四', isWeekend: false },
  { label: '五', isWeekend: false },
  { label: '六', isWeekend: true },
];
const WEEKDAY_LABELS_FULL = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];
const QUICK_AMOUNTS = [10, 20, 50, 100, 200, 500];

function pad(n) { return n < 10 ? '0' + n : '' + n; }
function dateStr(d) { return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; }
function daysBetween(d1, d2) { return Math.round((d2 - d1) / 86400000); }

Page({
  data: {
    uiTheme: getApp().globalData.uiTheme || 'handdrawn',
    weekdays: WEEKDAYS,
    currentYear: 0,
    currentMonth: 0,
    currentMonthText: '',
    weekdayFirstText: '',
    isCurrentMonth: true,
    calendarDays: [],
    selectedDate: '',
    selectedDay: 0,
    selectedWeekday: '',
    selectedDateLabel: '',
    selectedRelative: '',
    selectedIsToday: false,
    selectedAnnivs: [],
    selectedSavings: [],
    selectedNotes: [],
    selectedTotal: '0',
    monthTotal: '0',
    monthSavingsCount: 0,
    monthAnnivCount: 0,
    showAdd: false,
    addDateLabel: '',
    addDraft: { amount: '', planId: '', note: '' },
    plans: [],
    quickAmounts: QUICK_AMOUNTS,
    showAddAnniv: false,
    addAnnivTitle: '',
    _anniversaries: [],
    _savings: [],
    _notes: [],
  },

  onLoad() {
    this.loadData();
    const today = new Date();
    this.setCurrentMonth(today.getFullYear(), today.getMonth() + 1);
    this.setData({ selectedDate: dateStr(today) });
    this.refreshSelected();
  },

  onShow() {
    this.setData({ uiTheme: getApp().globalData.uiTheme || 'handdrawn' });
    this.loadData();
  },

  async loadData() {
    try {
      const [annivs, plansRes, notesRes] = await Promise.all([
        api.getAnniversaries().catch(() => []),
        api.getPlans().catch(() => []),
        api.getNotes().catch(() => []),
      ]);

      // 纪念日
      const _anniversaries = Array.isArray(annivs) ? annivs.map(a => ({
        id: a.id,
        name: a.title,
        icon: a.icon || '💕',
        color: a.color || '#F9A85C',
        date: a.date_val,
        recurring: a.recurring !== false,
        isBirthday: a.is_birthday || false,
      })) : [];

      // 存钱计划列表（仅进行中）
      const plansRaw = Array.isArray(plansRes) ? plansRes : (plansRes && plansRes.plans ? plansRes.plans : [])
      const _plans = plansRaw.filter(p => !p.done).map(p => ({
        id: p.id,
        name: p.title,
        icon: p.icon || '💰',
      }));

      // 存钱明细：从每个计划的 deliveries 字段提取
      let _savings = [];
      for (const plan of plansRaw) {
        const dels = plan.deliveries || []
        dels.forEach(d => {
          let dDate = ''
          if (d.created_at) dDate = String(d.created_at).slice(0, 10)
          else if (d.date) dDate = d.date
          if (!dDate) return
          _savings.push({
            id: 'd_' + d.id,
            date: dDate,
            amount: Number(d.amount || 0),
            planId: plan.id,
            planName: plan.title,
            planIcon: plan.icon || '💰',
            note: d.note || '',
          })
        })
      }

      // 留言
      const _notes = Array.isArray(notesRes) ? notesRes.map(n => ({
        id: n.id,
        content: n.content,
        date: n.created_at ? String(n.created_at).slice(0, 10) : '',
        userId: n.user_id,
        isMine: n.user_id === (getApp().globalData.userInfo || {}).id,
      })).filter(n => n.date) : [];

      this.setData({
        _anniversaries,
        _savings,
        _notes,
        plans: _plans,
      });
      this.refreshCalendar();
      this.refreshSelected();
    } catch(e) { console.error('loadData error', e) }
  },

  setCurrentMonth(year, month) {
    const today = new Date();
    const isCurrent = (year === today.getFullYear() && month === today.getMonth() + 1);
    const firstDay = new Date(year, month - 1, 1);
    const weekdayFirst = WEEKDAY_LABELS_FULL[firstDay.getDay()];

    this.setData({
      currentYear: year,
      currentMonth: month,
      currentMonthText: month + '月',
      weekdayFirstText: weekdayFirst + '开始',
      isCurrentMonth: isCurrent,
    });
    this.refreshCalendar();
    this.refreshMonthStats();
  },

  refreshCalendar() {
    const { currentYear: y, currentMonth: m } = this.data;
    const todayStrNow = dateStr(new Date());

    const firstDay = new Date(y, m - 1, 1);
    const firstDayOfWeek = firstDay.getDay();
    const daysInMonth = new Date(y, m, 0).getDate();
    const daysInPrevMonth = new Date(y, m - 1, 0).getDate();

    const cells = [];

    // 上月补位
    for (let i = firstDayOfWeek - 1; i >= 0; i--) {
      const d = daysInPrevMonth - i;
      const prevM = m - 1;
      const prevY = prevM === 0 ? y - 1 : y;
      const prevMM = prevM === 0 ? 12 : prevM;
      const date = `${prevY}-${pad(prevMM)}-${pad(d)}`;
      const cellData = this.buildCellData(date, d, false, todayStrNow);
      cells.push(cellData);
    }

    // 当月
    for (let d = 1; d <= daysInMonth; d++) {
      const date = `${y}-${pad(m)}-${pad(d)}`;
      const cellData = this.buildCellData(date, d, true, todayStrNow);
      cells.push(cellData);
    }

    // 下月补位（凑齐 42 个）
    const remaining = 42 - cells.length;
    for (let d = 1; d <= remaining; d++) {
      const nextM = m + 1;
      const nextY = nextM === 13 ? y + 1 : y;
      const nextMM = nextM === 13 ? 1 : nextM;
      const date = `${nextY}-${pad(nextMM)}-${pad(d)}`;
      const cellData = this.buildCellData(date, d, false, todayStrNow);
      cells.push(cellData);
    }

    this.setData({ calendarDays: cells });
  },

  buildCellData(date, day, isCurrentMonth, todayStrNow) {
    const isToday = date === todayStrNow;
    const future = date > todayStrNow;
    const annivs = this.findAnniversariesForDate(date);
    const savingsForDate = this.data._savings.filter(s => s.date === date);
    const hasSavings = savingsForDate.length > 0;
    const savingsTotal = savingsForDate.reduce((sum, s) => sum + Number(s.amount || 0), 0);

    const firstAnniv = annivs[0] || null;

    return {
      date,
      day,
      isCurrentMonth,
      isToday,
      isFuture: future,
      hasAnniv: annivs.length > 0,
      firstAnnivIcon: firstAnniv ? firstAnniv.icon : '',
      firstAnnivColor: firstAnniv ? firstAnniv.color : '',
      hasSavings,
      savingsTotal: hasSavings ? savingsTotal : 0,
    };
  },

  findAnniversariesForDate(date) {
    const [y, m, d] = date.split('-').map(Number);
    const matched = [];
    this.data._anniversaries.forEach(a => {
      const [ay, am, ad] = a.date.split('-').map(Number);
      if (a.recurring) {
        if (am === m && ad === d) {
          matched.push(this.enrichAnniv(a, date));
        }
      } else {
        if (a.date === date) {
          matched.push(this.enrichAnniv(a, date));
        }
      }
    });
    return matched;
  },

  enrichAnniv(anniv, date) {
    const today = new Date();
    const target = new Date(date);
    const diff = daysBetween(today, target);
    let daysNum, daysUnit, daysColor, metaText;

    if (diff === 0) {
      daysNum = '今';
      daysUnit = '天!';
      daysColor = '#F9A85C';
      metaText = '就是今天 🎉';
    } else if (diff > 0) {
      daysNum = String(diff);
      daysUnit = '天后';
      daysColor = '#5BA85B';
      metaText = anniv.recurring ? '每年这天' : '一次纪念';
    } else {
      daysNum = String(-diff);
      daysUnit = '天前';
      daysColor = '#8B7A8E';
      metaText = anniv.recurring ? '每年这天' : '一次纪念';
    }

    return { ...anniv, daysNum, daysUnit, daysColor, metaText };
  },

  refreshSelected() {
    const { selectedDate } = this.data;
    if (!selectedDate) return;
    const [y, m, d] = selectedDate.split('-').map(Number);
    const date = new Date(y, m - 1, d);
    const today = new Date();
    const isToday = dateStr(date) === dateStr(today);
    const diff = daysBetween(today, date);
    let relative = '';
    if (diff === 0) relative = '今天';
    else if (diff === 1) relative = '明天';
    else if (diff === -1) relative = '昨天';
    else if (diff > 0) relative = diff + ' 天后';
    else relative = (-diff) + ' 天前';

    const annivs = this.findAnniversariesForDate(selectedDate);
    const savings = this.data._savings
      .filter(s => s.date === selectedDate)
      .sort((a, b) => (b.id || 0) - (a.id || 0));
    const total = savings.reduce((sum, s) => sum + Number(s.amount || 0), 0);
    const notes = this.data._notes.filter(n => n.date === selectedDate);

    this.setData({
      selectedDay: d,
      selectedWeekday: WEEKDAY_LABELS_FULL[date.getDay()],
      selectedDateLabel: `${y}年${m}月${d}日`,
      selectedRelative: relative,
      selectedIsToday: isToday,
      selectedAnnivs: annivs,
      selectedSavings: savings,
      selectedNotes: notes,
      selectedTotal: total.toLocaleString('zh-CN'),
    });
  },

  refreshMonthStats() {
    const { currentYear: y, currentMonth: m } = this.data;
    const monthPrefix = `${y}-${pad(m)}`;
    const monthSavings = this.data._savings.filter(s => s.date.startsWith(monthPrefix));
    const total = monthSavings.reduce((sum, s) => sum + Number(s.amount || 0), 0);

    // 该月纪念日数（去重按月日）
    const annivSet = new Set();
    this.data._anniversaries.forEach(a => {
      const [, am, ad] = a.date.split('-').map(Number);
      if (a.recurring) annivSet.add(`${pad(am)}-${pad(ad)}`);
      else if (a.date.startsWith(monthPrefix)) annivSet.add(a.date);
    });

    // 不同存钱日
    const daySet = new Set(monthSavings.map(s => s.date));

    this.setData({
      monthTotal: total.toLocaleString('zh-CN'),
      monthSavingsCount: daySet.size,
      monthAnnivCount: annivSet.size,
    });
  },

  // ============== 月份切换 ==============
  onPrevMonth() {
    let { currentYear: y, currentMonth: m } = this.data;
    m--;
    if (m < 1) { m = 12; y--; }
    this.setCurrentMonth(y, m);
  },

  onNextMonth() {
    let { currentYear: y, currentMonth: m } = this.data;
    m++;
    if (m > 12) { m = 1; y++; }
    this.setCurrentMonth(y, m);
  },

  onPickMonth() {
    // 简单处理：直接跳回今天
    const today = new Date();
    this.setCurrentMonth(today.getFullYear(), today.getMonth() + 1);
  },

  onGoToday() {
    const today = new Date();
    this.setCurrentMonth(today.getFullYear(), today.getMonth() + 1);
    this.setData({ selectedDate: dateStr(today) });
    this.refreshSelected();
  },

  // ============== 选择日期 ==============
  onSelectDate(e) {
    const { date } = e.currentTarget.dataset;
    // 跨月点击时切换月份
    const [y, m] = date.split('-').map(Number);
    if (y !== this.data.currentYear || m !== this.data.currentMonth) {
      this.setCurrentMonth(y, m);
    }
    this.setData({ selectedDate: date });
    this.refreshSelected();
  },

  onTapAnniv(e) {
    const { id } = e.currentTarget.dataset;
    const anniv = this.data.selectedAnnivs.find(a => a.id === id);
    if (!anniv) return;
    wx.showModal({
      title: anniv.name,
      content: `${anniv.date}\n${anniv.recurring ? '每年纪念' : '一次性纪念'}\n${anniv.metaText}`,
      confirmText: '知道了',
      showCancel: false,
    });
  },

  // ============== 记一笔 ==============
  onOpenAdd() {
    this.setData({
      showAdd: true,
      addDateLabel: this.data.selectedDateLabel,
      addDraft: { amount: '', planId: '', note: '' },
    });
  },

  onCloseAdd() {
    this.setData({ showAdd: false });
  },

  onStopProp() {},

  onAmountInput(e) {
    const v = e.detail.value;
    // 只能数字 + 小数点
    const clean = v.replace(/[^\d.]/g, '');
    this.setData({ 'addDraft.amount': clean });
  },

  onPickQuickAmount(e) {
    const { amount } = e.currentTarget.dataset;
    this.setData({ 'addDraft.amount': String(amount) });
  },

  onPickPlan(e) {
    const { id } = e.currentTarget.dataset;
    this.setData({ 'addDraft.planId': id });
  },

  onNoteInput(e) {
    this.setData({ 'addDraft.note': e.detail.value });
  },

  onSaveRecord() {
    const { amount, planId, note } = this.data.addDraft;
    const amt = Number(amount);
    if (!amt || amt <= 0) {
      wx.showToast({ title: '请输入金额', icon: 'none' });
      return;
    }
    if (!planId) {
      wx.showToast({ title: '请选择关联计划', icon: 'none' });
      return;
    }
    api.deliverPlan(planId, amt, note || '')
      .then(() => {
        wx.showToast({ title: '✨ 记录成功', icon: 'success' });
        this.setData({ showAdd: false });
        this.loadData();
      })
      .catch(() => wx.showToast({ title: '记录失败', icon: 'none' }));
  },

  // ============== 纪念日 ==============
  onAddAnniv() {
    this.setData({
      showAddAnniv: true,
      addAnnivTitle: '',
    });
  },

  onCloseAddAnniv() {
    this.setData({ showAddAnniv: false, addAnnivTitle: '' });
  },

  onAddAnnivTitleInput(e) {
    this.setData({ addAnnivTitle: e.detail.value });
  },

  async onSaveAddAnniv() {
    const title = this.data.addAnnivTitle.trim();
    if (!title) {
      wx.showToast({ title: '请输入纪念日名称', icon: 'none' });
      return;
    }
    try {
      await api.createAnniversary({
        title,
        date_val: this.data.selectedDate,
      });
      wx.showToast({ title: '🎉 添加成功', icon: 'success' });
      this.setData({ showAddAnniv: false, addAnnivTitle: '' });
      this.loadData();
    } catch (e) {
      wx.showToast({ title: '添加失败', icon: 'none' });
    }
  },

  onGoAnnivMgmt() {
    this.setData({ showAddAnniv: false });
    wx.navigateTo({ url: '/pages/anniversaries/anniversaries' });
  },

  goCreatePlan() {
    this.setData({ showAdd: false });
    wx.navigateTo({ url: '/pages/plans/plans' });
  },
});
