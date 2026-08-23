/** storage.js — localStorage 课表数据管理 */

(function () {
  'use strict';

  const STORAGE_KEY = 'njust_schedule_data';
  const START_DATE_KEY = 'njust_semester_start';

  // 默认开学日期（第一周周一）——每学期开学时改这里
  const DEFAULT_START_DATE = '2026-03-02';

  // 获取开学日期
  function getStartDate() {
    return localStorage.getItem(START_DATE_KEY) || DEFAULT_START_DATE;
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

  // 清除考试数据（用于刷新）
  function clearExams() {
    localStorage.removeItem('njust_exams_data');
  }
  // 清除课表数据（用于刷新）
  function clearCourses() {
    localStorage.removeItem(STORAGE_KEY);
  }
  window.Storage = { DEFAULT_START_DATE, getStartDate, setStartDate, exportToFile, importFromFile, clearCourses, clearExams };
})();
