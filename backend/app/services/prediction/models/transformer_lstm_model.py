"""
Transformer + LSTM 混合模型

用于替代原有的LSTMTyphoonModel，提供更好的预测性能
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class TransformerLSTMModel(nn.Module):
    """
    Transformer + LSTM 混合模型
    
    架构：
    1. LSTM编码器 - 提取时序特征
    2. Transformer编码器 - 建模长程依赖
    3. 多步预测头 - 独立预测每个时间步
    4. 不确定性估计 - 输出预测分布
    """
    
    def __init__(
        self,
        input_size: int = 10,
        hidden_size: int = 256,
        num_lstm_layers: int = 2,
        num_transformer_layers: int = 2,
        num_heads: int = 8,
        output_size: int = 4,
        prediction_steps: int = 8,
        dropout: float = 0.2
    ):
        super().__init__()
        
        self.hidden_size = hidden_size
        self.prediction_steps = prediction_steps
        
        # LSTM编码器
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_lstm_layers,
            batch_first=True,
            dropout=dropout if num_lstm_layers > 1 else 0,
            bidirectional=False
        )
        
        # Transformer编码器
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_size,
            nhead=num_heads,
            dim_feedforward=hidden_size * 4,
            dropout=dropout,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_transformer_layers)
        
        # Layer Normalization
        self.layer_norm1 = nn.LayerNorm(hidden_size)
        self.layer_norm2 = nn.LayerNorm(hidden_size)
        
        # 预测头 - 为每个时间步独立预测均值和方差
        self.prediction_heads = nn.ModuleList([
            nn.Sequential(
                nn.Linear(hidden_size, hidden_size // 2),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_size // 2, output_size * 2)  # 均值和方差
            ) for _ in range(prediction_steps)
        ])
        
        # 置信度估计头
        self.confidence_head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Linear(hidden_size // 2, prediction_steps),
            nn.Sigmoid()
        )
        
        self._init_weights()
    
    def _init_weights(self):
        """初始化权重"""
        for name, param in self.lstm.named_parameters():
            if 'weight_ih' in name:
                nn.init.xavier_uniform_(param)
            elif 'weight_hh' in name:
                nn.init.orthogonal_(param)
            elif 'bias' in name:
                nn.init.zeros_(param)
        
        for head in self.prediction_heads:
            for layer in head:
                if isinstance(layer, nn.Linear):
                    nn.init.xavier_uniform_(layer.weight)
                    nn.init.zeros_(layer.bias)
    
    def forward(self, x):
        """
        前向传播
        
        Args:
            x: 输入序列 [batch, seq_len, input_size]
        
        Returns:
            predictions_mean: 预测均值 [batch, pred_steps, output_size]
            predictions_std: 预测标准差 [batch, pred_steps, output_size]
            confidence: 置信度 [batch, pred_steps]
        """
        # LSTM编码
        lstm_out, _ = self.lstm(x)
        lstm_out = self.layer_norm1(lstm_out)
        
        # Transformer编码
        transformer_out = self.transformer(lstm_out)
        transformer_out = self.layer_norm2(transformer_out + lstm_out)  # 残差连接
        
        # 取最后时刻的上下文
        context = transformer_out[:, -1, :]
        
        # 多步预测（输出均值和方差）
        predictions_mean = []
        predictions_std = []
        
        for head in self.prediction_heads:
            output = head(context)
            mean = output[..., :4]
            std = F.softplus(output[..., 4:]) + 1e-6  # 确保标准差为正
            predictions_mean.append(mean)
            predictions_std.append(std)
        
        predictions_mean = torch.stack(predictions_mean, dim=1)
        predictions_std = torch.stack(predictions_std, dim=1)
        
        # 置信度估计
        confidence = self.confidence_head(context)
        
        return predictions_mean, predictions_std, confidence
