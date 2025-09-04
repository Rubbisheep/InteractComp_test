import React, { useState, useRef, useEffect } from 'react';
import { Upload, Play, Download, FileText, BarChart3, CheckCircle, XCircle, Clock, AlertCircle, Key, Zap, Target, TrendingUp, Brain, Cpu, User, Users, LogIn, LogOut, UserPlus, Activity, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';

// 分页组件
const Pagination = ({ currentPage, pageSize, totalItems, onPageChange }) => {
  const totalPages = Math.ceil(totalItems / pageSize);
  
  if (totalPages <= 1) return null;

  const getVisiblePages = () => {
    const delta = 2;
    const range = [];
    const rangeWithDots = [];

    for (let i = Math.max(2, currentPage - delta);
         i <= Math.min(totalPages - 1, currentPage + delta);
         i++) {
      range.push(i);
    }

    if (currentPage - delta > 2) {
      rangeWithDots.push(1, '...');
    } else {
      rangeWithDots.push(1);
    }

    rangeWithDots.push(...range);

    if (currentPage + delta < totalPages - 1) {
      rangeWithDots.push('...', totalPages);
    } else {
      if (totalPages > 1) rangeWithDots.push(totalPages);
    }

    return rangeWithDots;
  };

  return (
    <div className="flex items-center justify-between mt-4 px-4 py-3 bg-slate-800/50 border border-slate-600 rounded-lg">
      <div className="flex items-center text-sm text-slate-300">
        显示第 {Math.min((currentPage - 1) * pageSize + 1, totalItems)} - {Math.min(currentPage * pageSize, totalItems)} 条，
        共 {totalItems} 条
      </div>
      
      <div className="flex items-center space-x-1">
        <button
          onClick={() => onPageChange(1)}
          disabled={currentPage === 1}
          className="p-2 text-slate-400 hover:text-slate-200 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-700/50 rounded"
        >
          <ChevronsLeft className="w-4 h-4" />
        </button>
        
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="p-2 text-slate-400 hover:text-slate-200 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-700/50 rounded"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        {getVisiblePages().map((page, index) => (
          <button
            key={index}
            onClick={() => typeof page === 'number' ? onPageChange(page) : null}
            disabled={page === '...'}
            className={`px-3 py-1 text-sm rounded ${
              page === currentPage
                ? 'bg-blue-500 text-white'
                : page === '...'
                ? 'text-slate-500 cursor-default'
                : 'text-slate-300 hover:bg-slate-700/50 hover:text-white'
            }`}
          >
            {page}
          </button>
        ))}

        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="p-2 text-slate-400 hover:text-slate-200 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-700/50 rounded"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
        
        <button
          onClick={() => onPageChange(totalPages)}
          disabled={currentPage === totalPages}
          className="p-2 text-slate-400 hover:text-slate-200 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-700/50 rounded"
        >
          <ChevronsRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

const InteractCompMultiUserPlatform = () => {
  // 用户认证状态
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [authMode, setAuthMode] = useState('login'); // 'login' | 'register'
  const [token, setToken] = useState(localStorage.getItem('auth_token'));

  // 原有状态
  const [activeTab, setActiveTab] = useState('upload');
  const [files, setFiles] = useState([]);
  const [configStatus, setConfigStatus] = useState(null);
  const [testResults, setTestResults] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const fileInputRef = useRef(null);

  // 新增多用户功能状态
  const [allTasks, setAllTasks] = useState([]);
  const [userTasks, setUserTasks] = useState([]);
  const [allUsers, setAllUsers] = useState([]);
  const [systemStatus, setSystemStatus] = useState({
    running_tasks: 0,
    max_concurrent_tasks: 10,  // 默认值，会从API更新
    available_slots: 10
  });

  // 分页状态
  const [userTasksPagination, setUserTasksPagination] = useState({
    currentPage: 1,
    pageSize: 5,
    totalItems: 0
  });
  const [communityTasksPagination, setCommunityTasksPagination] = useState({
    currentPage: 1,
    pageSize: 5,
    totalItems: 0
  });

  // 认证表单状态
  const [authForm, setAuthForm] = useState({
    username: '',
    password: '',
    displayName: ''
  });

  // 检查认证状态
  useEffect(() => {
    if (token) {
      checkAuthStatus();
    }
  }, [token]);

  const checkAuthStatus = async () => {
    if (!token) return;

    try {
      const response = await fetch('/auth/me', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const user = await response.json();
        setCurrentUser(user);
        setIsAuthenticated(true);
        checkConfigStatus();
        loadUserData();
      } else {
        // Token无效，清除本地存储
        localStorage.removeItem('auth_token');
        setToken(null);
        setIsAuthenticated(false);
        setCurrentUser(null);
      }
    } catch (error) {
      console.error('认证检查失败:', error);
      localStorage.removeItem('auth_token');
      setToken(null);
      setIsAuthenticated(false);
      setCurrentUser(null);
    }
  };

  const handleAuth = async (e) => {
    e.preventDefault();
    
    try {
      const endpoint = authMode === 'login' ? '/auth/login' : '/auth/register';
      const payload = authMode === 'login' 
        ? { username: authForm.username, password: authForm.password }
        : { username: authForm.username, password: authForm.password, display_name: authForm.displayName };

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (response.ok) {
        if (authMode === 'login') {
          setToken(data.token);
          localStorage.setItem('auth_token', data.token);
          setCurrentUser(data.user);
          setIsAuthenticated(true);
          setAuthForm({ username: '', password: '', displayName: '' });
          checkConfigStatus();
          loadUserData();
        } else {
          alert('注册成功，请登录');
          setAuthMode('login');
          setAuthForm({ username: '', password: '', displayName: '' });
        }
      } else {
        alert(data.detail || '操作失败');
      }
    } catch (error) {
      alert('操作失败: ' + error.message);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('auth_token');
    setToken(null);
    setIsAuthenticated(false);
    setCurrentUser(null);
    setFiles([]);
    setTestResults(null);
    setAllTasks([]);
    setUserTasks([]);
    setActiveTab('upload');
  };

  const loadUserData = async () => {
    if (!token) return;

    try {
      // 加载任务列表
      const tasksResponse = await fetch('/tasks', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (tasksResponse.ok) {
        const tasksData = await tasksResponse.json();
        setUserTasks(tasksData.user_tasks || []);
        setAllTasks(tasksData.all_tasks || []);
      }

      // 加载用户列表
      const usersResponse = await fetch('/users', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (usersResponse.ok) {
        const usersData = await usersResponse.json();
        setAllUsers(usersData.users || []);
      }

      // 加载用户文件
      const filesResponse = await fetch('/files', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (filesResponse.ok) {
        const filesData = await filesResponse.json();
        setFiles(filesData.files?.map(f => ({
          id: f.file_id,
          name: f.filename,
          size: f.size,
          status: 'ready'
        })) || []);
      }

      // 加载系统状态
      const systemResponse = await fetch('/system/status');
      if (systemResponse.ok) {
        const systemData = await systemResponse.json();
        setSystemStatus(systemData);
      }
    } catch (error) {
      console.error('加载用户数据失败:', error);
    }
  };

  // 检查配置状态
  const checkConfigStatus = async () => {
    try {
      const response = await fetch('/config/status');
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const status = await response.json();
      setConfigStatus(status);
    } catch (error) {
      console.error('检查配置状态失败:', error);
      setConfigStatus({ 
        config_found: false, 
        ready: false, 
        error: `无法连接到后端服务: ${error.message}` 
      });
    }
  };

  // 分页工具函数
  const getPaginatedData = (data, currentPage, pageSize) => {
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    return data.slice(startIndex, endIndex);
  };

  const updateUserTasksPagination = () => {
    setUserTasksPagination(prev => ({
      ...prev,
      totalItems: userTasks.length
    }));
  };

  const updateCommunityTasksPagination = () => {
    setCommunityTasksPagination(prev => ({
      ...prev,
      totalItems: allTasks.length
    }));
  };

  const handleUserTasksPageChange = (page) => {
    setUserTasksPagination(prev => ({
      ...prev,
      currentPage: page
    }));
  };

  const handleCommunityTasksPageChange = (page) => {
    setCommunityTasksPagination(prev => ({
      ...prev,
      currentPage: page
    }));
  };

  // 监听任务数据变化，更新分页
  useEffect(() => {
    updateUserTasksPagination();
  }, [userTasks]);

  useEffect(() => {
    updateCommunityTasksPagination();
  }, [allTasks]);

  const handleFileUpload = async (event) => {
    if (!token) {
      alert('请先登录');
      return;
    }

    const uploadedFiles = Array.from(event.target.files);
    
    for (const file of uploadedFiles) {
      const formData = new FormData();
      formData.append('file', file);
      
      try {
        const response = await fetch('/upload', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          },
          body: formData
        });
        
        if (response.ok) {
          const result = await response.json();
          setFiles(prev => [...prev, {
            id: result.file_id,
            name: result.filename,
            size: result.size,
            status: 'ready'
          }]);
        } else {
          alert(`文件 ${file.name} 上传失败`);
        }
      } catch (error) {
        alert(`文件 ${file.name} 上传失败: ${error.message}`);
      }
    }
  };

  const removeFile = async (fileId) => {
    if (!token) {
      alert('请先登录');
      return;
    }

    // 获取文件名用于确认对话框
    const fileToDelete = files.find(f => f.id === fileId);
    const fileName = fileToDelete ? fileToDelete.name : fileId;

    if (!confirm(`确定要删除文件 "${fileName}" 吗？此操作无法撤销。`)) {
      return;
    }

    try {
      const response = await fetch(`/files/${fileId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        // 从前端状态中移除文件
        setFiles(prev => prev.filter(file => file.id !== fileId));
        console.log('文件删除成功:', fileName);
      } else {
        const error = await response.json();
        alert(`删除文件失败: ${error.detail || '未知错误'}`);
      }
    } catch (error) {
      console.error('删除文件失败:', error);
      alert('删除文件失败，请检查网络连接');
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const startTesting = async () => {
    if (!token) {
      alert('请先登录');
      return;
    }

    if (files.length === 0) {
      alert('请先上传数据文件');
      return;
    }
    
    if (!configStatus || !configStatus.ready) {
      alert('配置文件未就绪，请检查config2.yaml文件中的API Keys配置');
      return;
    }

    setIsRunning(true);
    setProgress(0);
    setActiveTab('results');

    try {
      const fileIds = files.map(f => f.id);
      const startResponse = await fetch('/start_test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ file_ids: fileIds }),
      });

      if (!startResponse.ok) {
        const errorData = await startResponse.json();
        throw new Error(errorData.detail || `HTTP ${startResponse.status}`);
      }

      const responseData = await startResponse.json();
      const task_id = responseData.task_id;

      if (!task_id) {
        throw new Error('服务器未返回任务ID');
      }

      console.log('任务启动成功，ID:', task_id);

      const pollStatus = async () => {
        if (!task_id) {
          console.error('任务ID为空，停止轮询');
          setIsRunning(false);
          return;
        }

        try {
          const statusResponse = await fetch(`/test/${task_id}`, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });

          if (!statusResponse.ok) {
            console.error(`获取任务状态失败: HTTP ${statusResponse.status}`);
            setTimeout(pollStatus, 2000);
            return;
          }

          const status = await statusResponse.json();
          
          setProgress(status.progress || 0);

          // 同时更新系统状态
          try {
            const systemResponse = await fetch('/system/status');
            if (systemResponse.ok) {
              const systemData = await systemResponse.json();
              setSystemStatus(systemData);
            }
          } catch (e) {
            console.warn('更新系统状态失败:', e);
          }

          if (status.status === 'completed') {
            const results = {
              taskId: task_id,
              totalQuestions: status.total_questions,
              qualityPassedCount: status.quality_passed_count,
              qualityFailedCount: status.quality_failed_count,
              qualityFailedRate: status.quality_failed_rate,
              totalCost: status.total_cost,
              evaluationModels: ["GPT-5-mini", "GPT-5", "Claude-4-Sonnet"],
              failedItems: status.failed_items?.map((item, index) => ({
                id: index + 1,
                question: item.question,
                correctAnswer: item.correct_answer,
                modelResults: item.model_results,
                correctModelsCount: item.correct_models_count,
                qualityFailed: item.quality_failed
              })) || []
            };
            
            setTestResults(results);
            setIsRunning(false);
            loadUserData(); // 重新加载任务列表
          } else if (status.status === 'failed') {
            alert('测试失败: ' + (status.error || '未知错误'));
            setIsRunning(false);
          } else {
            setTimeout(pollStatus, 2000);
          }
        } catch (error) {
          console.error('轮询状态失败:', error);
          setTimeout(pollStatus, 2000);
        }
      };

      pollStatus();

    } catch (error) {
      alert('测试启动失败: ' + error.message);
      setIsRunning(false);
    }
  };

  const downloadReport = async (taskId) => {
    if (!token) {
      alert('请先登录');
      return;
    }

    try {
      const response = await fetch(`/test/${taskId}/download-csv`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (response.ok) {
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `三模型评估报告_${taskId}_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      } else {
        alert('下载报告失败');
      }
    } catch (error) {
      alert('下载报告失败: ' + error.message);
    }
  };

  // 如果未认证，显示登录/注册界面
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="w-full max-w-md p-8 bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-blue-600/20 rounded-2xl mb-6">
              <Brain className="w-10 h-10 text-blue-400" />
            </div>
            <h1 className="text-3xl font-bold text-white mb-2">InteractComp</h1>
            <p className="text-slate-400">多用户标注质量测试平台</p>
          </div>

          <div className="flex mb-6">
            <button
              onClick={() => setAuthMode('login')}
              className={`flex-1 py-2 px-4 text-sm font-medium rounded-l-lg border ${
                authMode === 'login' 
                  ? 'bg-blue-600 border-blue-600 text-white' 
                  : 'bg-slate-700 border-slate-600 text-slate-300 hover:bg-slate-600'
              }`}
            >
              登录
            </button>
            <button
              onClick={() => setAuthMode('register')}
              className={`flex-1 py-2 px-4 text-sm font-medium rounded-r-lg border ${
                authMode === 'register' 
                  ? 'bg-blue-600 border-blue-600 text-white' 
                  : 'bg-slate-700 border-slate-600 text-slate-300 hover:bg-slate-600'
              }`}
            >
              注册
            </button>
          </div>

          <form onSubmit={handleAuth} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">用户名</label>
              <input
                type="text"
                value={authForm.username}
                onChange={(e) => setAuthForm({...authForm, username: e.target.value})}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="请输入用户名"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">密码</label>
              <input
                type="password"
                value={authForm.password}
                onChange={(e) => setAuthForm({...authForm, password: e.target.value})}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="请输入密码"
                required
              />
            </div>

            {authMode === 'register' && (
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">显示名称</label>
                <input
                  type="text"
                  value={authForm.displayName}
                  onChange={(e) => setAuthForm({...authForm, displayName: e.target.value})}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="请输入显示名称（可选）"
                />
              </div>
            )}

            <button
              type="submit"
              className="w-full py-3 px-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg font-medium hover:from-blue-700 hover:to-purple-700 transition-colors flex items-center justify-center gap-2"
            >
              {authMode === 'login' ? <LogIn className="w-4 h-4" /> : <UserPlus className="w-4 h-4" />}
              {authMode === 'login' ? '登录' : '注册'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* 背景装饰 */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-1/2 -left-1/2 w-full h-full bg-gradient-to-r from-blue-600/10 to-purple-600/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute -bottom-1/2 -right-1/2 w-full h-full bg-gradient-to-r from-purple-600/10 to-pink-600/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
      </div>

      <div className="relative z-10">
        {/* 顶部导航 */}
        <div className="border-b border-slate-700/50 bg-slate-800/30 backdrop-blur-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-500 rounded-xl flex items-center justify-center">
                    <Brain className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h1 className="text-xl font-bold text-white">InteractComp</h1>
                    <p className="text-xs text-slate-400">多用户标注质量测试平台</p>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className="flex items-center gap-4 text-sm text-slate-300">
                  <div className="flex items-center gap-2">
                    <User className="w-4 h-4" />
                    <span>欢迎，{currentUser?.display_name || currentUser?.username}</span>
                  </div>
                  <div className="flex items-center gap-2 px-2 py-1 bg-slate-800 rounded">
                    <Activity className="w-4 h-4" />
                    <span>并发任务: {systemStatus.running_tasks}/{systemStatus.max_concurrent_tasks}</span>
                  </div>
                </div>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 px-3 py-2 text-sm bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  登出
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* 主要内容 */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* 标签页导航 */}
          <div className="flex space-x-1 bg-slate-800/50 backdrop-blur-sm p-1 rounded-xl mb-8">
            {[
              { id: 'upload', label: '文件上传', icon: Upload },
              { id: 'results', label: '测试结果', icon: BarChart3 },
              { id: 'tasks', label: '任务管理', icon: FileText },
              { id: 'community', label: '社区数据', icon: Users }
            ].map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-lg text-sm font-medium transition-all ${
                  activeTab === id
                    ? 'bg-blue-600 text-white shadow-lg'
                    : 'text-slate-400 hover:text-slate-300 hover:bg-slate-700/50'
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </button>
            ))}
          </div>

          {/* 标签页内容 */}
          {/* 文件上传页面 */}
          {activeTab === 'upload' && (
            <div className="space-y-8">
              {/* 配置状态检查 */}
              <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50">
                <div className="flex items-center gap-3 mb-4">
                  <Key className="w-5 h-5 text-yellow-400" />
                  <h3 className="text-lg font-semibold text-white">配置状态检查</h3>
                  <button
                    onClick={checkConfigStatus}
                    className="ml-auto px-3 py-1 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
                  >
                    刷新状态
                  </button>
                </div>
                
                {configStatus ? (
                  <div className="space-y-3">
                    {configStatus.ready ? (
                      <div>
                        <p className="text-green-300 font-semibold mb-2">✅ 配置就绪，可以开始测试</p>
                        <div className="text-sm text-slate-400">
                          <p>📁 配置文件: {configStatus.config_path || 'config2.yaml'}</p>
                          <p>🤖 评估模型: {configStatus.configured_models?.join(', ') || configStatus.required_models?.join(', ')}</p>
                        </div>
                      </div>
                    ) : (
                      <div>
                        <p className="text-red-300 font-semibold mb-2">❌ 配置未就绪</p>
                        <div className="text-sm text-slate-400">
                          <p>📄 错误: {configStatus.error}</p>
                          <p>📋 需要的模型: {configStatus.required_models?.join(', ')}</p>
                          <p>💡 请检查 config2.yaml 文件中的 API Keys 配置</p>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-slate-400">
                    <Clock className="w-4 h-4 animate-spin" />
                    <span>检查配置状态中...</span>
                  </div>
                )}
              </div>

              {/* 文件上传区域 */}
              <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50">
                <div className="flex items-center gap-3 mb-6">
                  <Upload className="w-5 h-5 text-blue-400" />
                  <h3 className="text-lg font-semibold text-white">上传数据文件</h3>
                </div>

                <div 
                  className="border-2 border-dashed border-slate-600 rounded-xl p-8 text-center hover:border-blue-500 transition-colors cursor-pointer"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Upload className="w-12 h-12 text-slate-400 mx-auto mb-4" />
                  <p className="text-slate-300 mb-2">点击上传或拖拽文件到此区域</p>
                  <p className="text-sm text-slate-500">支持 .jsonl 和 .json 格式</p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept=".jsonl,.json"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                </div>

                {/* 文件列表 */}
                {files.length > 0 && (
                  <div className="mt-6">
                    <h4 className="text-sm font-medium text-slate-300 mb-3">已上传文件 ({files.length})</h4>
                    <div className="space-y-2">
                      {files.map((file) => (
                        <div key={file.id} className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg">
                          <div className="flex items-center gap-3">
                            <FileText className="w-4 h-4 text-blue-400" />
                            <span className="text-white text-sm">{file.name}</span>
                            <span className="text-xs text-slate-400">({formatFileSize(file.size)})</span>
                          </div>
                          <button
                            onClick={() => removeFile(file.id)}
                            className="text-red-400 hover:text-red-300 text-sm"
                          >
                            移除
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 开始测试按钮 */}
                <div className="mt-8 flex justify-center">
                  <button
                    onClick={startTesting}
                    disabled={files.length === 0 || !configStatus?.ready || isRunning}
                    className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 disabled:from-gray-600 disabled:to-gray-600 text-white rounded-xl font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:from-blue-700 hover:to-purple-700 transition-colors"
                  >
                    <Play className="w-5 h-5" />
                    开始三模型评估
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 测试结果页面 */}
          {activeTab === 'results' && (
            <div className="space-y-6">
              {isRunning ? (
                <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-8 border border-slate-700/50 text-center">
                  <div className="inline-flex items-center justify-center w-20 h-20 bg-blue-600/20 rounded-2xl mb-6">
                    <Cpu className="w-10 h-10 text-blue-400 animate-pulse" />
                  </div>
                  <h3 className="text-2xl font-bold text-white mb-4">正在进行三模型评估</h3>
                  <div className="max-w-md mx-auto">
                    <div className="bg-slate-700 rounded-full h-2 mb-4">
                      <div 
                        className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all duration-500"
                        style={{ width: `${progress}%` }}
                      ></div>
                    </div>
                    <p className="text-slate-300 mb-2">进度: {progress}%</p>
                    <p className="text-sm text-slate-400">正在使用 GPT-5-mini、GPT-5、Claude-4-Sonnet 进行评估...</p>
                  </div>
                </div>
              ) : testResults ? (
                <div className="space-y-6">
                  {/* 评估结果概览 */}
                  <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50">
                    <div className="flex items-center gap-3 mb-6">
                      <BarChart3 className="w-5 h-5 text-green-400" />
                      <h3 className="text-lg font-semibold text-white">评估结果</h3>
                      <button
                        onClick={() => downloadReport(testResults.taskId)}
                        className="ml-auto flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm transition-colors"
                      >
                        <Download className="w-4 h-4" />
                        下载报告
                      </button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                      <div className="bg-slate-700/30 rounded-xl p-4">
                        <div className="text-2xl font-bold text-blue-400">{testResults.totalQuestions}</div>
                        <div className="text-sm text-slate-400">总题目数</div>
                      </div>
                      <div className="bg-slate-700/30 rounded-xl p-4">
                        <div className="text-2xl font-bold text-green-400">{testResults.qualityPassedCount}</div>
                        <div className="text-sm text-slate-400">质量合格</div>
                      </div>
                      <div className="bg-slate-700/30 rounded-xl p-4">
                        <div className="text-2xl font-bold text-red-400">{testResults.qualityFailedCount}</div>
                        <div className="text-sm text-slate-400">质量不合格</div>
                      </div>
                      <div className="bg-slate-700/30 rounded-xl p-4">
                        <div className="text-2xl font-bold text-purple-400">${testResults.totalCost?.toFixed(4)}</div>
                        <div className="text-sm text-slate-400">总成本</div>
                      </div>
                    </div>

                    <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4">
                      <p className="text-blue-300 font-medium">🎯 评估逻辑说明</p>
                      <p className="text-slate-400 text-sm mt-1">
                        质量不合格率: {(testResults.qualityFailedRate * 100).toFixed(1)}% - 
                        当2个或以上AI模型答对时，表示标注质量不合格，需要增加题目难度
                      </p>
                    </div>
                  </div>

                  {/* 质量不合格项目详情 */}
                  {testResults.failedItems && testResults.failedItems.length > 0 && (
                    <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50">
                      <h3 className="text-lg font-semibold text-white mb-4">质量不合格项目 ({testResults.failedItems.length})</h3>
                      <div className="space-y-4">
                        {testResults.failedItems.slice(0, 5).map((item) => (
                          <div key={item.id} className="border border-slate-600 rounded-lg p-4">
                            <div className="mb-2">
                              <span className="text-sm font-medium text-slate-300">问题：</span>
                              <span className="text-white ml-2">{item.question}</span>
                            </div>
                            <div className="mb-2">
                              <span className="text-sm font-medium text-slate-300">正确答案：</span>
                              <span className="text-green-300 ml-2">{item.correctAnswer}</span>
                            </div>
                            <div className="text-sm text-slate-400">
                              答对模型数: {item.correctModelsCount}/3
                            </div>
                          </div>
                        ))}
                        {testResults.failedItems.length > 5 && (
                          <p className="text-slate-400 text-center">还有 {testResults.failedItems.length - 5} 个项目，请下载完整报告查看</p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-8 border border-slate-700/50 text-center">
                  <div className="inline-flex items-center justify-center w-20 h-20 bg-slate-700/50 rounded-2xl mb-6">
                    <BarChart3 className="w-10 h-10 text-slate-400" />
                  </div>
                  <h3 className="text-2xl font-bold text-slate-300 mb-4">暂无测试结果</h3>
                  <p className="text-slate-400 mb-8">请先上传数据文件并开始评估</p>
                </div>
              )}
            </div>
          )}

          {/* 任务管理页面 */}
          {activeTab === 'tasks' && (
            <div className="space-y-6">
              <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50">
                <div className="flex items-center gap-3 mb-6">
                  <FileText className="w-5 h-5 text-blue-400" />
                  <h3 className="text-lg font-semibold text-white">我的任务</h3>
                  <span className="text-sm text-slate-400">({userTasks.length} 个任务)</span>
                </div>

                {userTasks.length > 0 ? (
                  <div className="space-y-4">
                    {getPaginatedData(userTasks, userTasksPagination.currentPage, userTasksPagination.pageSize).map((task) => (
                      <div key={task.task_id} className="border border-slate-600 rounded-lg p-4">
                        <div className="flex justify-between items-start mb-3">
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-white font-medium">任务 {task.task_id?.slice(0, 8)}</span>
                              <span className={`px-2 py-1 text-xs rounded-full ${
                                task.status === 'completed' ? 'bg-green-600/20 text-green-300' :
                                task.status === 'running' ? 'bg-blue-600/20 text-blue-300' :
                                task.status === 'failed' ? 'bg-red-600/20 text-red-300' :
                                'bg-yellow-600/20 text-yellow-300'
                              }`}>
                                {task.status}
                              </span>
                            </div>
                            <div className="text-sm text-slate-400">
                              创建时间: {new Date(task.created_at).toLocaleString()}
                            </div>
                          </div>
                          {task.status === 'completed' && (
                            <button
                              onClick={() => downloadReport(task.task_id)}
                              className="flex items-center gap-1 px-3 py-1 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
                            >
                              <Download className="w-3 h-3" />
                              下载
                            </button>
                          )}
                        </div>
                        
                        {task.status === 'completed' && (
                          <div className="grid grid-cols-4 gap-4 text-sm">
                            <div>
                              <span className="text-slate-400">总题目:</span>
                              <span className="text-white ml-1">{task.total_questions}</span>
                            </div>
                            <div>
                              <span className="text-slate-400">合格:</span>
                              <span className="text-green-300 ml-1">{task.quality_passed_count}</span>
                            </div>
                            <div>
                              <span className="text-slate-400">不合格:</span>
                              <span className="text-red-300 ml-1">{task.quality_failed_count}</span>
                            </div>
                            <div>
                              <span className="text-slate-400">成本:</span>
                              <span className="text-purple-300 ml-1">${task.total_cost?.toFixed(4)}</span>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                    
                    <Pagination
                      currentPage={userTasksPagination.currentPage}
                      pageSize={userTasksPagination.pageSize}
                      totalItems={userTasksPagination.totalItems}
                      onPageChange={handleUserTasksPageChange}
                    />
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <FileText className="w-12 h-12 text-slate-400 mx-auto mb-4" />
                    <p className="text-slate-300 mb-2">暂无任务</p>
                    <p className="text-sm text-slate-400">去上传文件开始第一个评估任务吧</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 社区数据页面 */}
          {activeTab === 'community' && (
            <div className="space-y-6">
              <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50">
                <div className="flex items-center gap-3 mb-6">
                  <Users className="w-5 h-5 text-purple-400" />
                  <h3 className="text-lg font-semibold text-white">社区任务数据</h3>
                  <span className="text-sm text-slate-400">({allTasks.length} 个任务)</span>
                </div>

                {allTasks.length > 0 ? (
                  <div className="space-y-4">
                    {getPaginatedData(allTasks, communityTasksPagination.currentPage, communityTasksPagination.pageSize).map((task) => (
                      <div key={task.task_id} className="border border-slate-600 rounded-lg p-4">
                        <div className="flex justify-between items-start mb-3">
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-white font-medium">任务 {task.task_id?.slice(0, 8)}</span>
                              <span className="text-sm text-blue-300">@{task.display_name || task.username}</span>
                              <span className={`px-2 py-1 text-xs rounded-full ${
                                task.status === 'completed' ? 'bg-green-600/20 text-green-300' :
                                task.status === 'running' ? 'bg-blue-600/20 text-blue-300' :
                                task.status === 'failed' ? 'bg-red-600/20 text-red-300' :
                                'bg-yellow-600/20 text-yellow-300'
                              }`}>
                                {task.status}
                              </span>
                            </div>
                            <div className="text-sm text-slate-400">
                              创建时间: {new Date(task.created_at).toLocaleString()}
                            </div>
                          </div>
                          {task.status === 'completed' && (
                            <button
                              onClick={() => downloadReport(task.task_id)}
                              className="flex items-center gap-1 px-3 py-1 text-sm bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors"
                            >
                              <Download className="w-3 h-3" />
                              查看
                            </button>
                          )}
                        </div>
                        
                        {task.status === 'completed' && (
                          <div className="grid grid-cols-4 gap-4 text-sm">
                            <div>
                              <span className="text-slate-400">总题目:</span>
                              <span className="text-white ml-1">{task.total_questions}</span>
                            </div>
                            <div>
                              <span className="text-slate-400">合格:</span>
                              <span className="text-green-300 ml-1">{task.quality_passed_count}</span>
                            </div>
                            <div>
                              <span className="text-slate-400">不合格:</span>
                              <span className="text-red-300 ml-1">{task.quality_failed_count}</span>
                            </div>
                            <div>
                              <span className="text-slate-400">成本:</span>
                              <span className="text-purple-300 ml-1">${task.total_cost?.toFixed(4)}</span>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                    
                    <Pagination
                      currentPage={communityTasksPagination.currentPage}
                      pageSize={communityTasksPagination.pageSize}
                      totalItems={communityTasksPagination.totalItems}
                      onPageChange={handleCommunityTasksPageChange}
                    />
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Users className="w-12 h-12 text-slate-400 mx-auto mb-4" />
                    <p className="text-slate-300 mb-2">暂无社区数据</p>
                    <p className="text-sm text-slate-400">成为第一个创建评估任务的用户吧</p>
                  </div>
                )}
              </div>

              {/* 用户统计 */}
              <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50">
                <div className="flex items-center gap-3 mb-4">
                  <Users className="w-5 h-5 text-green-400" />
                  <h3 className="text-lg font-semibold text-white">平台用户</h3>
                  <span className="text-sm text-slate-400">({allUsers.length} 位用户)</span>
                </div>

                {allUsers.length > 0 ? (
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                    {allUsers.map((user) => (
                      <div key={user.user_id} className="bg-slate-700/30 rounded-lg p-3">
                        <div className="flex items-center gap-2">
                          <User className="w-4 h-4 text-blue-400" />
                          <span className="text-white text-sm font-medium">{user.display_name || user.username}</span>
                        </div>
                        <div className="text-xs text-slate-400 mt-1">
                          加入时间: {new Date(user.created_at).toLocaleDateString()}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-slate-400">暂无用户数据</p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default InteractCompMultiUserPlatform;
