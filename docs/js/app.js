/** app.js — 主逻辑入口 */

document.addEventListener('DOMContentLoaded', async () => {
  'use strict';

  // ===== 数据解密（WebCrypto: PBKDF2-SHA256 → AES-256-GCM，与 src/crypto_helper.py 互通）=====
  const PW_KEY = 'njust_pw';
  const SCHEDULE_KEY = 'njust_schedule_data';
  const EXAMS_KEY = 'njust_exams_data';

  function b64ToBuf(b64) {
    const bin = atob(b64);
    const buf = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
    return buf;
  }
  function bufToB64(buf) {
    let bin = '';
    const bytes = new Uint8Array(buf);
    for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
    return btoa(bin);
  }
  // envelope 格式判断：{"v":1,...,"salt","iv","data"}，旧明文课表是数组，会被排除
  function isEnvelope(obj) {
    return obj && typeof obj === 'object' && !Array.isArray(obj) && obj.v && obj.salt && obj.iv && obj.data;
  }
  async function deriveKey(password, salt, iterations) {
    const baseKey = await crypto.subtle.importKey('raw', new TextEncoder().encode(password), 'PBKDF2', false, ['deriveKey']);
    return crypto.subtle.deriveKey(
      { name: 'PBKDF2', hash: 'SHA-256', salt, iterations },
      baseKey,
      { name: 'AES-GCM', length: 256 },
      false,
      ['decrypt', 'encrypt']
    );
  }
  async function decryptEnvelope(envelope, password) {
    const key = await deriveKey(password, b64ToBuf(envelope.salt), envelope.iter);
    const plain = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: b64ToBuf(envelope.iv) }, key, b64ToBuf(envelope.data));
    return JSON.parse(new TextDecoder().decode(plain));
  }
  async function encryptEnvelope(obj, password) {
    const salt = crypto.getRandomValues(new Uint8Array(16));
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const key = await deriveKey(password, salt, 200000);
    const data = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, new TextEncoder().encode(JSON.stringify(obj)));
    return { v: 1, alg: 'AES-GCM', kdf: 'PBKDF2-SHA256', iter: 200000, salt: bufToB64(salt), iv: bufToB64(iv), data: bufToB64(data) };
  }

  // ===== 密码输入（存 sessionStorage，关标签页即失效）=====
  const pwOverlay = document.getElementById('pw-overlay');
  const pwInput = document.getElementById('pw-input');
  const pwError = document.getElementById('pw-error');
  let pwResolver = null;

  function askPassword(showError) {
    pwOverlay.hidden = false;
    pwError.hidden = !showError;
    pwInput.value = '';
    setTimeout(() => pwInput.focus(), 50);
    return new Promise((resolve) => { pwResolver = resolve; });
  }
  function submitPw() {
    const pw = pwInput.value;
    if (!pw || !pwResolver) return;
    sessionStorage.setItem(PW_KEY, pw);
    pwOverlay.hidden = true;
    const r = pwResolver;
    pwResolver = null;
    r(pw);
  }
  document.getElementById('btn-pw-ok').addEventListener('click', submitPw);
  pwInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') submitPw(); });

  async function getPassword() {
    const saved = sessionStorage.getItem(PW_KEY);
    if (saved) return saved;
    return askPassword(false);
  }

  // ===== 加密数据加载：localStorage 只缓存密文 envelope，明文只留内存 =====
  async function loadEncryptedData(kind) {
    const lsKey = kind === 'schedule' ? SCHEDULE_KEY : EXAMS_KEY;
    const path = 'data/' + kind + '.enc.json';

    // 1. 读 localStorage 缓存；旧明文缓存（非 envelope）直接丢弃
    let envelope = null;
    try {
      const raw = localStorage.getItem(lsKey);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (isEnvelope(parsed)) {
          envelope = parsed;
          console.log('Using cached encrypted ' + kind);
        } else {
          console.warn(lsKey + ' 是旧明文格式，丢弃并重新拉取');
          localStorage.removeItem(lsKey);
        }
      }
    } catch (e) {
      localStorage.removeItem(lsKey);
    }

    // 2. 缓存没有则从服务器拉取密文
    if (!envelope) {
      try {
        const res = await fetch(path + '?v=' + Date.now());
        if (res.ok) envelope = await res.json();
      } catch (e) {
        console.error('Failed to load ' + path + ':', e);
      }
    }
    if (!isEnvelope(envelope)) return [];

    // 3. 解密；密码错误（AES-GCM 校验失败）则清除已存密码并重试
    let firstTry = true;
    while (true) {
      const pw = firstTry ? await getPassword() : await askPassword(true);
      firstTry = false;
      try {
        const plain = await decryptEnvelope(envelope, pw);
        localStorage.setItem(lsKey, JSON.stringify(envelope));
        return plain;
      } catch (e) {
        console.warn('解密失败，可能密码错误，请重试');
        sessionStorage.removeItem(PW_KEY);
      }
    }
  }

  // 1. 加载课表数据（解密后明文只在内存）
  let courses = await loadEncryptedData('schedule');

  // 1b. 加载考试数据
  let exams = await loadEncryptedData('exams');

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

  // 判断考试是否已考完
  function isExamFinished(exam) {
    const now = new Date();
    if (exam.date) {
      const endTime = exam.end_time || '23:59';
      const examEnd = new Date(`${exam.date}T${endTime}`);
      return now > examEnd;
    }
    if (exam.exam_time) {
      const match = exam.exam_time.match(/(\d{4}-\d{2}-\d{2})/);
      if (match) {
        const date = match[1];
        const timeMatch = exam.exam_time.match(/~(\d{2}:\d{2})/);
        const endTime = timeMatch ? timeMatch[1] : '23:59';
        const examEnd = new Date(`${date}T${endTime}`);
        return now > examEnd;
      }
    }
    return false;
  }

  // 考试安排
  function renderExams() {
    const examData = exams || [];
    if (!examData.length) {
      examsContent.innerHTML = '<p class="empty-state">暂无考试数据<br><br>请在电脑端运行<br><code>python -m src.exams_main</code><br>更新考试安排</p>';
      return;
    }
    let html = '<table class="exam-table">';
    html += '<tr><th>课程</th><th>时间</th><th>考场</th><th>座位</th></tr>';
    for (const e of examData) {
      const time = e.date ? `${e.date} ${e.start_time || ''}~${e.end_time || ''}` : (e.exam_time || '');
      const finished = isExamFinished(e);
      const rowClass = finished ? 'exam-finished' : '';
      html += `<tr class="${rowClass}"><td>${e.course_name || ''}</td><td>${time}</td><td>${e.room || ''}</td><td>${e.seat || ''}</td></tr>`;
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
      courses = data;
      Schedule.init(data);
      // 用当前密码加密后缓存密文（明文不落 localStorage）
      try {
        const pw = await getPassword();
        const env = await encryptEnvelope(data, pw);
        localStorage.setItem(SCHEDULE_KEY, JSON.stringify(env));
      } catch (cacheErr) {
        console.error('缓存导入课表失败:', cacheErr);
      }
      alert('课表导入成功！');
      closeMenu();
    } catch (err) {
      alert('导入失败: ' + err.message);
    }
    e.target.value = '';
  });

  // 导出课表
  document.getElementById('btn-export').addEventListener('click', () => {
    Storage.exportToFile(courses || [], 'njust_schedule.json');
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

  // 刷新数据（清除localStorage密文缓存，重新fetch课表+考试并解密）
  const btnRefresh = document.getElementById('btn-refresh');
  if (btnRefresh) {
    btnRefresh.addEventListener('click', async () => {
      closeMenu();
      if (!confirm('清除本地缓存并重新拉取最新课表和考试数据？')) return;

      // 清除缓存
      Storage.clearCourses();
      Storage.clearExams();

      let msg = '';

      // 重新拉取课表
      try {
        const res = await fetch('data/schedule.enc.json?v=' + Date.now());
        if (res.ok) {
          const env = await res.json();
          const pw = await getPassword();
          courses = await decryptEnvelope(env, pw);
          localStorage.setItem(SCHEDULE_KEY, JSON.stringify(env));
          Schedule.init(courses);
          msg += '课表已更新！共 ' + courses.length + ' 个时间段\n';
        } else {
          msg += '课表拉取失败\n';
        }
      } catch (e) {
        msg += '课表拉取失败: ' + e.message + '\n';
      }

      // 重新拉取考试
      try {
        const res = await fetch('data/exams.enc.json?v=' + Date.now());
        if (res.ok) {
          const env = await res.json();
          const pw = await getPassword();
          exams = await decryptEnvelope(env, pw);
          localStorage.setItem(EXAMS_KEY, JSON.stringify(env));
          msg += '考试已更新！共 ' + exams.length + ' 场考试';
        } else {
          msg += '考试拉取失败';
        }
      } catch (e) {
        msg += '考试拉取失败: ' + e.message;
      }

      alert(msg);
    });
  }
});
