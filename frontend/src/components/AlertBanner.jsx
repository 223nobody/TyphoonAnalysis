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
  const handleClose = (e) => {
    e.stopPropagation();
    setVisible(false);
  };

  // 查看详情 - 点击整个组件跳转
  const handleViewDetails = () => {
    navigate("/alert");
  };

  // 如果没有预警或横幅被关闭，不显示
  if (!visible || !bulletin) {
    return null;
  }

  return (
    <div
      onClick={handleViewDetails}
      style={{
        position: "relative",
        padding: "15px 20px",
        marginBottom: "20px",
        background: !hasBulletin
          ? "linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)"
          : "linear-gradient(135deg, #f87171 0%, #dc2626 100%)",
        borderRadius: "8px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
        animation: "slideDown 0.3s ease-out",
        color: "white",
        cursor: "pointer",
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
          {hasBulletin ? "🌀" : "🌊"}
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
              {hasBulletin ? "台风预警" : "台风监测"}
            </span>
            {hasBulletin && bulletin.typhoon_name && (
              <span style={{ fontSize: "14px", opacity: 0.9 }}>
                {bulletin.typhoon_name}
              </span>
            )}
          </div>
          <div style={{ fontSize: "14px", opacity: 0.95, lineHeight: "1.5" }}>
            {hasBulletin ? (
              <>
                <strong>强度等级：</strong>
                {bulletin.intensity || "未知"} | <strong>摘要：</strong>
                {bulletin.summary || bulletin.message || "暂无信息"}
              </>
            ) : (
              <>{bulletin.message || "当前没有活跃台风，系统正在持续监测中"}</>
            )}
          </div>
        </div>
      </div>
      <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
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
