/**
 * AI客服聊天界面组件 - 基于 Ant Design X 重构版本
 * 修复：流式回答期间持续自动滚动，完成后允许手动滚动
 * 优化：使用 useLayoutEffect 和 DOM 缓存提升滚动性能
 */
import {
  useState,
  useEffect,
  useLayoutEffect,
  useRef,
  useCallback,
  useMemo,
} from "react";
import { useNavigate } from "react-router-dom";
import { Bubble, Sender, Conversations, Welcome, Prompts } from "@ant-design/x";
import {
  Button,
  Spin,
  message,
  Typography,
  Space,
  Dropdown,
  Tooltip,
} from "antd";
import {
  ArrowLeftOutlined,
  PlusOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  RobotOutlined,
  UserOutlined,
  ThunderboltOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import {
  createAISession,
  getAISessions,
  getAISessionHistory,
  getAIQuestions,
  askAIQuestion,
  askAIQuestionStream,
} from "../services/api";
import "../styles/AIAgent.css";

const { Title, Text } = Typography;

/**
 * 欢迎界面子组件
 * 包含欢迎信息和热门问题提示
 */
const WelcomeSection = ({ questions, onQuestionClick }) => {
  const promptItems = useMemo(() => {
    return questions.map((q, index) => ({
      key: q.id || `q_${index}`,
      label: q.question,
      icon: <ThunderboltOutlined style={{ color: "#ff6b6b" }} />,
    }));
  }, [questions]);

  return (
    <div className="welcome-container" role="region" aria-label="欢迎界面">
      <Welcome
        icon={<RobotOutlined style={{ fontSize: 48, color: "#1677ff" }} />}
        title="您好，我是 AI 对话助手"
        description="我可以帮助您解答台风相关的问题，包括台风预测、历史数据分析、预警信息等。"
      />
      <div className="prompts-section">
        <Title level={5} style={{ marginBottom: 16, color: "#666" }}>
          <ThunderboltOutlined style={{ marginRight: 8, color: "#ff6b6b" }} />
          热门问题
        </Title>
        <Prompts
          items={promptItems}
          onItemClick={(info) => onQuestionClick(info.data.label)}
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
};

/**
 * 侧边栏子组件
 * 提供会话历史和导航功能
 */
const Sidebar = ({
  sessions,
  currentSessionId,
  onSessionClick,
  onNewChat,
  onBack,
  collapsed,
  onToggleCollapse,
}) => {
  const conversationItems = useMemo(() => {
    return sessions.map((session) => ({
      key: session.session_id,
      label:
        session.first_question.length > 30
          ? session.first_question.substring(0, 30) + "..."
          : session.first_question,
      timestamp: new Date(session.created_at).toLocaleDateString(),
    }));
  }, [sessions]);

  return (
    <aside
      className={`ai-agent-sidebar ${collapsed ? "collapsed" : ""}`}
      role="navigation"
      aria-label="会话历史"
    >
      {!collapsed && (
        <>
          <div className="sidebar-header">
            <div className="sidebar-header-buttons">
              <Tooltip title="返回首页">
                <Button
                  icon={<ArrowLeftOutlined />}
                  onClick={onBack}
                  className="icon-button"
                  aria-label="返回首页"
                />
              </Tooltip>
              <Tooltip title="新建对话">
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={onNewChat}
                  className="icon-button new-chat-button"
                  aria-label="新建对话"
                />
              </Tooltip>
              <Tooltip title="收起侧栏">
                <Button
                  icon={<MenuFoldOutlined />}
                  onClick={onToggleCollapse}
                  className="icon-button"
                  aria-label="收起侧栏"
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
              onActiveChange={onSessionClick}
            />
          </div>
        </>
      )}
      {collapsed && (
        <div className="sidebar-collapsed-buttons">
          <Tooltip title="展开侧栏" placement="right">
            <Button
              type="text"
              icon={<MenuUnfoldOutlined />}
              onClick={onToggleCollapse}
              size="large"
              aria-label="展开侧栏"
            />
          </Tooltip>
        </div>
      )}
    </aside>
  );
};

/**
 * 输入区域子组件
 * 提供消息输入和模型选择功能
 */
const InputArea = ({
  inputText,
  onInputChange,
  onSendMessage,
  sending,
  selectedModel,
  onModelChange,
  deepThinking,
  onDeepThinkingToggle,
}) => {
  const modelOptions = useMemo(
    () => [
      { value: "deepseek", label: "DeepSeek" },
      { value: "glm", label: "GLM (智谱清言)" },
      { value: "qwen", label: "Qwen (通义千问)" },
    ],
    [],
  );

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        onSendMessage();
      }
    },
    [onSendMessage],
  );

  return (
    <div className="ai-agent-input" role="form" aria-label="消息输入区域">
      <div className="input-wrapper">
        <Sender
          value={inputText}
          onChange={onInputChange}
          onSubmit={onSendMessage}
          placeholder="输入您的问题，按 Enter 发送..."
          loading={sending}
          style={{ width: "100%", maxWidth: 800 }}
          onKeyDown={handleKeyDown}
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
              onClick: ({ key }) => onModelChange(key),
              selectedKeys: [selectedModel],
            }}
            trigger={["click"]}
          >
            <Button
              className="pill-button model-select-button"
              aria-label="选择 AI 模型"
              aria-haspopup="true"
              aria-expanded="false"
            >
              {modelOptions.find((m) => m.value === selectedModel)?.label ||
                "选择模型"}
              <SettingOutlined style={{ marginLeft: 4 }} />
            </Button>
          </Dropdown>
          <Button
            className={`pill-button deep-thinking-button ${
              deepThinking ? "active" : ""
            }`}
            onClick={onDeepThinkingToggle}
            aria-label={`深度思考模式${deepThinking ? "已开启" : "已关闭"}`}
            aria-pressed={deepThinking}
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
  );
};

