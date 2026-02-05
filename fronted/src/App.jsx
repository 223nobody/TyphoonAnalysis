/**
 * 主应用组件
 */
import React, { useState, useEffect, useRef } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  useNavigate,
  useLocation,
} from "react-router-dom";
import Header from "./components/Header";
import TabNavigation from "./components/TabNavigation";
import AlertBanner from "./components/AlertBanner";
import MapVisualization from "./components/MapVisualization";
import TyphoonQuery from "./components/TyphoonQuery";
import Prediction from "./components/Prediction";
import ImageAnalysis from "./components/ImageAnalysis";
import ReportGeneration from "./components/ReportGeneration";
import StatisticsPanel from "./components/StatisticsPanel";
import AlertCenter from "./components/AlertCenter";
import AIAgentX from "./components/AIAgent";
import AIAgentButton from "./components/AIAgentButton";
import Login from "./components/Login";
import Register from "./components/Register";
import UserCenter from "./components/UserCenter";
import History from "./components/History";

function AppContent() {
  const navigate = useNavigate();
  const location = useLocation();
  const [selectedTyphoons, setSelectedTyphoons] = useState(new Set());
  // 多台风叠加显示选项（默认为true）
  const [allowMultipleTyphoons, setAllowMultipleTyphoons] = useState(true);

  // 跟踪上一次的路径，用于检测是否从 history 页面跳转
  const prevLocationRef = useRef(location.pathname);

  // 当从 history 页面跳转到 visualization 页面且带有 typhoon_id 参数时，关闭多台风叠加显示
  useEffect(() => {
    const currentPath = location.pathname;
    const searchParams = new URLSearchParams(location.search);
    const hasTyphoonId = searchParams.has("typhoon_id");

    // 检测是否从 history 页面跳转到 visualization 页面
    if (
      prevLocationRef.current === "/history" &&
      currentPath === "/visualization" &&
      hasTyphoonId
    ) {
      console.log(
        "从 history 页面跳转到 visualization 页面，关闭多台风叠加显示",
      );
      // 如果地图上存在多个台风，先清空所有选中的台风
      if (selectedTyphoons.size > 1) {
        console.log("地图上存在多个台风，清空所有选中的台风");
        clearAllSelectedTyphoons();
      }
      setAllowMultipleTyphoons(false);
    }

    // 更新上一次的路径
    prevLocationRef.current = currentPath;
  }, [location, selectedTyphoons]);

  const isUserCenter =
    location.pathname === "/user-center" || location.pathname === "/history";
  const isAIAgent = location.pathname === "/AI_agent";
  const isAuthPage =
    location.pathname === "/login" || location.pathname === "/register";

  const getActiveTab = () => {
    const path = location.pathname;
    if (path === "/" || path === "/visualization") return "visualization";
    if (path === "/typhoon") return "typhoon";
    if (path === "/prediction") return "prediction";
    if (path === "/analysis") return "analysis";
    if (path === "/report") return "report";
    if (path === "/statistics") return "statistics";
    if (path === "/alert") return "alert";
    return "visualization";
  };

  const tabs = [
    {
      id: "visualization",
      label: "🗺️ 台风路径可视化",
      path: "/visualization",
    },
    { id: "typhoon", label: "🌊 台风数据查询", path: "/typhoon" },
    { id: "prediction", label: "🎯 智能预测", path: "/prediction" },
    { id: "analysis", label: "🖼️ 图像分析", path: "/analysis" },
    { id: "report", label: "📊 报告生成", path: "/report" },
    { id: "statistics", label: "📈 统计分析", path: "/statistics" },
    { id: "alert", label: "🚨 预警中心", path: "/alert" },
  ];

  const handleTyphoonSelect = (typhoonId) => {
    setSelectedTyphoons((prev) => {
      const newSet = new Set(prev);

      if (allowMultipleTyphoons) {
        // 多台风叠加模式：切换选中状态
        if (newSet.has(typhoonId)) {
          newSet.delete(typhoonId);
        } else {
          newSet.add(typhoonId);
        }
      } else {
        // 单台风模式：清除之前的选择，只保留当前选中的台风
        if (newSet.has(typhoonId)) {
          // 如果点击的是已选中的台风，则取消选中
          newSet.delete(typhoonId);
        } else {
          // 清除所有之前的选择，只选中当前台风
          newSet.clear();
          newSet.add(typhoonId);
        }
      }

      return newSet;
    });
  };

  // 清空所有选中的台风
  const clearAllSelectedTyphoons = () => {
    console.log("清空所有选中的台风");
    setSelectedTyphoons(new Set());
  };

  const handleTabChange = (tabId) => {
    const tab = tabs.find((t) => t.id === tabId);
    if (tab) {
      navigate(tab.path);
    }
  };

  return (
    <div className="container">
      {isUserCenter || isAIAgent ? (
        <Routes>
          <Route path="/user-center" element={<UserCenter />} />
          <Route path="/history" element={<History />} />
          <Route path="/AI_agent" element={<AIAgentX />} />
        </Routes>
      ) : isAuthPage ? (
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
        </Routes>
      ) : (
        <>
          <Header />

          <TabNavigation
            tabs={tabs}
            activeTab={getActiveTab()}
            onTabChange={handleTabChange}
          />

          <AlertBanner />

          <div className="content-card">
            <Routes>
              <Route
                path="/"
                element={
                  <MapVisualization
                    selectedTyphoons={selectedTyphoons}
                    onTyphoonSelect={handleTyphoonSelect}
                    allowMultipleTyphoons={allowMultipleTyphoons}
                    setAllowMultipleTyphoons={setAllowMultipleTyphoons}
                    clearAllSelectedTyphoons={clearAllSelectedTyphoons}
                  />
                }
              />
              <Route
                path="/visualization"
                element={
                  <MapVisualization
                    selectedTyphoons={selectedTyphoons}
                    onTyphoonSelect={handleTyphoonSelect}
                    allowMultipleTyphoons={allowMultipleTyphoons}
                    setAllowMultipleTyphoons={setAllowMultipleTyphoons}
                    clearAllSelectedTyphoons={clearAllSelectedTyphoons}
                  />
                }
              />
              <Route path="/typhoon" element={<TyphoonQuery />} />
              <Route path="/prediction" element={<Prediction />} />
              <Route path="/analysis" element={<ImageAnalysis />} />
              <Route path="/report" element={<ReportGeneration />} />
              <Route
                path="/statistics"
                element={
                  <StatisticsPanel
                    selectedTyphoons={selectedTyphoons}
                    onTyphoonSelect={handleTyphoonSelect}
                  />
                }
              />
              <Route path="/alert" element={<AlertCenter />} />
            </Routes>
          </div>

          <AIAgentButton />
        </>
      )}
    </div>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;
