/** schedule.js — 课表渲染引擎 */

(function () {
  'use strict';

  // ===== 常量 =====
  const JIE_COUNT = 14;
  const WEEKDAYS = ['一', '二', '三', '四', '五', '六', '日'];
  const SEMESTER_START = new Date('2026-03-02'); // 开学第一周周一

  // 小节时间（用于显示）
  const JIE_TIME = {
    1: '08:00', 2: '08:50', 3: '09:40',
    4: '10:40', 5: '11:30',
    6: '14:00', 7: '14:50',
    8: '15:50', 9: '16:40', 10: '17:30',
    11: '19:00', 12: '19:50', 13: '20:40',
    14: '22:15'
  };

  // 计算小节结束时间（每小节45分钟）
  function getJieEndTime(jie) {
    const start = JIE_TIME[jie];
    if (!start) return '';
    const [h, m] = start.split(':').map(Number);
    let endM = m + 45;
    let endH = h;
    if (endM >= 60) {
      endH += 1;
      endM -= 60;
    }
    return `${String(endH).padStart(2, '0')}:${String(endM).padStart(2, '0')}`;
  }

  function formatCourseTime(course) {
    const start = JIE_TIME[course.startJie] || '';
    const end = getJieEndTime(course.endJie);
    return `${start}-${end}`;
  }

  // 全局状态
  let currentWeek = 1;
  let viewMode = 'week'; // 'week' | 'day'
  let currentDay = new Date().getDay(); // 0=周日,1=周一...
  if (currentDay === 0) currentDay = 7;
  let courses = [];

  // ===== 周次计算 =====
  function getCurrentWeek() {
    const now = new Date();
    const diff = Math.floor((now - SEMESTER_START) / (1000 * 60 * 60 * 24));
    return Math.max(1, Math.floor(diff / 7) + 1);
  }

  function getWeekDates(week) {
    const base = new Date(SEMESTER_START);
    base.setDate(base.getDate() + (week - 1) * 7);
    const dates = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(base);
      d.setDate(d.getDate() + i);
      dates.push(d);
    }
    return dates;
  }

  function formatDate(date) {
    return `${date.getMonth() + 1}/${date.getDate()}`;
  }

  // ===== 周次解析 =====
  function parseWeeks(weekStr) {
    const weeks = [];
    if (!weekStr) return weeks;
    const parts = weekStr.split(',');
    for (const part of parts) {
      if (part.includes('-')) {
        const [a, b] = part.split('-').map(Number);
        for (let w = a; w <= b; w++) weeks.push(w);
      } else {
        const w = Number(part);
        if (!isNaN(w)) weeks.push(w);
      }
    }
    return weeks;
  }

  function isCourseActive(course, week) {
    const weeks = parseWeeks(course.weeks);
    return weeks.length === 0 || weeks.includes(week);
  }

  // ===== 渲染日期栏 =====
  function renderDateBar() {
    const bar = document.getElementById('date-bar');
    bar.innerHTML = '<div class="corner"></div>';
    const dates = getWeekDates(currentWeek);
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    for (let i = 0; i < 7; i++) {
      const d = dates[i];
      const isToday = d.getTime() === today.getTime();
      const isActive = viewMode === 'day' && (i + 1) === currentDay;
      const cls = ['date-cell', isToday && 'today', isActive && 'active'].filter(Boolean).join(' ');
      bar.innerHTML += `
        <div class="${cls}" data-day="${i + 1}">
          <span class="weekday">${WEEKDAYS[i]}</span>
          <span class="date-num">${formatDate(d)}</span>
        </div>
      `;
    }
  }

  // ===== 渲染周视图 =====
  function renderWeekView() {
    const grid = document.getElementById('schedule-grid');
    grid.style.display = 'grid';
    grid.innerHTML = '';
    grid.className = 'schedule-grid';

    // 小节标签列
    for (let j = 1; j <= JIE_COUNT; j++) {
      const label = document.createElement('div');
      label.className = 'jie-label';
      label.textContent = j;
      grid.appendChild(label);
    }

    // 放置课程卡片（直接作为 grid item，自然跨行）
    for (const course of courses) {
      if (!isCourseActive(course, currentWeek)) continue;
      if (course.day < 1 || course.day > 7) continue;

      const card = document.createElement('div');
      card.className = `course-card c${course.color % 10}`;
      // 使用 CSS Grid 的 grid-area 跨越多个小节
      card.style.gridColumn = `${course.day + 1}`;
      card.style.gridRow = `${course.startJie} / ${course.endJie + 1}`;
      card.innerHTML = `
        <div class="course-name">${course.name}</div>
        <div class="course-location">${course.location || ''}</div>
        <div class="course-teacher">${course.teacher || ''}</div>
      `;
      card.addEventListener('click', () => showModal(course));
      grid.appendChild(card);
    }

    // 最后铺一层空 cell 提供网格线（DOM 在后面，pointer-events:none 不阻挡点击）
    for (let day = 1; day <= 7; day++) {
      for (let j = 1; j <= JIE_COUNT; j++) {
        const cell = document.createElement('div');
        cell.className = 'grid-cell';
        cell.style.gridColumn = day + 1;
        cell.style.gridRow = j;
        grid.appendChild(cell);
      }
    }
  }

  // ===== 渲染日视图 =====
  function renderDayView() {
    const grid = document.getElementById('schedule-grid');
    grid.style.display = 'flex';
    grid.innerHTML = '';
    grid.className = 'day-view active';

    const dayCourses = courses
      .filter(c => c.day === currentDay && isCourseActive(c, currentWeek))
      .sort((a, b) => a.startJie - b.startJie);

    if (dayCourses.length === 0) {
      grid.innerHTML = '<div class="empty-state">今日无课 🎉</div>';
      return;
    }

    for (const c of dayCourses) {
      const el = document.createElement('div');
      el.className = 'day-course-card';
      el.innerHTML = `
        <div class="day-time-tag">${formatCourseTime(c)}</div>
        <div class="day-info">
          <div class="day-course-name">${c.name}</div>
          <div class="day-course-meta">${c.location || ''} · ${c.teacher || ''}</div>
        </div>
      `;
      el.addEventListener('click', () => showModal(c));
      grid.appendChild(el);
    }
  }

  // ===== 渲染 =====
  function render() {
    renderDateBar();
    document.getElementById('week-label').textContent = `△ 第${currentWeek}周`;

    const weekdayNames = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];
    const today = new Date();
    document.getElementById('today-label').textContent = weekdayNames[today.getDay()];

    const viewBtn = document.getElementById('btn-view-toggle');
    viewBtn.textContent = viewMode === 'week' ? '日' : '周';

    if (viewMode === 'week') {
      renderWeekView();
    } else {
      renderDayView();
    }
  }

  // ===== 弹窗 =====
  function showModal(course) {
    document.getElementById('modal-title').textContent = course.name;
    document.getElementById('modal-time').innerHTML = `<strong>时间：</strong>星期${WEEKDAYS[course.day - 1]} ${formatCourseTime(course)}（第${course.startJie}-${course.endJie}小节）`;
    document.getElementById('modal-location').innerHTML = `<strong>地点：</strong>${course.location || '未指定'}`;
    document.getElementById('modal-teacher').innerHTML = `<strong>教师：</strong>${course.teacher || '未指定'}`;
    document.getElementById('modal-weeks').innerHTML = `<strong>周次：</strong>${course.weeks || '全学期'}`;
    document.getElementById('modal-overlay').hidden = false;
  }

  function hideModal() {
    document.getElementById('modal-overlay').hidden = true;
  }

  // ===== 导航 =====
  function prevWeek() { currentWeek--; render(); }
  function nextWeek() { currentWeek++; render(); }
  function toggleView() {
    viewMode = viewMode === 'week' ? 'day' : 'week';
    render();
  }
  function setDay(day) {
    currentDay = day;
    if (viewMode === 'week') {
      viewMode = 'day';
    }
    render();
  }

  // ===== 初始化 =====
  function init(data) {
    courses = data || [];
    currentWeek = getCurrentWeek();
    render();

    document.getElementById('btn-prev-week').addEventListener('click', prevWeek);
    document.getElementById('btn-next-week').addEventListener('click', nextWeek);
    document.getElementById('btn-view-toggle').addEventListener('click', toggleView);
    document.getElementById('btn-modal-close').addEventListener('click', hideModal);
    document.getElementById('modal-overlay').addEventListener('click', (e) => {
      if (e.target === document.getElementById('modal-overlay')) hideModal();
    });

    // 日期栏点击切换日视图
    document.getElementById('date-bar').addEventListener('click', (e) => {
      const cell = e.target.closest('.date-cell');
      if (cell) {
        const day = Number(cell.dataset.day);
        if (day) setDay(day);
      }
    });
  }

  // ===== 暴露 =====
  window.Schedule = { init, render, prevWeek, nextWeek, toggleView };
})();