/**
 * 消息列表子组件 - 修复：将chatEndRef移入滚动容器内
 */
const MessageList = ({
  messages,
  bubbleListRef,
  streamingMessageKey,
  chatEndRef,
}) => {
  const formatTimestamp = useCallback((timestamp) => {
    if (!timestamp) return "";
    const date = new Date(timestamp);
    const beijingTime = new Date(date.getTime() + 8 * 60 * 60 * 1000);
    const year = beijingTime.getUTCFullYear();
    const month = String(beijingTime.getUTCMonth() + 1).padStart(2, "0");
    const day = String(beijingTime.getUTCDate()).padStart(2, "0");
    const hours = String(beijingTime.getUTCHours()).padStart(2, "0");
    const minutes = String(beijingTime.getUTCMinutes()).padStart(2, "0");
    const seconds = String(beijingTime.getUTCSeconds()).padStart(2, "0");
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  }, []);

  const bubbleItems = useMemo(() => {
    return messages.map((msg) => {
      const hasReasoning =
        msg.reasoningContent && msg.reasoningContent.trim().length > 0;
      const isStreaming = streamingMessageKey === msg.key;
      const showStreamingIndicator =
        isStreaming && (!msg.content || msg.content.length === 0);

      return {
        ...msg,
        placement: msg.role === "user" ? "end" : "start",
        avatar: msg.role === "user" ? <UserOutlined /> : <RobotOutlined />,
        variant: msg.role === "user" ? "filled" : "shadow",
        content: (
          <div className="message-with-time">
            {showStreamingIndicator && (
              <div className="streaming-indicator">
                <span className="dot"></span>
                <span className="dot"></span>
                <span className="dot"></span>
                <span style={{ marginLeft: 4 }}>AI 正在思考...</span>
              </div>
            )}
            {hasReasoning && (
              <div className="reasoning-content">
                <div className="reasoning-header">
                  <ThunderboltOutlined
                    style={{ marginRight: 4, color: "#ff6b6b" }}
                  />
                  <span className="reasoning-title">已深度思考</span>
                </div>
                <div className="reasoning-text">{msg.reasoningContent}</div>
              </div>
            )}
            <div className="message-content" style={{ whiteSpace: "pre-wrap" }}>
              {msg.content}
              {isStreaming && <span className="typing-cursor"></span>}
            </div>
            <div className="message-timestamp">
              {formatTimestamp(msg.timestamp)}
            </div>
          </div>
        ),
      };
    });
  }, [messages, formatTimestamp, streamingMessageKey]);

  return (
    <Bubble.List
      ref={bubbleListRef}
      items={bubbleItems}
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
    >
      {/* 关键修改：将chatEndRef移入Bubble.List内部（滚动容器内） */}
      <div ref={chatEndRef} />
    </Bubble.List>
  );
};

