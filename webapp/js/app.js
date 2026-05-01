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

  function openMenu() { menuOverlay.hidden = false; }
  function closeMenu() { menuOverlay.hidden = true; }

  document.getElementById('btn-menu').addEventListener('click', openMenu);
  document.getElementById('btn-menu-close').addEventListener('click', closeMenu);
  menuOverlay.addEventListener('click', (e) => { if (e.target === menuOverlay) closeMenu(); });

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
});
