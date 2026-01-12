/**
 * 图像分析组件
 */
import React, { useState } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

function ImageAnalysis() {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [result, setResult] = useState(null);

    // 图像分析表单
    const [analysisForm, setAnalysisForm] = useState({
        typhoonId: '',
        imageUrl: '',
    });

    // 处理图像分析
    const handleAnalysis = async () => {
        if (!analysisForm.typhoonId) {
            alert('请输入台风ID');
            return;
        }

        if (!analysisForm.imageUrl) {
            alert('请输入图像URL');
            return;
        }

        try {
            setLoading(true);
            setError(null);
            const response = await axios.post(`${API_BASE_URL}/analysis/satellite`, {
                typhoon_id: analysisForm.typhoonId,
                image_url: analysisForm.imageUrl,
            });
            setResult(response.data);
        } catch (err) {
            setError(err.response?.data?.detail || err.message || '图像分析失败');
        } finally {
            setLoading(false);
        }
    };

    // 渲染分析结果
    const renderResult = () => {
        if (!result) return null;

        return (
            <div className="info-card" style={{ marginTop: '20px' }}>
                <h4>🖼️ 图像分析结果</h4>
                
                {/* 基本信息 */}
                <div style={{ marginBottom: '20px' }}>
                    <p><strong>台风ID:</strong> {result.typhoon_id}</p>
                    <p><strong>分析时间:</strong> {result.analysis_time || new Date().toLocaleString('zh-CN')}</p>
                </div>

                {/* 图像预览 */}
                {analysisForm.imageUrl && (
                    <div style={{ marginBottom: '20px' }}>
                        <h5>卫星云图</h5>
                        <img 
                            src={analysisForm.imageUrl} 
                            alt="台风卫星云图" 
                            style={{ 
                                maxWidth: '100%', 
                                height: 'auto', 
                                borderRadius: '8px',
                                border: '1px solid #e5e7eb'
                            }}
                            onError={(e) => {
                                e.target.style.display = 'none';
                                e.target.nextSibling.style.display = 'block';
                            }}
                        />
                        <div style={{ display: 'none', padding: '20px', background: '#f3f4f6', borderRadius: '8px' }}>
                            <p style={{ margin: 0, color: '#6b7280' }}>图像加载失败</p>
                        </div>
                    </div>
                )}

                {/* 分析结果 */}
                {result.analysis && (
                    <div>
                        <h5>分析结果</h5>
                        <div style={{ background: '#f9fafb', padding: '15px', borderRadius: '8px' }}>
                            {typeof result.analysis === 'string' ? (
                                <p style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{result.analysis}</p>
                            ) : (
                                <div>
                                    {result.analysis.center && (
                                        <p><strong>台风中心:</strong> {result.analysis.center}</p>
                                    )}
                                    {result.analysis.intensity && (
                                        <p><strong>强度评估:</strong> {result.analysis.intensity}</p>
                                    )}
                                    {result.analysis.structure && (
                                        <p><strong>结构特征:</strong> {result.analysis.structure}</p>
                                    )}
                                    {result.analysis.trend && (
                                        <p><strong>发展趋势:</strong> {result.analysis.trend}</p>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* 详细数据 */}
                {result.details && (
                    <div style={{ marginTop: '15px' }}>
                        <h5>详细数据</h5>
                        <table>
                            <tbody>
                                {Object.entries(result.details).map(([key, value]) => (
                                    <tr key={key}>
                                        <td style={{ fontWeight: 'bold' }}>{key}</td>
                                        <td>{typeof value === 'object' ? JSON.stringify(value) : value}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        );
    };

    return (
        <div>
            <h2>🖼️ 图像分析</h2>

            <h3>卫星云图分析</h3>
            
            <div className="form-group">
                <label>台风ID</label>
                <input
                    type="text"
                    placeholder="例如: 2501"
                    value={analysisForm.typhoonId}
                    onChange={(e) => setAnalysisForm({ ...analysisForm, typhoonId: e.target.value })}
                />
            </div>

            <div className="form-group">
                <label>图像URL</label>
                <input
                    type="text"
                    placeholder="输入卫星云图URL"
                    value={analysisForm.imageUrl}
                    onChange={(e) => setAnalysisForm({ ...analysisForm, imageUrl: e.target.value })}
                />
            </div>

            <button className="btn" onClick={handleAnalysis} disabled={loading}>
                🔍 开始分析
            </button>

            <div className="info-card" style={{ marginTop: '15px' }}>
                <p style={{ margin: 0, fontSize: '13px', color: '#1e40af' }}>
                    💡 <strong>说明：</strong>
                </p>
                <ul style={{ margin: '8px 0 0 20px', fontSize: '12px', color: '#1e40af' }}>
                    <li>支持分析台风卫星云图</li>
                    <li>基于AI视觉模型识别台风特征</li>
                    <li>提供台风中心位置、强度评估等信息</li>
                    <li>图像URL需要是公开可访问的链接</li>
                </ul>
            </div>

            {/* 错误提示 */}
            {error && (
                <div className="error-message" style={{ marginTop: '20px' }}>
                    ❌ {error}
                </div>
            )}

            {/* 加载状态 */}
            {loading && <div className="loading">分析中</div>}

            {/* 结果显示 */}
            {result && renderResult()}
        </div>
    );
}

export default ImageAnalysis;

