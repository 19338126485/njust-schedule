/** app.js — 主逻辑入口 */

document.addEventListener('DOMContentLoaded', async () => {
  'use strict';

  // 1. 加载课表数据（优先localStorage，其次schedule.json）
  let courses = Storage.loadCourses();

  if (!courses) {
    try {
      const res = await fetch('data/schedule.json');
      if (res.ok) {
        courses = await res.json();
        Storage.saveCourses(courses);
        console.log('Loaded from schedule.json');
      }
    } catch (e) {
      console.error('Failed to load schedule.json:', e);
    }
  }

  // 兜底空数据
  if (!courses) courses = [];

  // 1b. 加载考试数据（优先localStorage，其次exams.json）
  let exams = Storage.loadExams();
  if (!exams || !exams.length) {
    // localStorage 没有或为空，重新从服务器拉取
    try {
      const res = await fetch('data/exams.json?v=' + Date.now());
      if (res.ok) {
        exams = await res.json();
        Storage.saveExams(exams);
        console.log('Loaded from exams.json');
      }
    } catch (e) {
      console.error('Failed to load exams.json:', e);
    }
  }
  if (!exams) exams = [];

  // 2. 初始化课表渲染
  Schedule.init(courses);

  // 3. PWA: 注册 Service Worker
  if ('serviceWorker' in navigator) {
    try {
      await navigator.serviceWorker.register('sw.js');
      console.log('SW registered');
    } catch (e) {
      console.error('SW registration failed:', e);
    }
  }

  // 4. 首次使用：检查开学日期
  const FIRST_RUN_KEY = 'njust_first_run';
  if (!localStorage.getItem(FIRST_RUN_KEY)) {
    // 首次打开，提示设置开学日期
    setTimeout(() => {
      if (confirm('首次使用请确认开学日期\n\n当前设置：2026-03-02（南理工春季学期）\n\n每年开学日期可能不同，如不正确请点击"确定"在菜单中修改。')) {
        document.getElementById('date-input').value = Storage.getStartDate();
        document.getElementById('date-modal-overlay').hidden = false;
      }
      localStorage.setItem(FIRST_RUN_KEY, '1');
    }, 1500);
  }

  // 5. 菜单面板
  const menuOverlay = document.getElementById('menu-overlay');
  const menuPanel = document.getElementById('menu-panel');
  const dateModalOverlay = document.getElementById('date-modal-overlay');
  const aboutModalOverlay = document.getElementById('about-modal-overlay');
  const examsModalOverlay = document.getElementById('exams-modal-overlay');
  const examsContent = document.getElementById('exams-content');

  function openMenu() { menuOverlay.hidden = false; }
  function closeMenu() { menuOverlay.hidden = true; }

  document.getElementById('btn-menu').addEventListener('click', openMenu);
  document.getElementById('btn-menu-close').addEventListener('click', closeMenu);
  menuOverlay.addEventListener('click', (e) => { if (e.target === menuOverlay) closeMenu(); });

  // 考试安排
  function renderExams() {
    const examData = Storage.loadExams() || [];
    if (!examData.length) {
      examsContent.innerHTML = '<p class="empty-state">暂无考试数据<br><br>请在电脑端运行<br><code>python -m src.exams_main</code><br>更新考试安排</p>';
      return;
    }
    let html = '<table class="exam-table">';
    html += '<tr><th>课程</th><th>时间</th><th>考场</th><th>座位</th></tr>';
    for (const e of examData) {
      const time = e.date ? `${e.date} ${e.start_time || ''}~${e.end_time || ''}` : (e.exam_time || '');
      html += `<tr><td>${e.course_name || ''}</td><td>${time}</td><td>${e.room || ''}</td><td>${e.seat || ''}</td></tr>`;
    }
    html += '</table>';
    examsContent.innerHTML = html;
  }

  document.getElementById('btn-exams').addEventListener('click', () => {
    renderExams();
    examsModalOverlay.hidden = false;
    closeMenu();
  });
  document.getElementById('btn-exams-close').addEventListener('click', () => {
    examsModalOverlay.hidden = true;
  });
  examsModalOverlay.addEventListener('click', (e) => {
    if (e.target === examsModalOverlay) examsModalOverlay.hidden = true;
  });

  // 导入课表
  document.getElementById('btn-import').addEventListener('click', () => {
    document.getElementById('file-import').click();
  });
  document.getElementById('file-import').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      const data = await Storage.importFromFile(file);
      Storage.saveCourses(data);
      Schedule.init(data);
      alert('课表导入成功！');
      closeMenu();
    } catch (err) {
      alert('导入失败: ' + err.message);
    }
    e.target.value = '';
  });

  // 导出课表
  document.getElementById('btn-export').addEventListener('click', () => {
    const data = Storage.loadCourses() || [];
    Storage.exportToFile(data, 'njust_schedule.json');
    closeMenu();
  });

  // 设置开学日期
  document.getElementById('btn-set-date').addEventListener('click', () => {
    document.getElementById('date-input').value = Storage.getStartDate();
    dateModalOverlay.hidden = false;
    closeMenu();
  });
  document.getElementById('btn-date-save').addEventListener('click', () => {
    const date = document.getElementById('date-input').value;
    if (date) {
      Storage.setStartDate(date);
      alert('开学日期已保存: ' + date);
      dateModalOverlay.hidden = true;
    }
  });
  document.getElementById('btn-date-cancel').addEventListener('click', () => {
    dateModalOverlay.hidden = true;
  });
  dateModalOverlay.addEventListener('click', (e) => {
    if (e.target === dateModalOverlay) dateModalOverlay.hidden = true;
  });

  // 关于
  document.getElementById('btn-about').addEventListener('click', () => {
    aboutModalOverlay.hidden = false;
    closeMenu();
  });
  document.getElementById('btn-about-close').addEventListener('click', () => {
    aboutModalOverlay.hidden = true;
  });
  aboutModalOverlay.addEventListener('click', (e) => {
    if (e.target === aboutModalOverlay) aboutModalOverlay.hidden = true;
  });

  // 刷新数据（清除localStorage缓存，重新fetch）
  const btnRefresh = document.getElementById('btn-refresh');
  if (btnRefresh) {
    btnRefresh.addEventListener('click', async () => {
      closeMenu();
      if (!confirm('清除本地缓存并重新拉取最新数据？')) return;
      Storage.clearExams();
      try {
        const res = await fetch('data/exams.json?v=' + Date.now());
        if (res.ok) {
          const exams = await res.json();
          Storage.saveExams(exams);
          alert('考试数据已更新！\n共 ' + exams.length + ' 场考试');
        }
      } catch (e) {
        alert('拉取失败: ' + e.message);
      }
    });
  }
});