/**
 * AI客服聊天主组件 - 核心滚动逻辑修复
 */
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
  const [streamingMessageKey, setStreamingMessageKey] = useState(null);
  const [autoScroll, setAutoScroll] = useState(true);

  const bubbleListRef = useRef(null);
  const chatEndRef = useRef(null);
  const isUserScrollingRef = useRef(false);
  const scrollIntervalRef = useRef(null);
  const scrollRafRef = useRef(null);
  const lastScrollHeightRef = useRef(0);
  const isStreamingRef = useRef(false);
  const chatSectionRef = useRef(null);

  const SCROLL_THRESHOLD = 100;
  const SCROLL_DEBOUNCE_TIME = 150;
  const STREAMING_SCROLL_INTERVAL = 16;

  // 强制滚动到最新消息（立即执行，无动画）
  const scrollToBottomImmediate = useCallback(() => {
    if (!chatSectionRef.current) {
      chatSectionRef.current = document.querySelector(".ai-agent-chat");
    }

    if (chatSectionRef.current) {
      const { scrollHeight } = chatSectionRef.current;
      const currentScrollTop = chatSectionRef.current.scrollTop;

      if (scrollHeight !== lastScrollHeightRef.current) {
        chatSectionRef.current.scrollTop = scrollHeight;
        lastScrollHeightRef.current = scrollHeight;
      }
    }
  }, []);

  // 自动滚动到最新消息（平滑滚动）
  const scrollToBottom = useCallback(
    (force = false) => {
      if (chatEndRef.current && (autoScroll || force)) {
        chatEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
      }
    },
    [autoScroll],
  );

  // 用户滚动检测逻辑 - 流式加载期间完全屏蔽
  useEffect(() => {
    if (!chatSectionRef.current) {
      chatSectionRef.current = document.querySelector(".ai-agent-chat");
    }
    const chatSection = chatSectionRef.current;
    if (!chatSection) return;

    let scrollTimeout;
    let lastScrollTop = chatSection.scrollTop;
    let lastScrollTime = Date.now();

    const handleScroll = () => {
      const now = Date.now();
      const currentScrollTop = chatSection.scrollTop;

      if (isStreamingRef.current || sending) {
        return;
      }

      if (isUserScrollingRef.current) return;

      const timeDiff = now - lastScrollTime;
      const scrollDiff = Math.abs(currentScrollTop - lastScrollTop);

      if (timeDiff > SCROLL_DEBOUNCE_TIME && scrollDiff > 5) {
        isUserScrollingRef.current = true;
        clearTimeout(scrollTimeout);

        const { scrollTop, scrollHeight, clientHeight } = chatSection;
        const isAtBottom =
          scrollHeight - scrollTop - clientHeight < SCROLL_THRESHOLD;

        if (isAtBottom) {
          setAutoScroll(true);
        } else {
          setAutoScroll(false);
        }

        scrollTimeout = setTimeout(() => {
          isUserScrollingRef.current = false;
        }, SCROLL_DEBOUNCE_TIME);

        lastScrollTop = currentScrollTop;
        lastScrollTime = now;
      }
    };

    chatSection.addEventListener("scroll", handleScroll, { passive: true });
    return () => {
      chatSection.removeEventListener("scroll", handleScroll);
      clearTimeout(scrollTimeout);
    };
  }, [sending]);

  // 流式加载期间的滚动定时器 - 严谨启停
  useEffect(() => {
    const isInStreaming = sending || !!streamingMessageKey;
    isStreamingRef.current = isInStreaming;

    if (isInStreaming) {
      setAutoScroll(true);

      const scrollLoop = () => {
        if (!isStreamingRef.current) return;

        if (!chatSectionRef.current) {
          chatSectionRef.current = document.querySelector(".ai-agent-chat");
        }

        if (chatSectionRef.current) {
          const { scrollHeight } = chatSectionRef.current;
          if (scrollHeight !== lastScrollHeightRef.current) {
            chatSectionRef.current.scrollTop = scrollHeight;
            lastScrollHeightRef.current = scrollHeight;
          }
        }

        scrollRafRef.current = requestAnimationFrame(scrollLoop);
      };

      scrollRafRef.current = requestAnimationFrame(scrollLoop);
    } else {
      if (scrollRafRef.current) {
        cancelAnimationFrame(scrollRafRef.current);
        scrollRafRef.current = null;
      }

      if (scrollIntervalRef.current) {
        clearInterval(scrollIntervalRef.current);
        scrollIntervalRef.current = null;
      }

      scrollToBottomImmediate();
    }

    return () => {
      if (scrollRafRef.current) {
        cancelAnimationFrame(scrollRafRef.current);
        scrollRafRef.current = null;
      }

      if (scrollIntervalRef.current) {
        clearInterval(scrollIntervalRef.current);
        scrollIntervalRef.current = null;
      }
    };
  }, [sending, streamingMessageKey, scrollToBottomImmediate]);

  // 消息更新时的滚动逻辑 - 使用 useLayoutEffect 确保在 DOM 更新后、浏览器绘制前立即执行
  useLayoutEffect(() => {
    // 流式加载中：立即强制滚动
    if (isStreamingRef.current) {
      scrollToBottomImmediate();
    } else if (autoScroll) {
      // 非流式加载且开启自动滚动：平滑滚动
      scrollToBottom();
    }
  }, [messages, autoScroll, scrollToBottom, scrollToBottomImmediate]);

  // 【以下逻辑无修改：initializeChat、loadSessions、handleQuestionClick等】
  const initializeChat = useCallback(async () => {
    try {
      setLoading(true);

      const token = localStorage.getItem("token");
      if (!token) {
        message.error("请先登录后再使用 AI 对话助手");
        navigate("/login");
        return;
      }

      const sessionData = await createAISession();
      setCurrentSessionId(sessionData.session_id);

      const questionsData = await getAIQuestions();
      setQuestions(questionsData);

      setMessages([]);
    } catch (error) {
      console.error("初始化失败:", error);

      if (
        error.message.includes("Not authenticated") ||
        error.message.includes("401") ||
        error.message.includes("Unauthorized")
      ) {
        message.error("登录已过期，请重新登录");
        localStorage.removeItem("token");
        navigate("/login");
      } else {
        message.error("初始化失败，请刷新页面重试");
      }
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  const loadSessions = useCallback(async () => {
    try {
      const data = await getAISessions();
      setSessions(data);
    } catch (error) {
      console.error("加载会话列表失败:", error);

      if (
        error.message.includes("Not authenticated") ||
        error.message.includes("401") ||
        error.message.includes("Unauthorized")
      ) {
        localStorage.removeItem("token");
        navigate("/login");
      }
    }
  }, [navigate]);

  useEffect(() => {
    initializeChat();
    loadSessions();
  }, [initializeChat, loadSessions]);

  const handleQuestionClick = useCallback(
    async (questionText) => {
      if (!questionText.trim() || sending) return;

      const token = localStorage.getItem("token");
      if (!token) {
        message.error("请先登录后再使用 AI 对话助手");
        navigate("/login");
        return;
      }

      // 用户发起提问时，强制开启 autoScroll，忽略之前手动向上滚动导致的 autoScroll=false 状态
      setAutoScroll(true);
      setSending(true);
      const userMessage = {
        key: `user_${Date.now()}`,
        role: "user",
        content: questionText,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setInputText("");

      // 用户发送消息后，立即调用 scrollToBottomImmediate()，移除延迟逻辑
      scrollToBottomImmediate();

      const aiMessageKey = `ai_${Date.now()}`;
      const aiMessage = {
        key: aiMessageKey,
        role: "ai",
        content: "",
        reasoningContent: "",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, aiMessage]);
      setStreamingMessageKey(aiMessageKey);

      try {
        console.log("📤 开始发送问题到后端（流式传输）...", {
          sessionId: currentSessionId,
          question: questionText,
          model: selectedModel,
          deepThinking: deepThinking,
        });

        await askAIQuestionStream(
          currentSessionId,
          questionText,
          selectedModel,
          deepThinking,
          (data) => {
            console.log("📥 收到流式数据块:", data);

            if (data.type === "reasoning_content") {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.key === aiMessageKey
                    ? {
                        ...msg,
                        reasoningContent:
                          (msg.reasoningContent || "") + data.content,
                      }
                    : msg,
                ),
              );
            } else if (data.type === "content") {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.key === aiMessageKey
                    ? { ...msg, content: (msg.content || "") + data.content }
                    : msg,
                ),
              );
            } else if (data.type === "error") {
              console.error("❌ 流式传输错误:", data.message);
              message.error(data.message);
            }
          },
          () => {
            console.log("✅ 流式传输完成");
            setMessages((prev) =>
              prev.map((msg) =>
                msg.key === aiMessageKey
                  ? { ...msg, timestamp: new Date().toISOString() }
                  : msg,
              ),
            );
            setStreamingMessageKey(null);
            loadSessions();
          },
          (error) => {
            console.error("❌ 流式传输失败:", error);
            message.error(`发送消息失败：${error.message}`);
            setStreamingMessageKey(null);
            setAutoScroll(true);
          },
        );

        console.log("✅ 消息发送成功");
      } catch (error) {
        console.error("❌ 发送消息失败:", error);
        console.error("❌ 错误详情:", {
          message: error.message,
          stack: error.stack,
          name: error.name,
        });

        if (
          error.message.includes("Not authenticated") ||
          error.message.includes("401") ||
          error.message.includes("Unauthorized")
        ) {
          message.error("登录已过期，请重新登录");
          localStorage.removeItem("token");
          navigate("/login");
        } else if (
          error.message.includes("timeout") ||
          error.message.includes("超时")
        ) {
          message.error(
            `请求超时：${
              deepThinking ? "深度思考模式" : "AI 服务"
            }响应时间过长，请稍后重试`,
          );
        } else if (error.message.includes("数据格式错误")) {
          message.error("AI 回答格式异常，请重试或联系管理员");
        } else {
          message.error(`发送消息失败：${error.message}`);
        }

        setMessages((prev) => prev.filter((msg) => msg.key !== aiMessageKey));
      } finally {
        setSending(false);
      }
    },
    [
      currentSessionId,
      selectedModel,
      deepThinking,
      sending,
      loadSessions,
      navigate,
      scrollToBottomImmediate,
    ],
  );

  const handleSendMessage = useCallback(async () => {
    await handleQuestionClick(inputText);
  }, [inputText, handleQuestionClick]);

  const handleNewChat = useCallback(async () => {
    try {
      const token = localStorage.getItem("token");
      if (!token) {
        message.error("请先登录后再使用 AI 对话助手");
        navigate("/login");
        return;
      }

      const data = await createAISession();
      setCurrentSessionId(data.session_id);

      const questionsData = await getAIQuestions();
      setQuestions(questionsData);
      setMessages([]);

      loadSessions();
    } catch (error) {
      console.error("创建新对话失败:", error);

      if (
        error.message.includes("Not authenticated") ||
        error.message.includes("401") ||
        error.message.includes("Unauthorized")
      ) {
        message.error("登录已过期，请重新登录");
        localStorage.removeItem("token");
        navigate("/login");
      } else {
        message.error("创建新对话失败");
      }
    }
  }, [loadSessions, navigate]);

  const handleSessionClick = useCallback(
    async (sessionId) => {
      try {
        const token = localStorage.getItem("token");
        if (!token) {
          message.error("请先登录后再使用 AI 对话助手");
          navigate("/login");
          return;
        }

        setLoading(true);
        setCurrentSessionId(sessionId);

        const data = await getAISessionHistory(sessionId);

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
            reasoningContent: item.reasoning_content || "",
            timestamp: item.created_at,
          });
        });

        setMessages(historyMessages);
      } catch (error) {
        console.error("加载会话历史失败:", error);

        if (
          error.message.includes("Not authenticated") ||
          error.message.includes("401") ||
          error.message.includes("Unauthorized")
        ) {
          message.error("登录已过期，请重新登录");
          localStorage.removeItem("token");
          navigate("/login");
        } else {
          message.error("加载会话历史失败");
        }
      } finally {
        setLoading(false);
      }
    },
    [navigate],
  );

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => !prev);
  }, []);

  const handleBack = useCallback(() => {
    navigate("/");
  }, [navigate]);

  const handleInputChange = useCallback((value) => {
    setInputText(value);
  }, []);

  const handleModelChange = useCallback((model) => {
    setSelectedModel(model);
  }, []);

  const handleDeepThinkingToggle = useCallback(() => {
    setDeepThinking((prev) => !prev);
  }, []);

  return (
    <div className="ai-agent-container" role="main" aria-label="AI 对话助手">
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSessionClick={handleSessionClick}
        onNewChat={handleNewChat}
        onBack={handleBack}
        collapsed={sidebarCollapsed}
        onToggleCollapse={toggleSidebar}
      />

      <main className="ai-agent-main" role="main">
        <header className="ai-agent-header">
          <div className="header-title">
            <RobotOutlined style={{ fontSize: 24, marginRight: 8 }} />
            <Title level={4} style={{ margin: 0 }}>
              AI 对话助手
            </Title>
          </div>
        </header>

        <section
          className="ai-agent-chat"
          role="log"
          aria-live="polite"
          aria-atomic="false"
        >
          {loading ? (
            <div className="loading-container">
              <Spin size="large" />
              <Text type="secondary" style={{ marginTop: 16 }}>
                正在加载...
              </Text>
            </div>
          ) : messages.length === 0 ? (
            <WelcomeSection
              questions={questions}
              onQuestionClick={handleQuestionClick}
            />
          ) : (
            <MessageList
              messages={messages}
              bubbleListRef={bubbleListRef}
              streamingMessageKey={streamingMessageKey}
              chatEndRef={chatEndRef} // 传递chatEndRef到子组件
            />
          )}
        </section>

        <InputArea
          inputText={inputText}
          onInputChange={handleInputChange}
          onSendMessage={handleSendMessage}
          sending={sending}
          selectedModel={selectedModel}
          onModelChange={handleModelChange}
          deepThinking={deepThinking}
          onDeepThinkingToggle={handleDeepThinkingToggle}
        />
      </main>
    </div>
  );
}

export default AIAgent;
