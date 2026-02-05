/**
 * 历史记录组件 - 展示查询历史、收藏台风、生成报告
 */
import { useState, useEffect, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Card, Button, Spin, Empty, message, Row, Col, Tag } from "antd";
import {
  ArrowLeftOutlined,
  HistoryOutlined,
  StarOutlined,
  FileTextOutlined,
  LoadingOutlined,
} from "@ant-design/icons";
import {
  getQueryHistoryByCount,
  getCollectTyphoons,
  getUserReports,
} from "../services/api";
import "../styles/History.css";
import "../styles/common.css";

const STORAGE_TOKEN_KEY = "token";

const reportTypeMap = {
  impact: "影响评估报告",
  comprehensive: "综合分析报告",
  predict: "预测分析报告",
};

const getReportTypeText = (reportType) => {
  return reportTypeMap[reportType] || reportType || "综合报告";
};

const History = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const type = searchParams.get("type");
  const token = localStorage.getItem(STORAGE_TOKEN_KEY);

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState([]);
  const [error, setError] = useState(null);

  const renderTyphoonCard = useCallback((item, config) => {
    return (
      <Col xs={24} sm={12} md={8} lg={6} key={item.id}>
        <Card
          hoverable
          className="history-typhoon-card"
          onClick={() => config.navigateTo(item)}
        >
          <div className="typhoon-card-header">
            <Tag color="blue">{item.typhoon_id}</Tag>
            {item.created_at && (
              <span className="typhoon-card-time">
                {new Date(item.created_at).toLocaleDateString()}
              </span>
            )}
          </div>
          <div className="typhoon-card-body">
            <h3 className="typhoon-card-name">{item.typhoon_name}</h3>
          </div>
          {item.query_count !== undefined && (
            <div className="typhoon-card-footer">
              <Tag color="green">查询 {item.query_count} 次</Tag>
            </div>
          )}
        </Card>
      </Col>
    );
  }, []);

  const renderReportCard = useCallback((item, config) => {
    return (
      <Col xs={24} sm={12} md={8} lg={6} key={item.id}>
        <Card
          hoverable
          className="history-report-card"
          onClick={() => config.navigateTo(item)}
        >
          <div className="report-card-header">
            <Tag color="purple">{getReportTypeText(item.report_type)}</Tag>
            <span className="report-card-time">
              {item.created_at
                ? new Date(item.created_at).toLocaleDateString()
                : "-"}
            </span>
          </div>
          <div className="report-card-body">
            <h3 className="report-card-name">
              {item.typhoon_name || "未命名报告"}
            </h3>
          </div>
        </Card>
      </Col>
    );
  }, []);

  const typeConfig = {
    query_count: {
      title: "查询历史",
      icon: <HistoryOutlined />,
      fetchData: () => getQueryHistoryByCount(20),
      renderCard: renderTyphoonCard,
      navigateTo: (item) => {
        if (item.typhoon_id) {
          navigate(`/visualization?typhoon_id=${item.typhoon_id}`);
        } else {
          message.error("台风ID不存在，无法跳转");
        }
      },
    },
    collect_count: {
      title: "收藏台风",
      icon: <StarOutlined />,
      fetchData: () => getCollectTyphoons(),
      renderCard: renderTyphoonCard,
      navigateTo: (item) => {
        if (item.typhoon_id) {
          navigate(`/typhoon?typhoon_id=${item.typhoon_id}`);
        } else {
          message.error("台风ID不存在，无法跳转");
        }
      },
    },
    report_count: {
      title: "生成报告",
      icon: <FileTextOutlined />,
      fetchData: () => getUserReports(0, 20),
      renderCard: renderReportCard,
      navigateTo: (item) => {
        if (item.id) {
          navigate(`/report?report_id=${item.id}`);
        } else {
          message.error("报告ID不存在，无法跳转");
        }
      },
    },
  };

  const handleBack = useCallback(() => {
    navigate("/user-center");
  }, [navigate]);

  const handleRetry = useCallback(() => {
    window.location.reload();
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      if (!token) {
        message.error("请先登录");
        navigate("/login");
        return;
      }

      if (!type || !typeConfig[type]) {
        setError("无效的页面类型");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        const config = typeConfig[type];
        const result = await config.fetchData();

        if (!result) {
          throw new Error("未返回数据");
        }

        const items = result.items || result || [];

        if (!Array.isArray(items)) {
          console.error("数据格式错误:", result);
          throw new Error("数据格式错误");
        }

        setData(items);
      } catch (err) {
        console.error("加载数据失败:", err);
        const errorMessage =
          err.response?.data?.detail || err.message || "加载数据失败";
        setError(errorMessage);
        message.error(errorMessage);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [type, token, navigate]);

  if (loading) {
    return (
      <div className="history-loading-wrapper">
        <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} />} />
        <div className="loading-text">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="history-error-wrapper">
        <Empty description={error} />
        <div className="error-actions">
          <Button type="primary" onClick={handleRetry}>
            重试
          </Button>
          <Button onClick={handleBack}>返回用户中心</Button>
        </div>
      </div>
    );
  }

  const config = typeConfig[type];

  return (
    <div className="history-wrapper">
      <div className="history-container">
        <div className="history-header">
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={handleBack}
            className="history-back-button"
            style={{ cursor: "pointer", transition: "all 0.2s ease" }}
          >
            返回用户中心
          </Button>
          <h2 className="history-title">
            {config.icon} {config.title}
          </h2>
        </div>

        <div className="history-content">
          {data.length === 0 ? (
            <Empty description="暂无数据" />
          ) : (
            <Row gutter={[16, 16]}>
              {data.map((item) => config.renderCard(item, config))}
            </Row>
          )}
        </div>
      </div>
    </div>
  );
};

export default History;
