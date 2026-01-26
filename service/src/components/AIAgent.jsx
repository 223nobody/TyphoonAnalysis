/**
 * AI客服聊天界面组件 - 基于 Ant Design X 重构版本
 * 使用 4 空格缩进，符合项目规范
 */
import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Bubble, Sender, Conversations, Welcome, Prompts } from "@ant-design/x";
import {
  Button,
  Spin,
  message,
  Typography,
  Space,
  Tooltip,
  Dropdown,
} from "antd";
import {
  ArrowLeftOutlined,
  PlusOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  RobotOutlined,
  UserOutlined,
  FireOutlined,
  ThunderboltOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import {
  createAISession,
  getAISessions,
  getAISessionHistory,
  getAIQuestions,
  askAIQuestion,
} from "../services/api";
import "../styles/AIAgent.css";

const { Title, Text } = Typography;

function AIAgent() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [inputText, setInputText] = useState("");
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [selectedModel, setSelectedModel] = useState("deepseek");
  const [sending, setSending] = useState(false);
  const [deepThinking, setDeepThinking] = useState(false);
  const bubbleListRef = useRef(null);

  // 模型选项
  const modelOptions = [
    { value: "deepseek", label: "DeepSeek" },
    { value: "glm", label: "GLM (智谱清言)" },
    { value: "qwen", label: "Qwen (通义千问)" },
  ];

  // 初始化：创建新会话并加载热门问题
  useEffect(() => {
    initializeChat();
    loadSessions();
  }, []);

  // 初始化聊天
  const initializeChat = async () => {
    try {
      setLoading(true);
      // 创建新会话
      const sessionData = await createAISession();
      setCurrentSessionId(sessionData.session_id);

      // 加载热门问题
      const questionsData = await getAIQuestions();
      setQuestions(questionsData);

      // 设置为空消息，显示欢迎界面
      setMessages([]);
    } catch (error) {
      console.error("初始化失败:", error);
      message.error("初始化失败，请刷新页面重试");
    } finally {
      setLoading(false);
    }
  };

  // 加载会话列表
  const loadSessions = async () => {
    try {
      const data = await getAISessions();
      setSessions(data);
    } catch (error) {
      console.error("加载会话列表失败:", error);
    }
  };

  // 处理问题点击
  const handleQuestionClick = async (questionText) => {
    await sendMessage(questionText);
  };

  // 发送消息
  const sendMessage = async (content) => {
    if (!content.trim() || sending) return;

    setSending(true);
    const userMessage = {
      key: `user_${Date.now()}`,
      role: "user",
      content: content,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInputText("");

    try {
      console.log("📤 开始发送问题到后端...", {
        sessionId: currentSessionId,
        question: content,
        model: selectedModel,
        deepThinking: deepThinking,
      });

      const data = await askAIQuestion(
        currentSessionId,
        content,
        selectedModel,
        deepThinking
      );

      console.log("📥 收到后端响应:", data);

      // 验证响应数据格式
      if (!data || typeof data.answer !== "string") {
        console.error("❌ 后端返回数据格式错误:", data);
        throw new Error("后端返回数据格式错误");
      }

      const botMessage = {
        key: `ai_${Date.now()}`,
        role: "ai",
        content: data.answer,
        timestamp: new Date().toISOString(),
      };

      console.log("✅ 准备添加 AI 消息到界面:", botMessage);
      setMessages((prev) => [...prev, botMessage]);

      // 刷新会话列表
      loadSessions();

      console.log("✅ 消息发送成功");
    } catch (error) {
      console.error("❌ 发送消息失败:", error);
      console.error("❌ 错误详情:", {
        message: error.message,
        stack: error.stack,
        name: error.name,
      });

      // 根据错误类型显示不同的提示
      if (error.message.includes("timeout") || error.message.includes("超时")) {
        message.error(
          `请求超时：${
            deepThinking ? "深度思考模式" : "AI 服务"
          }响应时间过长，请稍后重试`
        );
      } else if (error.message.includes("数据格式错误")) {
        message.error("AI 回答格式异常，请重试或联系管理员");
      } else {
        message.error(`发送消息失败：${error.message}`);
      }
    } finally {
      setSending(false);
    }
  };

  // 处理发送消息
  const handleSendMessage = async () => {
    await sendMessage(inputText);
  };

  // 创建新对话
  const handleNewChat = async () => {
    try {
      const data = await createAISession();
      setCurrentSessionId(data.session_id);

      // 重新加载欢迎消息
      const questionsData = await getAIQuestions();
      setQuestions(questionsData);
      setMessages([]);

      // 刷新会话列表
      loadSessions();
    } catch (error) {
      console.error("创建新对话失败:", error);
      message.error("创建新对话失败");
    }
  };

  // 切换到历史会话
  const handleSessionClick = async (sessionId) => {
    try {
      setLoading(true);
      setCurrentSessionId(sessionId);

      // 加载该会话的历史记录
      const data = await getAISessionHistory(sessionId);

      // 转换为消息格式
      const historyMessages = [];
      data.forEach((item, index) => {
        historyMessages.push({
          key: `user_${index}`,
          role: "user",
          content: item.question,
          timestamp: item.created_at,
        });
        historyMessages.push({
          key: `ai_${index}`,
          role: "ai",
          content: item.answer,
          timestamp: item.created_at,
        });
      });

      setMessages(historyMessages);
    } catch (error) {
      console.error("加载会话历史失败:", error);
      message.error("加载会话历史失败");
    } finally {
      setLoading(false);
    }
  };

  // 切换侧栏折叠状态
  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  // 返回首页
  const handleBack = () => {
    navigate("/");
  };

  // 转换会话列表为 Conversations 组件所需格式
  const conversationItems = sessions.map((session) => ({
    key: session.session_id,
    label:
      session.first_question.length > 30
        ? session.first_question.substring(0, 30) + "..."
        : session.first_question,
    timestamp: new Date(session.created_at).toLocaleDateString(),
  }));

  // 转换热门问题为 Prompts 组件所需格式
  const promptItems = questions.map((q, index) => ({
    key: q.id || `q_${index}`,
    label: q.question,
    icon: <FireOutlined style={{ color: "#ff6b6b" }} />,
  }));

  // 格式化时间为北京时间
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return "";
    const date = new Date(timestamp);
    // 转换为北京时间（UTC+8）
    const beijingTime = new Date(date.getTime() + 8 * 60 * 60 * 1000);
    const year = beijingTime.getUTCFullYear();
    const month = String(beijingTime.getUTCMonth() + 1).padStart(2, "0");
    const day = String(beijingTime.getUTCDate()).padStart(2, "0");
    const hours = String(beijingTime.getUTCHours()).padStart(2, "0");
    const minutes = String(beijingTime.getUTCMinutes()).padStart(2, "0");
    const seconds = String(beijingTime.getUTCSeconds()).padStart(2, "0");
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  };

  // 转换消息为 Bubble.List 所需格式
  const bubbleItems = messages.map((msg) => ({
    ...msg,
    placement: msg.role === "user" ? "end" : "start",
    avatar: msg.role === "user" ? <UserOutlined /> : <RobotOutlined />,
    variant: msg.role === "user" ? "filled" : "shadow",
    content: (
      <div className="message-with-time">
        <div className="message-content" style={{ whiteSpace: "pre-wrap" }}>
          {msg.content}
        </div>
        <div className="message-timestamp">
          {formatTimestamp(msg.timestamp)}
        </div>
      </div>
    ),
  }));

  // 渲染欢迎界面
  const renderWelcome = () => (
    <div className="welcome-container">
      <Welcome
        icon={<RobotOutlined style={{ fontSize: 48, color: "#1677ff" }} />}
        title="您好，我是 AI 对话助手"
        description="我可以帮助您解答台风相关的问题，包括台风预测、历史数据分析、预警信息等。"
      />
      <div className="prompts-section">
        <Title level={5} style={{ marginBottom: 16, color: "#666" }}>
          <FireOutlined style={{ marginRight: 8, color: "#ff6b6b" }} />
          热门问题
        </Title>
        <Prompts
          items={promptItems}
          onItemClick={(info) => handleQuestionClick(info.data.label)}
          wrap
          styles={{
            list: {
              maxWidth: 800,
              justifyContent: "center",
            },
            item: {
              flex: "0 0 auto",
            },
          }}
        />
      </div>
    </div>
  );

  return (
    <div className="ai-agent-container">
      {/* 左侧会话列表 */}
      <div
        className={`ai-agent-sidebar ${sidebarCollapsed ? "collapsed" : ""}`}
      >
        {!sidebarCollapsed && (
          <>
            <div className="sidebar-header">
              <div className="sidebar-header-buttons">
                <Tooltip title="返回首页">
                  <Button
                    icon={<ArrowLeftOutlined />}
                    onClick={handleBack}
                    className="icon-button"
                  />
                </Tooltip>
                <Tooltip title="新建对话">
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={handleNewChat}
                    className="icon-button new-chat-button"
                  />
                </Tooltip>
                <Tooltip title="收起侧栏">
                  <Button
                    icon={<MenuFoldOutlined />}
                    onClick={toggleSidebar}
                    className="icon-button"
                  />
                </Tooltip>
              </div>
            </div>
            <div className="sidebar-content">
              <Text
                type="secondary"
                style={{ padding: "8px 16px", display: "block" }}
              >
                历史对话
              </Text>
              <Conversations
                items={conversationItems}
                activeKey={currentSessionId}
                onActiveChange={handleSessionClick}
              />
            </div>
          </>
        )}
        {sidebarCollapsed && (
          <div className="sidebar-collapsed-buttons">
            <Tooltip title="展开侧栏" placement="right">
              <Button
                type="text"
                icon={<MenuUnfoldOutlined />}
                onClick={toggleSidebar}
                size="large"
              />
            </Tooltip>
          </div>
        )}
      </div>

      {/* 主聊天区域 */}
      <div className="ai-agent-main">
        {/* 头部 */}
        <div className="ai-agent-header">
          <div className="header-title">
            <RobotOutlined style={{ fontSize: 24, marginRight: 8 }} />
            <Title level={4} style={{ margin: 0 }}>
              AI 对话助手
            </Title>
          </div>
        </div>

        {/* 消息列表 */}
        <div className="ai-agent-chat">
          {loading ? (
            <div className="loading-container">
              <Spin size="large" />
              <Text type="secondary" style={{ marginTop: 16 }}>
                正在加载...
              </Text>
            </div>
          ) : messages.length === 0 ? (
            renderWelcome()
          ) : (
            <Bubble.List
              ref={bubbleListRef}
              items={bubbleItems}
              autoScroll
              style={{ height: "100%", padding: "0 24px" }}
              roles={{
                ai: {
                  placement: "start",
                  avatar: <RobotOutlined />,
                  variant: "shadow",
                  shape: "round",
                },
                user: {
                  placement: "end",
                  avatar: <UserOutlined />,
                  variant: "filled",
                  shape: "round",
                },
              }}
            />
          )}
        </div>

        {/* 输入框区域 */}
        <div className="ai-agent-input">
          <div className="input-wrapper">
            <Sender
              value={inputText}
              onChange={setInputText}
              onSubmit={handleSendMessage}
              placeholder="输入您的问题，按 Enter 发送..."
              loading={sending}
              style={{ width: "100%", maxWidth: 800 }}
            />
          </div>
          <div className="input-controls">
            <Space size="middle">
              <Dropdown
                menu={{
                  items: [
                    { key: "deepseek", label: "DeepSeek" },
                    { key: "glm", label: "GLM (智谱清言)" },
                    { key: "qwen", label: "Qwen (通义千问)" },
                  ],
                  onClick: ({ key }) => setSelectedModel(key),
                  selectedKeys: [selectedModel],
                }}
                trigger={["click"]}
              >
                <Button className="pill-button model-select-button">
                  {modelOptions.find((m) => m.value === selectedModel)?.label ||
                    "选择模型"}
                  <SettingOutlined style={{ marginLeft: 4 }} />
                </Button>
              </Dropdown>
              <Button
                className={`pill-button deep-thinking-button ${
                  deepThinking ? "active" : ""
                }`}
                onClick={() => setDeepThinking(!deepThinking)}
              >
                <ThunderboltOutlined style={{ marginRight: 4 }} />
                深度思考
              </Button>
            </Space>
            <Text type="secondary" className="input-hint">
              AI 可能会产生错误信息，请注意核实重要内容
            </Text>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AIAgent;
