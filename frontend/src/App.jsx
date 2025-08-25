import React, { useState, useRef } from 'react';
import { Upload, Play, Download, Settings, FileText, BarChart3, CheckCircle, XCircle, Clock, AlertCircle, Key, Zap, Target, TrendingUp, Brain, Search } from 'lucide-react';

const ModernAnnotationTestingPlatform = () => {
  const [activeTab, setActiveTab] = useState('upload');
  const [files, setFiles] = useState([]);
  const [apiConfig, setApiConfig] = useState({
    llmModel: 'gpt-4o',
    graderModel: 'gpt-4o',
    apiKey: '',
    baseUrl: 'https://api.openai.com/v1',
    maxTurns: 5,
    searchEngine: 'llm_knowledge',
    googleApiKey: ''  // Google/Serper API Key
  });
  const [testResults, setTestResults] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const fileInputRef = useRef(null);

  const handleFileUpload = async (event) => {
    const uploadedFiles = Array.from(event.target.files);
    
    for (const file of uploadedFiles) {
      const formData = new FormData();
      formData.append('file', file);
      
      try {
        const response = await fetch('/upload', {
          method: 'POST',
          body: formData
        });
        
        if (response.ok) {
          const result = await response.json();
          setFiles(prev => [...prev, {
            id: result.file_id,
            name: result.filename,
            size: result.size,
            file: file,
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

  const removeFile = (fileId) => {
    setFiles(prev => prev.filter(file => file.id !== fileId));
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const startTesting = async () => {
    if (files.length === 0) {
      alert('请先上传数据文件');
      return;
    }
    if (!apiConfig.apiKey) {
      alert('请先配置 OpenAI API Key');
      return;
    }
    if (apiConfig.searchEngine === 'google' && !apiConfig.googleApiKey) {
      alert('使用 Google 搜索需要配置 Serper API Key');
      return;
    }

    setIsRunning(true);
    setProgress(0);
    setActiveTab('results');

    try {
      const fileIds = files.map(f => f.id);
      const testConfig = {
        llm_config: apiConfig.llmModel,
        user_config: apiConfig.graderModel, 
        api_key: apiConfig.apiKey,
        base_url: apiConfig.baseUrl,
        max_turns: apiConfig.maxTurns,
        search_engine_type: apiConfig.searchEngine,
        google_api_key: apiConfig.googleApiKey,  // 传递Google API Key
        max_concurrent_tasks: 1
      };

      const startResponse = await fetch('/test/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_ids: fileIds,
          config: testConfig
        })
      });

      if (!startResponse.ok) {
        throw new Error('启动测试失败');
      }

      const { task_id } = await startResponse.json();

      const pollStatus = async () => {
        try {
          const statusResponse = await fetch(`/test/${task_id}`);
          const status = await statusResponse.json();
          
          setProgress(status.progress || 0);

          if (status.status === 'completed') {
            // 修正REMIND逻辑：模型答错率 = 标注质量分
            const modelCorrectRate = status.average_score; // 模型正确率
            const annotationQualityScore = 1 - modelCorrectRate; // 标注质量分 = 1 - 模型正确率
            const goodAnnotations = Math.round(annotationQualityScore * status.total_questions); // 好的标注数量
            const needImprovement = status.total_questions - goodAnnotations; // 需要改进的数量
            
            const results = {
              taskId: task_id,
              totalQuestions: status.total_questions,
              successfulTests: goodAnnotations,  // 好的标注（模型答错）
              failedTests: needImprovement,      // 需要改进（模型答对）
              averageScore: annotationQualityScore, // 标注质量分
              averageCost: status.average_cost,
              totalCost: status.total_cost,
              failedItems: status.failed_items?.map((item, index) => ({
                id: index + 1,
                question: item.question,
                expectedAnswer: item.expected_answer,
                actualAnswer: item.actual_answer,
                reason: item.reason
              })) || []
            };
            
            setTestResults(results);
            setIsRunning(false);
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

  const downloadReport = async () => {
    if (!testResults || !testResults.taskId) {
      alert('没有可下载的报告');
      return;
    }
    
    try {
      const response = await fetch(`/test/${testResults.taskId}/download-csv`);
      if (response.ok) {
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `interactcomp_test_results_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      } else {
        alert('下载报告失败');
      }
    } catch (error) {
      alert('下载报告失败: ' + error.message);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* 背景装饰 */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-1/2 -left-1/2 w-full h-full bg-gradient-to-r from-blue-600/10 to-purple-600/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute -bottom-1/2 -right-1/2 w-full h-full bg-gradient-to-l from-purple-600/10 to-pink-600/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
      </div>

      <div className="relative z-10 container mx-auto px-6 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-3 mb-4">
            <div className="p-3 bg-gradient-to-r from-blue-500 to-purple-600 rounded-2xl shadow-lg">
              <Brain className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
              InteractComp 标注质量测试平台
            </h1>
          </div>
          <p className="text-xl text-slate-300 mb-6">
            智能评估你的标注数据质量，让模型答错才是好标注
          </p>
          <div className="inline-flex items-center gap-2 px-6 py-3 bg-blue-500/20 border border-blue-500/30 rounded-full text-blue-300">
            <Target className="w-5 h-5" />
            <span className="font-medium">测试原理：优秀的标注应该让AI模型难以找到正确答案</span>
          </div>
        </div>

        {/* Navigation */}
        <div className="bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 rounded-2xl mb-8 overflow-hidden">
          <div className="flex">
            {[
              { id: 'upload', label: '数据上传', icon: Upload, color: 'blue' },
              { id: 'config', label: '模型配置', icon: Settings, color: 'purple' },
              { id: 'results', label: '测试结果', icon: BarChart3, color: 'green' }
            ].map(tab => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex-1 flex items-center justify-center gap-3 px-6 py-4 font-semibold transition-all duration-300 ${
                    isActive
                      ? `bg-${tab.color}-500/20 text-${tab.color}-300 border-b-2 border-${tab.color}-400`
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/30'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Tab Content */}
          <div className="p-8">
            {activeTab === 'upload' && (
              <div className="space-y-8">
                <div 
                  className="border-2 border-dashed border-slate-600 hover:border-blue-500 rounded-2xl p-12 text-center transition-all duration-300 bg-slate-800/30 hover:bg-blue-500/5 group cursor-pointer"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <div className="mb-6">
                    <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-r from-blue-500 to-purple-600 rounded-2xl mb-4 group-hover:scale-110 transition-transform">
                      <Upload className="w-10 h-10 text-white" />
                    </div>
                  </div>
                  <h3 className="text-2xl font-bold text-slate-200 mb-3">上传 InteractComp 格式数据</h3>
                  <p className="text-slate-400 mb-6">支持 .jsonl 格式文件，包含 question/answer/context 字段</p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".jsonl,.json"
                    multiple
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                  <button className="inline-flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold rounded-xl hover:shadow-lg hover:shadow-blue-500/25 transition-all">
                    <Upload className="w-5 h-5" />
                    选择文件
                  </button>
                  <p className="text-xs text-slate-500 mt-4">💡 记住：优秀的标注会让模型答错！</p>
                </div>

                {files.length > 0 && (
                  <div className="space-y-4">
                    <h3 className="text-xl font-semibold text-slate-200 flex items-center gap-2">
                      <FileText className="w-6 h-6 text-blue-400" />
                      已上传文件 ({files.length})
                    </h3>
                    <div className="grid gap-3">
                      {files.map(file => (
                        <div key={file.id} className="flex items-center justify-between p-4 bg-slate-700/50 backdrop-blur-sm border border-slate-600/50 rounded-xl hover:bg-slate-700/70 transition-colors">
                          <div className="flex items-center gap-4">
                            <div className="p-2 bg-blue-500/20 rounded-lg">
                              <FileText className="w-6 h-6 text-blue-400" />
                            </div>
                            <div>
                              <p className="font-medium text-slate-200">{file.name}</p>
                              <p className="text-sm text-slate-400">{formatFileSize(file.size)}</p>
                            </div>
                          </div>
                          <button
                            onClick={() => removeFile(file.id)}
                            className="p-2 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors"
                          >
                            <XCircle className="w-5 h-5" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'config' && (
              <div className="max-w-2xl mx-auto space-y-8">
                <div className="text-center mb-8">
                  <div className="inline-flex items-center gap-2 p-3 bg-purple-500/20 rounded-xl mb-4">
                    <Settings className="w-6 h-6 text-purple-400" />
                    <span className="font-semibold text-purple-300">AI 模型配置</span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-3">
                    <label className="flex items-center gap-2 text-sm font-semibold text-slate-300">
                      <Key className="w-4 h-4 text-yellow-400" />
                      OpenAI API Key *
                    </label>
                    <input
                      type="password"
                      value={apiConfig.apiKey}
                      onChange={(e) => setApiConfig(prev => ({ ...prev, apiKey: e.target.value }))}
                      className="w-full p-4 bg-slate-700/50 border border-slate-600 rounded-xl text-slate-200 placeholder-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none transition-all"
                      placeholder="sk-..."
                    />
                  </div>

                  <div className="space-y-3">
                    <label className="flex items-center gap-2 text-sm font-semibold text-slate-300">
                      <Search className="w-4 h-4 text-orange-400" />
                      Google搜索 API Key
                      {apiConfig.searchEngine === 'google' && <span className="text-red-400">*</span>}
                    </label>
                    <input
                      type="password"
                      value={apiConfig.googleApiKey}
                      onChange={(e) => setApiConfig(prev => ({ ...prev, googleApiKey: e.target.value }))}
                      className="w-full p-4 bg-slate-700/50 border border-slate-600 rounded-xl text-slate-200 placeholder-slate-400 focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 outline-none transition-all"
                      placeholder="输入你的Google搜索API Key"
                      disabled={apiConfig.searchEngine !== 'google'}
                    />
                    {apiConfig.searchEngine === 'google' && (
                      <div className="p-3 bg-orange-500/10 border border-orange-500/20 rounded-lg">
                        <p className="text-xs text-orange-300 mb-2">
                          💡 支持多种Google搜索API服务：
                        </p>
                        <ul className="text-xs text-orange-400 space-y-1">
                          <li>• <strong>Serper.dev</strong> - 快速便宜的搜索API</li>
                          <li>• <strong>Google Custom Search</strong> - 官方搜索API</li>  
                          <li>• <strong>SerpApi</strong> - 专业搜索API服务</li>
                          <li>• <strong>其他兼容服务</strong> - 任何Google搜索API</li>
                        </ul>
                      </div>
                    )}
                  </div>

                  <div className="space-y-3">
                    <label className="text-sm font-semibold text-slate-300">API 端点</label>
                    <input
                      type="text"
                      value={apiConfig.baseUrl}
                      onChange={(e) => setApiConfig(prev => ({ ...prev, baseUrl: e.target.value }))}
                      className="w-full p-4 bg-slate-700/50 border border-slate-600 rounded-xl text-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 outline-none transition-all"
                    />
                  </div>

                  <div className="space-y-3">
                    <label className="flex items-center gap-2 text-sm font-semibold text-slate-300">
                      <Search className="w-4 h-4 text-orange-400" />
                      搜索引擎
                    </label>
                    <select
                      value={apiConfig.searchEngine}
                      onChange={(e) => setApiConfig(prev => ({ ...prev, searchEngine: e.target.value }))}
                      className="w-full p-4 bg-slate-700/50 border border-slate-600 rounded-xl text-slate-200 focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 outline-none transition-all"
                    >
                      <option value="llm_knowledge">LLM Knowledge (免费)</option>
                      <option value="google">Google Search (需要API Key)</option>
                      <option value="wikipedia">Wikipedia (免费)</option>
                    </select>
                    {apiConfig.searchEngine === 'google' && (
                      <div className="p-3 bg-orange-500/10 border border-orange-500/20 rounded-lg">
                        <p className="text-xs text-orange-300">
                          💡 Google搜索能提供最新信息，有助于找到隐藏答案
                        </p>
                      </div>
                    )}
                  </div>

                  <div className="space-y-3">
                    <label className="flex items-center gap-2 text-sm font-semibold text-slate-300">
                      <Brain className="w-4 h-4 text-blue-400" />
                      主评估模型
                    </label>
                    <select
                      value={apiConfig.llmModel}
                      onChange={(e) => setApiConfig(prev => ({ ...prev, llmModel: e.target.value }))}
                      className="w-full p-4 bg-slate-700/50 border border-slate-600 rounded-xl text-slate-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none transition-all"
                    >
                      <option value="gpt-4o">GPT-4o</option>
                      <option value="gpt-4o-mini">GPT-4o Mini</option>
                      <option value="o3">O3</option>
                    </select>
                  </div>

                  <div className="space-y-3">
                    <label className="flex items-center gap-2 text-sm font-semibold text-slate-300">
                      <Target className="w-4 h-4 text-green-400" />
                      评分模型
                    </label>
                    <select
                      value={apiConfig.graderModel}
                      onChange={(e) => setApiConfig(prev => ({ ...prev, graderModel: e.target.value }))}
                      className="w-full p-4 bg-slate-700/50 border border-slate-600 rounded-xl text-slate-200 focus:border-green-500 focus:ring-2 focus:ring-green-500/20 outline-none transition-all"
                    >
                      <option value="gpt-4o">GPT-4o</option>
                      <option value="gpt-4o-mini">GPT-4o Mini</option>
                      <option value="o3">O3</option>
                    </select>
                  </div>

                  <div className="space-y-3">
                    <label className="text-sm font-semibold text-slate-300">最大推理轮数</label>
                    <input
                      type="number"
                      value={apiConfig.maxTurns}
                      onChange={(e) => setApiConfig(prev => ({ ...prev, maxTurns: parseInt(e.target.value) }))}
                      min="1"
                      max="10"
                      className="w-full p-4 bg-slate-700/50 border border-slate-600 rounded-xl text-slate-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 outline-none transition-all"
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'results' && (
              <div className="space-y-8">
                {isRunning ? (
                  <div className="text-center py-16">
                    <div className="inline-flex items-center justify-center w-24 h-24 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full mb-6 animate-spin">
                      <Zap className="w-12 h-12 text-white" />
                    </div>
                    <h3 className="text-2xl font-bold text-slate-200 mb-4">AI 正在分析你的标注质量...</h3>
                    <div className="max-w-md mx-auto">
                      <div className="w-full bg-slate-700 rounded-full h-3 mb-4 overflow-hidden">
                        <div 
                          className="h-3 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full transition-all duration-500 ease-out"
                          style={{ width: `${progress}%` }}
                        ></div>
                      </div>
                      <p className="text-slate-400">{Math.round(progress)}% 完成</p>
                    </div>
                  </div>
                ) : testResults ? (
                  <div className="space-y-8">
                    {/* Stats Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                      <div className="bg-gradient-to-br from-green-500/20 to-emerald-600/20 border border-green-500/30 rounded-2xl p-6 backdrop-blur-sm">
                        <div className="flex items-center justify-between mb-4">
                          <div>
                            <p className="text-green-300 font-semibold mb-1">标注质量分</p>
                            <p className="text-3xl font-bold text-white">
                              {(testResults.averageScore * 100).toFixed(1)}%
                            </p>
                            <p className="text-xs text-green-400 mt-1">模型答错率</p>
                          </div>
                          <div className="p-3 bg-green-500/20 rounded-xl">
                            <TrendingUp className="w-8 h-8 text-green-400" />
                          </div>
                        </div>
                        <div className="flex items-center gap-2 text-sm text-green-300">
                          <CheckCircle className="w-4 h-4" />
                          质量评级：{testResults.averageScore > 0.7 ? '优秀' : testResults.averageScore > 0.5 ? '良好' : '需要改进'}
                        </div>
                      </div>

                      <div className="bg-gradient-to-br from-blue-500/20 to-cyan-600/20 border border-blue-500/30 rounded-2xl p-6 backdrop-blur-sm">
                        <div className="flex items-center justify-between mb-4">
                          <div>
                            <p className="text-blue-300 font-semibold mb-1">总问题数</p>
                            <p className="text-3xl font-bold text-white">{testResults.totalQuestions}</p>
                          </div>
                          <div className="p-3 bg-blue-500/20 rounded-xl">
                            <FileText className="w-8 h-8 text-blue-400" />
                          </div>
                        </div>
                      </div>

                      <div className="bg-gradient-to-br from-red-500/20 to-rose-600/20 border border-red-500/30 rounded-2xl p-6 backdrop-blur-sm">
                        <div className="flex items-center justify-between mb-4">
                          <div>
                            <p className="text-red-300 font-semibold mb-1">需要改进</p>
                            <p className="text-3xl font-bold text-white">{testResults.failedTests}</p>
                            <p className="text-xs text-red-400 mt-1">模型答对了</p>
                          </div>
                          <div className="p-3 bg-red-500/20 rounded-xl">
                            <AlertCircle className="w-8 h-8 text-red-400" />
                          </div>
                        </div>
                      </div>

                      <div className="bg-gradient-to-br from-purple-500/20 to-violet-600/20 border border-purple-500/30 rounded-2xl p-6 backdrop-blur-sm">
                        <div className="flex items-center justify-between mb-4">
                          <div>
                            <p className="text-purple-300 font-semibold mb-1">测试成本</p>
                            <p className="text-3xl font-bold text-white">${testResults.totalCost?.toFixed(3)}</p>
                          </div>
                          <div className="p-3 bg-purple-500/20 rounded-xl">
                            <BarChart3 className="w-8 h-8 text-purple-400" />
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Failed Items */}
                    {testResults.failedItems.length > 0 && (
                      <div className="bg-slate-800/50 border border-orange-500/30 rounded-2xl overflow-hidden backdrop-blur-sm">
                        <div className="bg-gradient-to-r from-orange-500/20 to-red-500/20 p-6 border-b border-orange-500/20">
                          <h3 className="text-xl font-bold text-slate-200 flex items-center gap-3">
                            <AlertCircle className="w-6 h-6 text-orange-400" />
                            需要优化的问题 ({testResults.failedItems.length})
                          </h3>
                          <p className="text-slate-400 mt-2">这些问题对AI来说太简单了，建议增加难度和混淆性</p>
                        </div>
                        <div className="divide-y divide-slate-700">
                          {testResults.failedItems.map(item => (
                            <div key={item.id} className="p-6 hover:bg-slate-700/30 transition-colors">
                              <div className="space-y-4">
                                <div>
                                  <p className="font-semibold text-slate-300 mb-2">问题:</p>
                                  <p className="text-slate-400 bg-slate-700/50 p-4 rounded-xl leading-relaxed">{item.question}</p>
                                </div>
                                
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                  <div>
                                    <p className="font-semibold text-blue-300 mb-2">正确答案（隐藏）:</p>
                                    <p className="text-slate-300 bg-blue-500/10 border border-blue-500/20 p-4 rounded-xl">{item.expectedAnswer}</p>
                                  </div>
                                  <div>
                                    <p className="font-semibold text-green-300 mb-2">AI 回答（正确）:</p>
                                    <p className="text-slate-300 bg-green-500/10 border border-green-500/20 p-4 rounded-xl">{item.actualAnswer}</p>
                                  </div>
                                </div>
                                
                                <div>
                                  <p className="font-semibold text-orange-300 mb-2">改进建议:</p>
                                  <p className="text-slate-400 italic bg-orange-500/10 border border-orange-500/20 p-4 rounded-xl">{item.reason}</p>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Action Buttons */}
                    <div className="flex flex-wrap gap-4 justify-center">
                      <button
                        onClick={downloadReport}
                        className="inline-flex items-center gap-3 px-8 py-4 bg-gradient-to-r from-green-500 to-emerald-600 text-white font-semibold rounded-xl hover:shadow-lg hover:shadow-green-500/25 transition-all"
                      >
                        <Download className="w-5 h-5" />
                        下载CSV报告
                      </button>
                      <button
                        onClick={() => setTestResults(null)}
                        className="inline-flex items-center gap-3 px-8 py-4 bg-slate-700/50 border border-slate-600 text-slate-300 font-semibold rounded-xl hover:bg-slate-600/50 transition-all"
                      >
                        重新测试
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-16">
                    <div className="inline-flex items-center justify-center w-20 h-20 bg-slate-700/50 rounded-2xl mb-6">
                      <BarChart3 className="w-10 h-10 text-slate-400" />
                    </div>
                    <h3 className="text-2xl font-bold text-slate-300 mb-4">准备开始测试</h3>
                    <p className="text-slate-400 mb-8">上传 REMIND 格式数据并配置模型参数</p>
                    <div className="max-w-md mx-auto p-6 bg-blue-500/10 border border-blue-500/20 rounded-xl">
                      <p className="text-blue-300 font-medium">💡 测试提醒</p>
                      <p className="text-slate-400 text-sm mt-2">
                        REMIND 评估标注质量 - AI答错说明标注优秀，答对说明需要改进难度
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Start Test Button */}
        {!isRunning && !testResults && (
          <div className="text-center">
            <button
              onClick={startTesting}
              disabled={files.length === 0 || !apiConfig.apiKey || (apiConfig.searchEngine === 'google' && !apiConfig.googleApiKey)}
              className={`inline-flex items-center gap-3 px-12 py-4 text-xl font-bold rounded-2xl transition-all ${
                files.length === 0 || !apiConfig.apiKey || (apiConfig.searchEngine === 'google' && !apiConfig.googleApiKey)
                  ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
                  : 'bg-gradient-to-r from-blue-500 to-purple-600 text-white hover:shadow-xl hover:shadow-blue-500/25 hover:scale-105'
              }`}
            >
              <Play className="w-6 h-6" />
              开始智能测试
            </button>
            {(files.length === 0 || !apiConfig.apiKey || (apiConfig.searchEngine === 'google' && !apiConfig.googleApiKey)) && (
              <p className="text-slate-400 text-sm mt-4">
                {files.length === 0 ? '⚠️ 请先上传数据文件' : 
                 !apiConfig.apiKey ? '⚠️ 请先配置 OpenAI API Key' :
                 '⚠️ 使用 Google 搜索需要配置 Serper API Key'}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ModernAnnotationTestingPlatform;