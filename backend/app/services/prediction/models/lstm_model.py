"""
LSTM台风预测模型

基于LSTM网络的台风路径与强度联合预测模型
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Optional


class LSTMTyphoonModel(nn.Module):
    """
    LSTM台风路径与强度联合预测模型

    架构说明:
    - 输入: [batch_size, seq_len=12, input_size=10]
    - 输出: [batch_size, pred_steps=8, output_size=4]

    组件:
    1. LSTM编码器 (3层, hidden=128)
    2. Multi-Head Attention (8 heads)
    3. 多步预测头 (每个时间步独立)
    """

    def __init__(
        self,
        input_size: int = 10,
        hidden_size: int = 128,
        num_layers: int = 3,
        output_size: int = 4,
        prediction_steps: int = 8,
        dropout: float = 0.2,
        attention_heads: int = 8
    ):
        super().__init__()

        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.output_size = output_size
        self.prediction_steps = prediction_steps

        # LSTM编码器
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=False
        )

        # Layer Normalization
        self.layer_norm = nn.LayerNorm(hidden_size)

        # Multi-Head Attention
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_size,
            num_heads=attention_heads,
            dropout=dropout,
            batch_first=True
        )

        # 预测头 - 为每个预测时间步创建独立的预测头
        self.prediction_heads = nn.ModuleList([
            nn.Sequential(
                nn.Linear(hidden_size, hidden_size // 2),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_size // 2, output_size)
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

    def forward(
        self,
        x: torch.Tensor,
        return_attention: bool = False
    ) -> Tuple[torch.Tensor, torch.Tensor, Optional[torch.Tensor]]:
        """
        前向传播

        Args:
            x: 输入序列 [batch, seq_len, input_size]
            return_attention: 是否返回注意力权重

        Returns:
            predictions: 预测结果 [batch, pred_steps, output_size]
            confidence: 置信度 [batch, pred_steps]
            attention_weights: 注意力权重 (可选)
        """
        batch_size = x.size(0)

        # LSTM编码
        lstm_out, (hidden, cell) = self.lstm(x)
        # lstm_out: [batch, seq_len, hidden_size]

        # Layer Normalization
        lstm_out = self.layer_norm(lstm_out)

        # Multi-Head Attention
        attn_out, attn_weights = self.attention(lstm_out, lstm_out, lstm_out)
        # attn_out: [batch, seq_len, hidden_size]

        # 残差连接
        attn_out = attn_out + lstm_out

        # 取最后时刻的上下文向量
        context = attn_out[:, -1, :]  # [batch, hidden_size]

        # 多步预测
        predictions = []
        for i in range(self.prediction_steps):
            pred = self.prediction_heads[i](context)
            predictions.append(pred)

        predictions = torch.stack(predictions, dim=1)
        # predictions: [batch, pred_steps, output_size]

        # 置信度估计
        confidence = self.confidence_head(context)
        # confidence: [batch, pred_steps]

        if return_attention:
            return predictions, confidence, attn_weights

        return predictions, confidence, None


class SimpleTyphoonModel(nn.Module):
    """
    简化版台风预测模型 (用于无GPU环境或快速推理)

    使用更简单的架构，减少计算量
    """

    def __init__(
        self,
        input_size: int = 10,
        hidden_size: int = 64,
        num_layers: int = 2,
        output_size: int = 4,
        prediction_steps: int = 8,
        dropout: float = 0.2
    ):
        super().__init__()

        self.prediction_steps = prediction_steps

        # LSTM编码器
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )

        # 共享预测头
        self.prediction_head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size // 2, output_size * prediction_steps)
        )

        # 置信度头
        self.confidence_head = nn.Sequential(
            nn.Linear(hidden_size, prediction_steps),
            nn.Sigmoid()
        )

    def forward(
        self,
        x: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor, None]:
        """
        前向传播

        Args:
            x: 输入序列 [batch, seq_len, input_size]

        Returns:
            predictions: 预测结果 [batch, pred_steps, output_size]
            confidence: 置信度 [batch, pred_steps]
            None: 无注意力权重
        """
        # LSTM编码
        lstm_out, _ = self.lstm(x)

        # 取最后时刻
        context = lstm_out[:, -1, :]

        # 预测
        pred_flat = self.prediction_head(context)
        predictions = pred_flat.view(-1, self.prediction_steps, 4)

        # 置信度
        confidence = self.confidence_head(context)

        return predictions, confidence, None
