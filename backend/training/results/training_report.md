# 台风预测模型训练报告

## 基本信息
- **训练时间**: 2026-02-24 02:06:21
- **模型架构**: Transformer + LSTM 混合神经网络
- **训练设备**: cuda

## 数据配置
- **年份范围**: 2000 - 2020
- **输入序列长度**: 12 个时间点（过去72小时）
- **预测步数**: 8 个时间点（未来48小时）
- **训练样本数**: 12165
- **验证样本数**: 3041

## 模型参数
- **输入维度**: 14
- **隐藏层维度**: 256
- **LSTM层数**: 2
- **Transformer层数**: 2
- **注意力头数**: 8
- **总参数量**: 2,690,760

## 训练参数
- **批次大小**: 64
- **训练轮数**: 89 / 100
- **初始学习率**: 0.001
- **权重衰减**: 1e-05

## 评估结果

### 路径预测误差
| 指标 | 数值 |
|------|------|
| 纬度 MAE | 1.3937° |
| 纬度 RMSE | 2.1365° |
| 经度 MAE | 1.6701° |
| 经度 RMSE | 2.3216° |
| 路径 MAE | 0.0100° |
| 路径 RMSE | 0.0135° |

### 强度预测误差
| 指标 | 数值 |
|------|------|
| 气压 MAE | 0.0880 |
| 气压 RMSE | 0.2642 |
| 风速 MAE | 0.1585 m/s |
| 风速 RMSE | 0.2272 m/s |

### 按预测时间步的路径误差
| 预测时间 | 路径误差 |
|----------|----------|
| 6h | 0.0077° |
| 12h | 0.0074° |
| 18h | 0.0073° |
| 24h | 0.0076° |
| 30h | 0.0081° |
| 36h | 0.0081° |
| 42h | 0.0086° |
| 48h | 0.0254° |

### 置信度统计
- **平均置信度**: 0.9957
- **置信度标准差**: 0.0073

## 文件输出
- **最佳模型**: c:\code\.vscode\python\TyphoonAnalysis\backend\training\models\best_model.pth
- **最终模型**: c:\code\.vscode\python\TyphoonAnalysis\backend\training\models\final_model.pth
- **训练历史**: c:\code\.vscode\python\TyphoonAnalysis\backend\training\results\training_history.json
- **评估结果**: c:\code\.vscode\python\TyphoonAnalysis\backend\training\results\evaluation_results.json

## 可视化图表
1. 数据探索: c:\code\.vscode\python\TyphoonAnalysis\backend\training\results\data_exploration.png
2. 训练历史: c:\code\.vscode\python\TyphoonAnalysis\backend\training\results\training_history.png
3. 时间步误差: c:\code\.vscode\python\TyphoonAnalysis\backend\training\results\time_step_errors.png
4. 预测分析: c:\code\.vscode\python\TyphoonAnalysis\backend\training\results\prediction_analysis.png
5. 置信度分析: c:\code\.vscode\python\TyphoonAnalysis\backend\training\results\confidence_analysis.png
