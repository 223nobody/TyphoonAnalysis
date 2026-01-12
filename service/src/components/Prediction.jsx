/**
 * 智能预测组件
 */
import React, { useState } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

function Prediction() {
    const [predictionType, setPredictionType] = useState('path');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [result, setResult] = useState(null);

    // 路径预测表单
    const [pathForm, setPathForm] = useState({
        typhoonId: '',
        hours: 24,
    });

    // 强度预测表单
    const [intensityForm, setIntensityForm] = useState({
        typhoonId: '',
        hours: 24,
    });

    // 处理路径预测
    const handlePathPrediction = async () => {
        if (!pathForm.typhoonId) {
            alert('请输入台风ID');
            return;
        }

        try {
            setLoading(true);
            setError(null);
            const response = await axios.post(`${API_BASE_URL}/prediction/path`, {
                typhoon_id: pathForm.typhoonId,
                hours: parseInt(pathForm.hours),
            });
            setResult({ type: 'path', data: response.data });
        } catch (err) {
            setError(err.response?.data?.detail || err.message || '路径预测失败');
        } finally {
            setLoading(false);
        }
    };

    // 处理强度预测
    const handleIntensityPrediction = async () => {
        if (!intensityForm.typhoonId) {
            alert('请输入台风ID');
            return;
        }

        try {
            setLoading(true);
            setError(null);
            const response = await axios.post(`${API_BASE_URL}/prediction/intensity`, {
                typhoon_id: intensityForm.typhoonId,
                hours: parseInt(intensityForm.hours),
            });
            setResult({ type: 'intensity', data: response.data });
        } catch (err) {
            setError(err.response?.data?.detail || err.message || '强度预测失败');
        } finally {
            setLoading(false);
        }
    };

    // 渲染路径预测表单
    const renderPathForm = () => (
        <div>
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '15px' }}>
                <div className="form-group">
                    <label>台风ID</label>
                    <input
                        type="text"
                        placeholder="例如: 2501"
                        value={pathForm.typhoonId}
                        onChange={(e) => setPathForm({ ...pathForm, typhoonId: e.target.value })}
                    />
                </div>
                <div className="form-group">
                    <label>预测时长（小时）</label>
                    <input
                        type="number"
                        placeholder="例如: 24"
                        min="6"
                        max="120"
                        value={pathForm.hours}
                        onChange={(e) => setPathForm({ ...pathForm, hours: e.target.value })}
                    />
                </div>
            </div>
            <button className="btn" onClick={handlePathPrediction} disabled={loading}>
                🎯 开始路径预测
            </button>
            <div className="info-card" style={{ marginTop: '15px' }}>
                <p style={{ margin: 0, fontSize: '13px', color: '#1e40af' }}>
                    💡 <strong>说明：</strong>路径预测基于历史数据和AI模型，预测未来台风移动轨迹
                </p>
            </div>
        </div>
    );

    // 渲染强度预测表单
    const renderIntensityForm = () => (
        <div>
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '15px' }}>
                <div className="form-group">
                    <label>台风ID</label>
                    <input
                        type="text"
                        placeholder="例如: 2501"
                        value={intensityForm.typhoonId}
                        onChange={(e) => setIntensityForm({ ...intensityForm, typhoonId: e.target.value })}
                    />
                </div>
                <div className="form-group">
                    <label>预测时长（小时）</label>
                    <input
                        type="number"
                        placeholder="例如: 24"
                        min="6"
                        max="120"
                        value={intensityForm.hours}
                        onChange={(e) => setIntensityForm({ ...intensityForm, hours: e.target.value })}
                    />
                </div>
            </div>
            <button className="btn" onClick={handleIntensityPrediction} disabled={loading}>
                🎯 开始强度预测
            </button>
            <div className="info-card" style={{ marginTop: '15px' }}>
                <p style={{ margin: 0, fontSize: '13px', color: '#1e40af' }}>
                    💡 <strong>说明：</strong>强度预测基于AI模型，预测未来台风强度变化趋势
                </p>
            </div>
        </div>
    );

    // 渲染路径预测结果
    const renderPathResult = (data) => {
        if (!data || !data.predictions || data.predictions.length === 0) {
            return (
                <div className="info-card">
                    <p>暂无预测数据</p>
                </div>
            );
        }

        return (
            <div className="info-card">
                <h4>🎯 路径预测结果</h4>
                <p><strong>台风ID:</strong> {data.typhoon_id}</p>
                <p><strong>预测时长:</strong> {data.hours} 小时</p>
                <p><strong>预测点数:</strong> {data.predictions.length}</p>
                
                <table style={{ marginTop: '15px' }}>
                    <thead>
                        <tr>
                            <th>时间</th>
                            <th>纬度</th>
                            <th>经度</th>
                            <th>置信度</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.predictions.map((pred, index) => (
                            <tr key={index}>
                                <td>{pred.time || `+${pred.hours || index * 6}h`}</td>
                                <td style={{ textAlign: 'center' }}>{pred.latitude?.toFixed(2) || 'N/A'}</td>
                                <td style={{ textAlign: 'center' }}>{pred.longitude?.toFixed(2) || 'N/A'}</td>
                                <td style={{ textAlign: 'center' }}>
                                    {pred.confidence ? `${(pred.confidence * 100).toFixed(1)}%` : 'N/A'}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        );
    };

    // 渲染强度预测结果
    const renderIntensityResult = (data) => {
        if (!data || !data.predictions || data.predictions.length === 0) {
            return (
                <div className="info-card">
                    <p>暂无预测数据</p>
                </div>
            );
        }

        return (
            <div className="info-card">
                <h4>🎯 强度预测结果</h4>
                <p><strong>台风ID:</strong> {data.typhoon_id}</p>
                <p><strong>预测时长:</strong> {data.hours} 小时</p>
                <p><strong>预测点数:</strong> {data.predictions.length}</p>
                
                <table style={{ marginTop: '15px' }}>
                    <thead>
                        <tr>
                            <th>时间</th>
                            <th>风速 (m/s)</th>
                            <th>气压 (hPa)</th>
                            <th>强度等级</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.predictions.map((pred, index) => (
                            <tr key={index}>
                                <td>{pred.time || `+${pred.hours || index * 6}h`}</td>
                                <td style={{ textAlign: 'center' }}>{pred.wind_speed?.toFixed(1) || 'N/A'}</td>
                                <td style={{ textAlign: 'center' }}>{pred.pressure?.toFixed(0) || 'N/A'}</td>
                                <td style={{ textAlign: 'center' }}>{pred.intensity || 'N/A'}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        );
    };

    return (
        <div>
            <h2>🎯 智能预测</h2>

            {/* 预测类型选择 */}
            <div className="form-group">
                <label>预测类型</label>
                <select value={predictionType} onChange={(e) => setPredictionType(e.target.value)}>
                    <option value="path">路径预测</option>
                    <option value="intensity">强度预测</option>
                </select>
            </div>

            {/* 根据类型渲染不同表单 */}
            {predictionType === 'path' && renderPathForm()}
            {predictionType === 'intensity' && renderIntensityForm()}

            {/* 错误提示 */}
            {error && (
                <div className="error-message" style={{ marginTop: '20px' }}>
                    ❌ {error}
                </div>
            )}

            {/* 加载状态 */}
            {loading && <div className="loading">预测中</div>}

            {/* 结果显示 */}
            {result && (
                <div style={{ marginTop: '20px' }}>
                    {result.type === 'path' && renderPathResult(result.data)}
                    {result.type === 'intensity' && renderIntensityResult(result.data)}
                </div>
            )}
        </div>
    );
}

export default Prediction;

