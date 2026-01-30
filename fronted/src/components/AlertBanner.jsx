/**
 * 预警通知横幅组件
 * 在主页顶部显示台风预警信息
 */
import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { getActiveAlerts } from "../services/api";

function AlertBanner() {
  const [bulletin, setBulletin] = useState(null);
  const [hasBulletin, setHasBulletin] = useState(false);
  const [visible, setVisible] = useState(true);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  // 加载台风预警
  const loadBulletin = async () => {
    try {
      setLoading(true);
      const data = await getActiveAlerts();

      // 使用后端返回的 has_bulletin 字段判断是否有活跃台风
      setHasBulletin(data.has_bulletin);

      // 检查是否有台风预警
      if (data.has_bulletin && data.bulletin) {
        setBulletin(data.bulletin);
        setVisible(true);
      } else {
        // 没有活跃台风时，设置一个空的 bulletin 对象用于显示"无活跃台风"状态
        setBulletin({ message: data.message || "当前没有活跃台风" });
        setVisible(true);
      }
    } catch (err) {
      console.error("加载台风预警失败:", err);
    } finally {
      setLoading(false);
    }
  };

  // 组件挂载时加载预警，并设置定时刷新
  useEffect(() => {
    // 立即执行一次
    loadBulletin();

    // 每小时刷新一次（3600000毫秒）
    const interval = setInterval(() => {
      loadBulletin();
    }, 3600000);

    return () => clearInterval(interval);
  }, []);

  // 关闭横幅
  const handleClose = () => {
    setVisible(false);
  };

  // 查看详情
  const handleViewDetails = () => {
    navigate("/alert");
  };

  // 如果没有预警或横幅被关闭，不显示
  if (!visible || !bulletin) {
    return null;
  }

  return (
    <div
      style={{
        position: "relative",
        padding: "15px 20px",
        marginBottom: "20px",
        background: !hasBulletin
          ? "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)"
          : "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        borderRadius: "8px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
        animation: "slideDown 0.3s ease-out",
        color: "white",
      }}
    >
      <div
        style={{ flex: 1, display: "flex", alignItems: "center", gap: "15px" }}
      >
        <div
          style={{
            fontSize: "24px",
            animation: "pulse 2s infinite",
          }}
        >
          🌀
        </div>
        <div style={{ flex: 1 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              marginBottom: "5px",
            }}
          >
            <span
              style={{
                fontWeight: "bold",
                fontSize: "16px",
              }}
            >
              台风预警
            </span>
            <span style={{ fontSize: "14px", opacity: 0.9 }}>
              {bulletin.typhoon_name}
            </span>
          </div>
          <div style={{ fontSize: "14px", opacity: 0.95, lineHeight: "1.5" }}>
            <strong>强度等级：</strong>
            {bulletin.intensity} | <strong>摘要：</strong>
            {bulletin.summary}
          </div>
        </div>
      </div>
      <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
        <button
          onClick={handleViewDetails}
          style={{
            padding: "8px 16px",
            background: "rgba(255, 255, 255, 0.2)",
            color: "white",
            border: "1px solid rgba(255, 255, 255, 0.3)",
            borderRadius: "6px",
            cursor: "pointer",
            fontSize: "14px",
            fontWeight: "500",
            transition: "all 0.2s",
          }}
          onMouseEnter={(e) => {
            e.target.style.background = "rgba(255, 255, 255, 0.3)";
          }}
          onMouseLeave={(e) => {
            e.target.style.background = "rgba(255, 255, 255, 0.2)";
          }}
        >
          查看详情
        </button>
        <button
          onClick={handleClose}
          style={{
            padding: "8px 12px",
            background: "transparent",
            border: "none",
            cursor: "pointer",
            fontSize: "20px",
            color: "white",
            transition: "opacity 0.2s",
          }}
          onMouseEnter={(e) => (e.target.style.opacity = "0.7")}
          onMouseLeave={(e) => (e.target.style.opacity = "1")}
          title="关闭"
        >
          ×
        </button>
      </div>

      <style>
        {`
                    @keyframes slideDown {
                        from {
                            opacity: 0;
                            transform: translateY(-20px);
                        }
                        to {
                            opacity: 1;
                            transform: translateY(0);
                        }
                    }
                    @keyframes pulse {
                        0%, 100% {
                            opacity: 1;
                        }
                        50% {
                            opacity: 0.7;
                        }
                    }
                `}
      </style>
    </div>
  );
}

export default AlertBanner;
