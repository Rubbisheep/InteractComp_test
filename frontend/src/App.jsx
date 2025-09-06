import React, { useState, useRef } from 'react';
import { Upload, Play, Download, FileText, BarChart3, CheckCircle, XCircle, Clock, AlertCircle, Key, Zap, Target, TrendingUp, Brain, Cpu } from 'lucide-react';

const InteractCompTestingPlatform = () => {
  const [activeTab, setActiveTab] = useState('upload');
  const [files, setFiles] = useState([]);
  const [configStatus, setConfigStatus] = useState(null);
  const [testResults, setTestResults] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const fileInputRef = useRef(null);

  // 检查配置状态
  const checkConfigStatus = async () => {
    try {
      const response = await fetch('/config/status');
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const status = await response.json();
      setConfigStatus(status);
      console.log('配置状态:', status); // 调试日志
    } catch (error) {
      console.error('检查配置状态失败:', error);
      setConfigStatus({ 
        config_found: false, 
        ready: false, 
        error: `无法连接到后端服务: ${error.message}` 
      });
    }
  };

  // 组件加载时检查配置
  React.useEffect(() => {
    checkConfigStatus();
  }, []);

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
    
    // 检查配置状态
    if (!configStatus || !configStatus.ready) {
      alert('配置文件未就绪，请检查config2.yaml文件中的API Keys配置');
      return;
    }

    setIsRunning(true);
    setProgress(0);
    setActiveTab('results');

    try {
      const fileIds = files.map(f => f.id);
      const startResponse = await fetch('/test/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(fileIds),  
        });

        // const text = await startResponse.text();
        // if (!startResponse.ok) throw new Error(text);
        // alert('启动成功：' + text);

    //   const startResponse = await fetch('/test/start', {
    //     method: 'POST',
    //     headers: { 'Content-Type': 'application/json' },
    //     body: JSON.stringify({
    //       file_ids: fileIds
    //     })
    //   });

    //   if (!startResponse.ok) {
    //     const errorData = await startResponse.json();
    //     throw new Error(errorData.detail || '启动测试失败');
    //   }

      const { task_id } = await startResponse.json();

      const pollStatus = async () => {
        try {
          const statusResponse = await fetch(`/test/${task_id}`);
          const status = await statusResponse.json();
          
          setProgress(status.progress || 0);

          if (status.status === 'completed') {
            const results = {
              taskId: task_id,
              totalQuestions: status.total_questions,
              qualityPassedCount: status.quality_passed_count,  // 质量合格
              qualityFailedCount: status.quality_failed_count,  // 质量不合格  
              qualityFailedRate: status.quality_failed_rate,    // 质量不合格率
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
        a.download = `三模型评估报告_${new Date().toISOString().split('T')[0]}.csv`;
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
              InteractComp 三模型标注质量测试
            </h1>
          </div>
          <p className="text-xl text-slate-300 mb-6">
            自动使用 GPT-5-mini, GPT-5, Claude-sonnet-4-20250514 三个模型评估标注质量
          </p>
          <div className="inline-flex items-center gap-2 px-6 py-3 bg-blue-500/20 border border-blue-500/30 rounded-full text-blue-300">
            <Target className="w-5 h-5" />
            <span className="font-medium">评估标准：2个以上模型答对 = 标注质量不合格</span>
          </div>
        </div>

        {/* Navigation */}
        <div className="bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 rounded-2xl mb-8 overflow-hidden">
          <div className="flex">
            {[
              { id: 'upload', label: '数据上传', icon: Upload, color: 'blue' },
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
                {/* 配置状态显示区域 */}
                <div className={`border border-slate-600/50 rounded-xl p-6 ${configStatus?.ready ? 'bg-green-500/10 border-green-500/30' : 'bg-orange-500/10 border-orange-500/30'}`}>
                  <div className="flex items-center gap-3 mb-4">
                    {configStatus?.ready ? (
                      <CheckCircle className="w-6 h-6 text-green-400" />
                    ) : (
                      <AlertCircle className="w-6 h-6 text-orange-400" />
                    )}
                    <h3 className="text-xl font-bold text-slate-200">配置状态</h3>
                    <button
                      onClick={checkConfigStatus}
                      className="ml-auto px-3 py-1 text-sm bg-slate-600 hover:bg-slate-500 text-slate-200 rounded-lg transition-colors"
                    >
                      刷新
                    </button>
                    <button
                      onClick={() => {
                        console.log('当前配置状态:', configStatus);
                        alert('配置状态已输出到浏览器控制台，请按F12查看');
                      }}
                      className="ml-2 px-3 py-1 text-sm bg-blue-600 hover:bg-blue-500 text-slate-200 rounded-lg transition-colors"
                    >
                      调试
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
                            {configStatus.models_configured && (
                              <p>✅ 已配置: {configStatus.models_configured}/{configStatus.required_models?.length || 3}</p>
                            )}
                          </div>
                        </div>
                      ) : (
                        <div>
                          <p className="text-orange-300 font-semibold mb-2">⚠️ 配置需要完善</p>
                          {configStatus.config_found ? (
                            <div className="text-sm text-slate-400">
                              <p>📁 配置文件已找到</p>
                              <p>🤖 已配置模型: {configStatus.models_configured || 0}个</p>
                              {configStatus.missing_models?.length > 0 && (
                                <p className="text-orange-300 mt-1">
                                  缺少配置: {configStatus.missing_models.join(', ')}
                                </p>
                              )}
                            </div>
                          ) : (
                            <div className="text-sm text-orange-300">
                              <p>📁 {configStatus.error || '未找到 config2.yaml 配置文件'}</p>
                              {configStatus.suggestion && (
                                <p className="mt-1">{configStatus.suggestion}</p>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <Clock className="w-5 h-5 text-slate-400 animate-spin" />
                      <span className="text-slate-400">正在检查配置...</span>
                    </div>
                  )}
                </div>

                {/* 文件上传区域 */}
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
                  <p className="text-slate-400 mb-6">支持 .jsonl 格式文件，包含 domain/question/answer/wrong_answer/context 字段</p>
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
                  <p className="text-xs text-slate-500 mt-4">💡 优秀标注应该让多数AI模型难以找到正确答案</p>
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

            {activeTab === 'results' && (
              <div className="space-y-8">
                {isRunning ? (
                  <div className="text-center py-16">
                    <div className="inline-flex items-center justify-center w-24 h-24 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full mb-6 animate-spin">
                      <Zap className="w-12 h-12 text-white" />
                    </div>
                    <h3 className="text-2xl font-bold text-slate-200 mb-4">三个AI模型正在评估标注质量...</h3>
                    <div className="flex items-center justify-center gap-4 mb-6">
                      <div className="flex items-center gap-2">
                        <Cpu className="w-5 h-5 text-blue-400" />
                        <span className="text-slate-300">GPT-5-mini</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Brain className="w-5 h-5 text-green-400" />
                        <span className="text-slate-300">GPT-5</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Target className="w-5 h-5 text-purple-400" />
                        <span className="text-slate-300">Claude-sonnet-4-20250514</span>
                      </div>
                    </div>
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
                            <p className="text-green-300 font-semibold mb-1">质量合格率</p>
                            <p className="text-3xl font-bold text-white">
                              {((1 - testResults.qualityFailedRate) * 100).toFixed(1)}%
                            </p>
                            <p className="text-xs text-green-400 mt-1">少数模型答对</p>
                          </div>
                          <div className="p-3 bg-green-500/20 rounded-xl">
                            <CheckCircle className="w-8 h-8 text-green-400" />
                          </div>
                        </div>
                        <div className="flex items-center gap-2 text-sm text-green-300">
                          <CheckCircle className="w-4 h-4" />
                          质量合格：{testResults.qualityPassedCount}
                        </div>
                      </div>

                      <div className="bg-gradient-to-br from-red-500/20 to-rose-600/20 border border-red-500/30 rounded-2xl p-6 backdrop-blur-sm">
                        <div className="flex items-center justify-between mb-4">
                          <div>
                            <p className="text-red-300 font-semibold mb-1">质量不合格率</p>
                            <p className="text-3xl font-bold text-white">
                              {(testResults.qualityFailedRate * 100).toFixed(1)}%
                            </p>
                            <p className="text-xs text-red-400 mt-1">多数模型答对</p>
                          </div>
                          <div className="p-3 bg-red-500/20 rounded-xl">
                            <AlertCircle className="w-8 h-8 text-red-400" />
                          </div>
                        </div>
                        <div className="flex items-center gap-2 text-sm text-red-300">
                          <XCircle className="w-4 h-4" />
                          需要改进：{testResults.qualityFailedCount}
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

                      <div className="bg-gradient-to-br from-purple-500/20 to-violet-600/20 border border-purple-500/30 rounded-2xl p-6 backdrop-blur-sm">
                        <div className="flex items-center justify-between mb-4">
                          <div>
                            <p className="text-purple-300 font-semibold mb-1">评估成本</p>
                            <p className="text-3xl font-bold text-white">${testResults.totalCost?.toFixed(3)}</p>
                          </div>
                          <div className="p-3 bg-purple-500/20 rounded-xl">
                            <BarChart3 className="w-8 h-8 text-purple-400" />
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Model Evaluation Info */}
                    <div className="bg-slate-800/50 border border-blue-500/30 rounded-2xl p-6">
                      <h3 className="text-xl font-bold text-slate-200 mb-4 flex items-center gap-3">
                        <Brain className="w-6 h-6 text-blue-400" />
                        三模型评估详情
                      </h3>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {testResults.evaluationModels.map((model, index) => {
                          const colors = ['blue', 'green', 'purple'];
                          const icons = [Cpu, Brain, Target];
                          const Icon = icons[index];
                          const color = colors[index];
                          const modelKeys = ['gpt-5-mini', 'gpt-5', 'claude-sonnet-4-20250514'];
                          
                          return (
                            <div key={model} className={`p-4 bg-${color}-500/10 border border-${color}-500/20 rounded-xl`}>
                              <div className="flex items-center gap-3 mb-2">
                                <Icon className={`w-5 h-5 text-${color}-400`} />
                                <span className="font-semibold text-slate-200">{model}</span>
                              </div>
                              <p className={`text-sm text-${color}-300`}>参与标注质量评估</p>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Failed Items */}
                    {testResults.failedItems.length > 0 && (
                      <div className="bg-slate-800/50 border border-orange-500/30 rounded-2xl overflow-hidden backdrop-blur-sm">
                        <div className="bg-gradient-to-r from-orange-500/20 to-red-500/20 p-6 border-b border-orange-500/20">
                          <h3 className="text-xl font-bold text-slate-200 flex items-center gap-3">
                            <AlertCircle className="w-6 h-6 text-orange-400" />
                            质量不合格问题 ({testResults.failedItems.length})
                          </h3>
                          <p className="text-slate-400 mt-2">这些问题被多数AI模型答对，建议增加难度和混淆性</p>
                        </div>
                        <div className="divide-y divide-slate-700">
                          {testResults.failedItems.slice(0, 10).map(item => (
                            <div key={item.id} className="p-6 hover:bg-slate-700/30 transition-colors">
                              <div className="space-y-4">
                                <div>
                                  <p className="font-semibold text-slate-300 mb-2">问题:</p>
                                  <p className="text-slate-400 bg-slate-700/50 p-4 rounded-xl leading-relaxed">{item.question}</p>
                                </div>
                                
                                <div>
                                  <p className="font-semibold text-blue-300 mb-2">正确答案（隐藏）:</p>
                                  <p className="text-slate-300 bg-blue-500/10 border border-blue-500/20 p-4 rounded-xl">{item.correctAnswer}</p>
                                </div>
                                
                                <div>
                                  <p className="font-semibold text-orange-300 mb-2">模型答题情况 ({item.correctModelsCount}/3 答对):</p>
                                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                    {Object.entries(item.modelResults || {}).map(([modelName, result]) => (
                                      <div key={modelName} className={`p-3 rounded-lg ${result.correct ? 'bg-green-500/10 border border-green-500/20' : 'bg-red-500/10 border border-red-500/20'}`}>
                                        <div className="flex items-center gap-2 mb-2">
                                          {result.correct ? 
                                            <CheckCircle className="w-4 h-4 text-green-400" /> : 
                                            <XCircle className="w-4 h-4 text-red-400" />
                                          }
                                          <span className="text-sm font-semibold text-slate-300">{modelName}</span>
                                        </div>
                                        <p className="text-xs text-slate-400">{result.answer}</p>
                                      </div>
                                    ))}
                                  </div>
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
                        下载详细报告
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
                    <h3 className="text-2xl font-bold text-slate-300 mb-4">准备开始三模型评估</h3>
                    <p className="text-slate-400 mb-8">配置API Keys并上传数据文件</p>
                    <div className="max-w-md mx-auto p-6 bg-blue-500/10 border border-blue-500/20 rounded-xl">
                      <p className="text-blue-300 font-medium">🤖 评估逻辑</p>
                      <p className="text-slate-400 text-sm mt-2">
                        三个AI模型独立作答，2个以上答对表示标注质量不合格，需要增加难度
                      </p>
                      <p className="text-slate-500 text-xs mt-3">
                        💡 请确保config2.yaml文件已正确配置API Keys
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
              disabled={files.length === 0 || !configStatus?.ready}
              className={`inline-flex items-center gap-3 px-12 py-4 text-xl font-bold rounded-2xl transition-all ${
                files.length === 0 || !configStatus?.ready
                  ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
                  : 'bg-gradient-to-r from-blue-500 to-purple-600 text-white hover:shadow-xl hover:shadow-blue-500/25 hover:scale-105'
              }`}
            >
              <Play className="w-6 h-6" />
              开始三模型评估
            </button>
            {(files.length === 0 || !configStatus?.ready) && (
              <p className="text-slate-400 text-sm mt-4">
                {files.length === 0 ? '⚠️ 请先上传数据文件' : 
                 !configStatus?.ready ? '⚠️ 请先完善config2.yaml配置文件' :
                 ''}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default InteractCompTestingPlatform;