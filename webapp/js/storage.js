/** storage.js — localStorage 课表数据管理 */

(function () {
  'use strict';

  const STORAGE_KEY = 'njust_schedule_data';
  const START_DATE_KEY = 'njust_semester_start';

  // 加载课表数据
  function loadCourses() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) return JSON.parse(raw);
    } catch (e) {
      console.error('Storage load error:', e);
    }
    return null;
  }

  // 保存课表数据
  function saveCourses(courses) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(courses));
      return true;
    } catch (e) {
      console.error('Storage save error:', e);
      return false;
    }
  }

  // 获取开学日期
  function getStartDate() {
    return localStorage.getItem(START_DATE_KEY) || '2026-02-17';
  }

  // 设置开学日期
  function setStartDate(date) {
    localStorage.setItem(START_DATE_KEY, date);
  }

  // 导出为 JSON 文件
  function exportToFile(courses, filename = 'njust_schedule.json') {
    const blob = new Blob([JSON.stringify(courses, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  // 从文件导入
  function importFromFile(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const data = JSON.parse(e.target.result);
          if (Array.isArray(data)) {
            saveCourses(data);
            resolve(data);
          } else {
            reject(new Error('文件格式错误'));
          }
        } catch (err) {
          reject(err);
        }
      };
      reader.onerror = () => reject(new Error('文件读取失败'));
      reader.readAsText(file);
    });
  }

  // 加载考试数据
  function loadExams() {
    try {
      const raw = localStorage.getItem('njust_exams_data');
      if (raw) return JSON.parse(raw);
    } catch (e) {
      console.error('Exams load error:', e);
    }
    return null;
  }

  // 保存考试数据
  function saveExams(exams) {
    try {
      localStorage.setItem('njust_exams_data', JSON.stringify(exams));
      return true;
    } catch (e) {
      console.error('Exams save error:', e);
      return false;
    }
  }
  // 清除考试数据（用于刷新）
  function clearExams() {
    localStorage.removeItem('njust_exams_data');
  }
  // 清除课表数据（用于刷新）
  function clearCourses() {
    localStorage.removeItem(STORAGE_KEY);
  }
  window.Storage = { loadCourses, saveCourses, getStartDate, setStartDate, exportToFile, importFromFile, loadExams, saveExams, clearCourses, clearExams };
})();
