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
  Modal,
  Input,
  Avatar,
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
  AudioOutlined,
  AudioMutedOutlined,
  MoreOutlined,
  EditOutlined,
  DeleteOutlined,
  LogoutOutlined,
  NodeIndexOutlined,
} from "@ant-design/icons";
import {
  createAISession,
  getAISessions,
  getAISessionHistory,
  getAIQuestions,
  askAIQuestion,
  askAIQuestionStream,
  transcribeAudio,
  deleteAISession,
  renameAISession,
  searchKnowledgeGraph,
  graphRAGLocalSearch,
} from "../services/api";
import KnowledgeGraphPanel from "./KnowledgeGraphPanel";
import "../styles/AIAgent.css";

const { Title, Text } = Typography;

/**
 * 欢迎界面子组件
 * 包含欢迎信息和热门问题提示
 */
const WelcomeSection = ({ questions, onQuestionClick, username }) => {
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
        title={`Hi ${username}，我是你的 AI 对话助手`}
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
 * 会话项组件 - 支持悬浮菜单和右键菜单
 */
const ConversationItem = ({
  session,
  isActive,
  onClick,
  onDelete,
  onRename,
}) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const [showMenuButton, setShowMenuButton] = useState(false);

  const label = useMemo(() => {
    return session.first_question.length > 30
      ? session.first_question.substring(0, 30) + "..."
      : session.first_question;
  }, [session.first_question]);

  // 处理删除 - 带确认提示
  const handleDelete = useCallback(() => {
    Modal.confirm({
      title: (
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "8px",
              background: "linear-gradient(135deg, #EF4444 0%, #F87171 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 4px 12px rgba(239, 68, 68, 0.3)",
            }}
          >
            <DeleteOutlined style={{ color: "#fff", fontSize: "16px" }} />
          </div>
          <span style={{ fontSize: "16px", fontWeight: "600" }}>删除对话</span>
        </div>
      ),
      content: (
        <div style={{ padding: "8px 0" }}>
          <p
            style={{
              fontSize: "14px",
              color: "#64748B",
              margin: "0 0 12px 0",
              lineHeight: "1.6",
            }}
          >
            确定要删除对话
          </p>
          <p
            style={{
              fontSize: "14px",
              color: "#1E293B",
              fontWeight: "500",
              margin: "0",
              padding: "10px 14px",
              background: "rgba(99, 102, 241, 0.06)",
              borderRadius: "8px",
              border: "1px solid rgba(99, 102, 241, 0.1)",
            }}
          >
            "{label}"
          </p>
          <p
            style={{ fontSize: "13px", color: "#94A3B8", margin: "12px 0 0 0" }}
          >
            ⚠️ 此操作不可恢复，请谨慎操作
          </p>
        </div>
      ),
      okText: "确认删除",
      okType: "danger",
      cancelText: "取消",
      okButtonProps: {
        danger: true,
        type: "primary",
        style: {
          background: "linear-gradient(135deg, #EF4444 0%, #F87171 100%)",
          border: "none",
          boxShadow: "0 4px 12px rgba(239, 68, 68, 0.3)",
        },
      },
      cancelButtonProps: {
        style: {
          borderRadius: "10px",
          height: "38px",
        },
      },
      centered: true,
      width: 520,
      onOk: () => {
        onDelete(session.session_id);
      },
    });
    setMenuOpen(false);
  }, [session.session_id, label, onDelete]);

  // 处理重命名
  const handleRename = useCallback(() => {
    onRename(session.session_id, session.first_question);
    setMenuOpen(false);
  }, [session.session_id, session.first_question, onRename]);

  // 处理右键菜单
  const handleContextMenu = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setMenuOpen(true);
  }, []);

  // 菜单配置
  const menuProps = {
    items: [
      {
        key: "rename",
        icon: <EditOutlined />,
        label: "重命名",
      },
      {
        key: "delete",
        icon: <DeleteOutlined />,
        label: "删除",
        danger: true,
      },
    ],
    onClick: ({ key }) => {
      if (key === "rename") {
        handleRename();
      } else if (key === "delete") {
        handleDelete();
      }
    },
  };

  // 处理鼠标离开整个会话项区域
  const handleMouseLeave = useCallback(
    (e) => {
      // 检查鼠标是否移动到了下拉菜单上
      const relatedTarget = e.relatedTarget;
      const dropdownElement = e.currentTarget.querySelector(".ant-dropdown");

      // 如果菜单是打开的，不隐藏按钮
      if (menuOpen) {
        return;
      }

      setShowMenuButton(false);
    },
    [menuOpen],
  );

  return (
    <div
      className={`conversation-item ${isActive ? "active" : ""}`}
      onClick={() => onClick(session.session_id)}
      onMouseEnter={() => setShowMenuButton(true)}
      onMouseLeave={handleMouseLeave}
      onContextMenu={handleContextMenu}
      role="button"
      tabIndex={0}
      aria-label={`对话: ${label}`}
      aria-current={isActive ? "true" : undefined}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          onClick(session.session_id);
        }
      }}
    >
      <div className="conversation-item-content">
        <span className="conversation-item-label" title={label}>
          {label}
        </span>
        <span className="conversation-item-time">
          {new Date(session.created_at).toLocaleDateString()}
        </span>
      </div>
      <Dropdown
        menu={menuProps}
        placement="bottomRight"
        trigger={["click"]}
        open={menuOpen}
        onOpenChange={setMenuOpen}
        getPopupContainer={() => document.body}
        autoAdjustOverflow={{ adjustX: 1, adjustY: 1 }}
      >
        <Button
          type="text"
          size="small"
          icon={<MoreOutlined rotate={90} />}
          className={`conversation-item-menu ${
            showMenuButton || isActive || menuOpen ? "visible" : ""
          }`}
          onClick={(e) => e.stopPropagation()}
          aria-label="更多操作"
        />
      </Dropdown>
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
  onDeleteSession,
  onRenameSession,
}) => {
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
            <div className="conversations-list">
              {sessions.map((session) => (
                <ConversationItem
                  key={session.session_id}
                  session={session}
                  isActive={session.session_id === currentSessionId}
                  onClick={onSessionClick}
                  onDelete={onDeleteSession}
                  onRename={onRenameSession}
                />
              ))}
            </div>
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
 * 提供消息输入、语音输入和模型选择功能
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
  // 语音输入相关 props
  isRecording,
  recordingTime,
  isTranscribing,
  onStartRecording,
  onStopRecording,
}) => {
  const modelOptions = useMemo(
    () => [
      { value: "deepseek", label: "DeepSeek" },
      { value: "glm", label: "GLM (智谱清言)" },
      { value: "qwen", label: "Qwen (通义千问)" },
    ],
    [],
  );

  // 格式化录音时间显示 (MM:SS)
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="ai-agent-input" role="form" aria-label="消息输入区域">
      <div className="input-wrapper">
        <Sender
          value={inputText}
          onChange={onInputChange}
          onSubmit={onSendMessage}
          placeholder={
            isRecording
              ? `正在录音... ${formatTime(recordingTime)}`
              : isTranscribing
                ? "正在识别语音..."
                : "输入您的问题，按 Enter 发送..."
          }
          loading={sending || isTranscribing}
          style={{ width: "100%", maxWidth: 800 }}
          prefix={
            <Tooltip
              title={
                isRecording
                  ? "点击停止录音"
                  : isTranscribing
                    ? "正在识别中..."
                    : "点击开始语音输入"
              }
            >
              <Button
                type={isRecording ? "primary" : "text"}
                danger={isRecording}
                icon={isRecording ? <AudioMutedOutlined /> : <AudioOutlined />}
                onClick={isRecording ? onStopRecording : onStartRecording}
                loading={isTranscribing}
                className={`voice-input-button ${isRecording ? "recording" : ""}`}
                aria-label={isRecording ? "停止录音" : "开始语音输入"}
              >
                {isRecording && (
                  <span className="recording-time">
                    {formatTime(recordingTime)}
                  </span>
                )}
              </Button>
            </Tooltip>
          }
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
          {isRecording
            ? "正在录音，点击麦克风图标停止"
            : isTranscribing
              ? "正在将语音转换为文字..."
              : "AI 可能会产生错误信息，请注意核实重要内容"}
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
  userAvatar,
  onAvatarClick,
  onViewGraphVisualization,
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
      // 只有在深度思考模式下才显示推理内容
      const hasReasoning =
        msg.deepThinking &&
        msg.reasoningContent &&
        msg.reasoningContent.trim().length > 0;
      const isStreaming = streamingMessageKey === msg.key;
      const showStreamingIndicator =
        isStreaming && (!msg.content || msg.content.length === 0);

      // 从 msg 中解构出需要传递的属性，排除 reasoningContent 和 deepThinking
      const { reasoningContent, deepThinking, ...msgProps } = msg;

      return {
        ...msgProps,
        placement: msg.role === "user" ? "end" : "start",
        avatar:
          msg.role === "user" ? (
            userAvatar ? (
              <img
                src={userAvatar}
                alt="用户头像"
                onClick={onAvatarClick}
                className="user-avatar-img"
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: "50%",
                  objectFit: "cover",
                  cursor: "pointer",
                }}
              />
            ) : (
              <UserOutlined />
            )
          ) : (
            <RobotOutlined />
          ),
        variant: msg.role === "user" ? "filled" : "shadow",
        content: (
          <div className="message-with-time">
            {/* GraphRAG 液态玻璃风格按钮 - 在AI消息上方 */}
            {/* 判断条件：历史记录使用 hasGraphVisualization，流式消息使用 graphData */}
            {msg.role === "ai" &&
              (msg.hasGraphVisualization || msg.graphData) && (
                <div className="graph-rag-glass-btn-wrapper">
                  <button
                    className="graph-rag-glass-btn"
                    onClick={() =>
                      onViewGraphVisualization && onViewGraphVisualization(msg)
                    }
                    title="点击切换知识图谱可视化"
                  >
                    <span className="graph-rag-icon">
                      <NodeIndexOutlined />
                    </span>
                    <span className="graph-rag-text">GraphRAG</span>
                    <span className="graph-rag-shine"></span>
                  </button>
                </div>
              )}
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
  }, [
    messages,
    formatTimestamp,
    streamingMessageKey,
    onViewGraphVisualization,
  ]);

  return (
    <>
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
            avatar: userAvatar ? (
              <img
                src={userAvatar}
                alt="用户头像"
                onClick={onAvatarClick}
                className="user-avatar-img"
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: "50%",
                  objectFit: "cover",
                  cursor: "pointer",
                }}
              />
            ) : (
              <UserOutlined />
            ),
            variant: "filled",
            shape: "round",
          },
        }}
      />
      {/* 将chatEndRef放在Bubble.List外部，用于自动滚动 */}
      <div ref={chatEndRef} style={{ height: 0 }} />
    </>
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
  const [userAvatar, setUserAvatar] = useState(null);
  const [username, setUsername] = useState("223");

  // 重命名对话框状态
  const [renameModal, setRenameModal] = useState({
    visible: false,
    sessionId: null,
    title: "",
  });

  // 语音输入相关状态
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [isTranscribing, setIsTranscribing] = useState(false);

  // 知识检索相关状态
  const [showKnowledgePanel, setShowKnowledgePanel] = useState(false);
  const [knowledgeSearchResults, setKnowledgeSearchResults] = useState(null);
  const [isSearchingKnowledge, setIsSearchingKnowledge] = useState(false);
  const [graphContext, setGraphContext] = useState(null);
  const [seedEntities, setSeedEntities] = useState([]);
  const [traversalStats, setTraversalStats] = useState(null);
  const [reasoningPaths, setReasoningPaths] = useState([]);

  const bubbleListRef = useRef(null);
  const chatEndRef = useRef(null);
  const isUserScrollingRef = useRef(false);
  const scrollIntervalRef = useRef(null);
  const scrollRafRef = useRef(null);
  const lastScrollHeightRef = useRef(0);
  const isStreamingRef = useRef(false);
  const chatSectionRef = useRef(null);
  const isSubmittingRef = useRef(false); // 防止重复提交的 ref

  // 语音录制相关 refs
  const mediaRecorderRef = useRef(null);
  const recordingTimerRef = useRef(null);
  const audioChunksRef = useRef([]);
  const isRecordingRef = useRef(false); // 用于解决闭包问题
  const stopRecordingRef = useRef(null); // 用于在 startRecording 中调用 stopRecording

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

  // 获取当前登录用户头像和用户名
  useEffect(() => {
    const loadUserInfo = () => {
      try {
        const userStr = localStorage.getItem("user");
        if (userStr) {
          const userData = JSON.parse(userStr);
          if (userData?.avatar_url) {
            setUserAvatar(userData.avatar_url);
          }
          if (userData?.username) {
            setUsername(userData.username);
          }
        }
      } catch (error) {
        console.error("加载用户信息失败:", error);
      }
    };

    loadUserInfo();
  }, []);

  useEffect(() => {
    initializeChat();
    loadSessions();
  }, [initializeChat, loadSessions]);

  /**
   * 【优化】轻量级检索判断 - 更宽松的判断逻辑
   * 支持更多台风相关查询场景
   */
  const shouldUseKnowledgeRetrieval = useCallback((question) => {
    // 台风相关核心关键词
    const typhoonKeywords = [
      "台风",
      "飓风",
      "气旋",
      "热带风暴",
      "热带低压",
      "超强台风",
      "强台风",
      "登陆",
      "路径",
      "风速",
      "气压",
      "强度",
      "风眼",
      "中心",
    ];

    // 常见台风名称（扩展列表）
    const typhoonNames = [
      "龙王",
      "山竹",
      "利奇马",
      "烟花",
      "灿都",
      "查特安",
      "榕树",
      "艾利",
      "桑达",
      "圆规",
      "南川",
      "玛瑙",
      "妮亚图",
      "雷伊",
      "舒力基",
      "彩云",
      "小熊",
      "查帕卡",
      "卢碧",
      "银河",
      "妮妲",
      "奥麦斯",
      "康森",
      "灿鸿",
      "浪卡",
      "莫拉菲",
      "天鹅",
      "艾莎尼",
      "环高",
      "科罗旺",
      "杜鹃",
      "纳莎",
      "纳沙",
      "天琴",
      "凤凰",
      "海鸥",
      "风神",
      "娜基莉",
      "夏浪",
      "麦德姆",
      "博罗依",
      "浣熊",
      "桦加沙",
      "米娜",
      "塔巴",
      "琵琶",
      "蓝湖",
      "剑鱼",
      "玲玲",
      "杨柳",
      "白鹿",
      "罗莎",
      "竹节草",
      "范斯高",
      "韦帕",
      "百合",
      "丹娜丝",
      "木恩",
      "圣帕",
      "蝴蝶",
      "洛鞍",
      "银杏",
      "桃芝",
      "万宜",
      "天兔",
    ];

    // 地理位置关键词（扩展）
    const locationKeywords = [
      "广东",
      "福建",
      "浙江",
      "海南",
      "台湾",
      "香港",
      "澳门",
      "广西",
      "江苏",
      "上海",
      "山东",
      "辽宁",
      "河北",
      "天津",
      "江西",
      "湖南",
      "湖北",
      "安徽",
      "河南",
      "广州",
      "深圳",
      "厦门",
      "福州",
      "杭州",
      "宁波",
      "温州",
      "海口",
      "三亚",
      "台北",
      "高雄",
      "南京",
      "苏州",
      "青岛",
      "烟台",
      "威海",
    ];

    // 查询意图关键词
    const intentKeywords = [
      "哪些",
      "什么",
      "谁",
      "哪里",
      "什么时候",
      "多少",
      "多强",
      "影响",
      "造成",
      "损失",
      "伤亡",
      "受灾",
      "对比",
      "比较",
      "最强",
      "最弱",
      "最大",
      "最小",
      "最近",
      "最新",
    ];

    // 检查各类关键词
    const hasTyphoonKeyword = typhoonKeywords.some((kw) =>
      question.includes(kw),
    );
    const hasTyphoonName = typhoonNames.some((name) => question.includes(name));
    const hasLocationKeyword = locationKeywords.some((kw) =>
      question.includes(kw),
    );
    const hasIntentKeyword = intentKeywords.some((kw) => question.includes(kw));

    // 时间模式（年份）
    const hasYearPattern = /\b(19|20)\d{2}\b/.test(question);

    // 台风编号模式（6位数字，如202401）
    const hasTyphoonIdPattern = /\b(19|20)\d{4}\b/.test(question);

    // 宽松的判断逻辑：满足任一条件即可触发知识检索
    // 1. 包含台风关键词
    // 2. 包含台风名称
    // 3. 包含地点 + 年份/意图
    // 4. 包含台风编号
    return (
      hasTyphoonKeyword ||
      hasTyphoonName ||
      hasTyphoonIdPattern ||
      (hasLocationKeyword && (hasYearPattern || hasIntentKeyword))
    );
  }, []);

  /**
   * 构建混合上下文（GraphRAG + 传统搜索）- 用于graph_result字段
   * 注意：提示词拼接已迁移到后端，前端只负责构建graph_result内容
   */
  const buildHybridContext = useCallback((graphRAGResult, fallbackResult) => {
    let context = graphRAGResult.context_text || "";

    if (
      fallbackResult?.typhoons?.length > 0 ||
      (Array.isArray(fallbackResult) && fallbackResult.length > 0)
    ) {
      context += "\n\n[补充检索结果]\n";
      const items = fallbackResult?.typhoons || fallbackResult;
      items.slice(0, 5).forEach((item, idx) => {
        context += `${idx + 1}. ${item.name_cn || item.typhoon_id} (${item.year}年)\n`;
      });
    }

    return context;
  }, []);

  /**
   * 构建传统搜索上下文 - 用于graph_result字段
   * 注意：提示词拼接已迁移到后端，前端只负责构建graph_result内容
   */
  const buildFallbackContext = useCallback((fallbackResult) => {
    let context = "";

    if (fallbackResult?.typhoons?.length > 0) {
      context += "共检索到以下台风信息：\n";
      fallbackResult.typhoons.slice(0, 10).forEach((item, idx) => {
        context += `${idx + 1}. ${item.name_cn || item.typhoon_id} `;
        context += `(${item.year}年, 最大风速${item.max_wind_speed}m/s)\n`;
      });
    } else if (Array.isArray(fallbackResult) && fallbackResult.length > 0) {
      context += "共检索到以下台风信息：\n";
      fallbackResult.slice(0, 10).forEach((item, idx) => {
        context += `${idx + 1}. ${item.name_cn || item.typhoon_id} `;
        context += `(${item.year}年, 最大风速${item.max_wind_speed}m/s)\n`;
      });
    }

    return context;
  }, []);

  const handleQuestionClick = useCallback(
    async (questionText) => {
      // 使用 ref 防止重复提交（比 state 更可靠，因为 ref 的更新是同步的）
      if (!questionText.trim() || sending || isSubmittingRef.current) return;

      const token = localStorage.getItem("token");
      if (!token) {
        message.error("请先登录后再使用 AI 对话助手");
        navigate("/login");
        return;
      }

      // 标记正在提交，防止重复点击
      isSubmittingRef.current = true;

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

      // 【优化】第一步：轻量级预判断
      const needsKnowledge = shouldUseKnowledgeRetrieval(questionText);
      let graphResult = ""; // 用于存储知识图谱检索结果，传递给后端
      let graphRAGResult = null;
      let graphDataToSave = null; // 用于存储完整的图谱可视化数据

      console.log("🔍 知识检索判断:", {
        question: questionText,
        needsKnowledge: needsKnowledge,
      });

      if (needsKnowledge) {
        setIsSearchingKnowledge(true);
        console.log("✅ 需要进行知识检索，开始调用GraphRAG...");

        try {
          console.log(
            "📤 调用GraphRAG LocalSearch API: /api/kg/graphrag/search",
          );
          console.log("📋 请求参数:", {
            query: questionText,
            maxDepth: 2,
            maxNodes: 50,
            includePaths: true,
            enableQualityCheck: true,
          });

          // 【优化】第二步：调用GraphRAG（后端统一处理实体识别和检索）
          const startTime = Date.now();
          graphRAGResult = await graphRAGLocalSearch(questionText, {
            maxDepth: 2,
            maxNodes: 50,
            includePaths: true,
            enableQualityCheck: true, // 启用质量评估
          });
          const endTime = Date.now();

          console.log(`✅ GraphRAG检索完成，耗时: ${endTime - startTime}ms`);
          console.log(
            "📦 GraphRAG检索结果:",
            JSON.stringify(graphRAGResult, null, 2),
          );
          console.log("📊 质量评分:", graphRAGResult?.quality_score);
          console.log("📈 质量等级:", graphRAGResult?.quality_level);
          console.log("🎯 种子实体:", graphRAGResult?.seed_entities);
          console.log(
            "🌐 子图节点数:",
            graphRAGResult?.subgraph?.nodes?.length || 0,
          );

          // 【优化】第三步：根据后端返回的质量评估结果决定如何使用
          // 质量等级与后端保持一致: high >= 0.7, medium >= 0.4, low < 0.4
          if (
            graphRAGResult.quality_score >= 0.7 ||
            graphRAGResult.quality_level === "high"
          ) {
            // 高质量结果：使用GraphRAG上下文增强
            console.log("✅ GraphRAG高质量结果，使用图谱上下文");

            setGraphContext({
              text: graphRAGResult.context_text,
              structured: graphRAGResult.context_structured,
              keywords:
                graphRAGResult.seed_entities?.map((e) => e.entity_name) || [],
              quality_level: graphRAGResult.quality_level,
              quality_score: graphRAGResult.quality_score,
            });

            setKnowledgeSearchResults(graphRAGResult.subgraph);
            setSeedEntities(graphRAGResult.seed_entities);
            setTraversalStats(graphRAGResult.traversal_stats);
            setReasoningPaths(graphRAGResult.reasoning_paths || []);
            setShowKnowledgePanel(true);

            // 保存graph_result，由后端拼接提示词
            graphResult = graphRAGResult.context_text || "";
            // 保存完整的图谱可视化数据
            graphDataToSave = {
              subgraph: graphRAGResult.subgraph,
              seed_entities: graphRAGResult.seed_entities,
              traversal_stats: graphRAGResult.traversal_stats,
              reasoning_paths: graphRAGResult.reasoning_paths || [],
              context: {
                text: graphRAGResult.context_text,
                structured: graphRAGResult.context_structured,
                keywords:
                  graphRAGResult.seed_entities?.map((e) => e.entity_name) || [],
                quality_level: graphRAGResult.quality_level,
                quality_score: graphRAGResult.quality_score,
              },
            };
            console.log("📝 GraphRAG上下文已保存，长度:", graphResult.length);
          } else if (
            graphRAGResult.quality_score >= 0.4 ||
            graphRAGResult.quality_level === "medium"
          ) {
            // 中等质量：GraphRAG + 传统搜索混合
            console.log("⚠️ GraphRAG中等质量，混合使用");

            const fallbackResult = await searchKnowledgeGraph(questionText, 10);

            // 构建混合的graph_result
            const hybridContext = buildHybridContext(
              graphRAGResult,
              fallbackResult,
            );
            graphResult = hybridContext;

            // 设置图谱上下文（使用GraphRAG结果）
            setGraphContext({
              text: graphRAGResult.context_text,
              structured: graphRAGResult.context_structured,
              keywords:
                graphRAGResult.seed_entities?.map((e) => e.entity_name) || [],
              quality_level: graphRAGResult.quality_level,
              quality_score: graphRAGResult.quality_score,
            });

            setSeedEntities(graphRAGResult.seed_entities);
            setTraversalStats(graphRAGResult.traversal_stats);
            setReasoningPaths(graphRAGResult.reasoning_paths || []);

            // 仍然展示可视化，但标记为"部分结果"
            setKnowledgeSearchResults(graphRAGResult.subgraph);
            setShowKnowledgePanel(true);

            // 保存完整的图谱可视化数据（中等质量）
            graphDataToSave = {
              subgraph: graphRAGResult.subgraph,
              seed_entities: graphRAGResult.seed_entities,
              traversal_stats: graphRAGResult.traversal_stats,
              reasoning_paths: graphRAGResult.reasoning_paths || [],
              context: {
                text: graphRAGResult.context_text,
                structured: graphRAGResult.context_structured,
                keywords:
                  graphRAGResult.seed_entities?.map((e) => e.entity_name) || [],
                quality_level: graphRAGResult.quality_level,
                quality_score: graphRAGResult.quality_score,
              },
            };
          } else {
            // 低质量：降级到传统搜索
            console.log("📉 GraphRAG质量低，降级到传统搜索");

            const fallbackResult = await searchKnowledgeGraph(questionText, 20);

            // 构建传统搜索的graph_result
            graphResult = buildFallbackContext(fallbackResult);

            // 可选：展示传统搜索结果
            if (fallbackResult?.length > 0) {
              setKnowledgeSearchResults({ typhoons: fallbackResult });
              setShowKnowledgePanel(true);
            }
          }
        } catch (error) {
          console.error("❌ GraphRAG检索失败:", error);
          console.error("错误详情:", error.message);
          // 异常降级到传统搜索
          try {
            console.log("🔄 降级到传统搜索...");
            const fallbackResult = await searchKnowledgeGraph(questionText, 20);
            console.log("✅ 传统搜索结果:", fallbackResult);

            // 构建传统搜索的graph_result
            graphResult = buildFallbackContext(fallbackResult);

            // 即使降级也要显示可视化
            if (
              fallbackResult?.length > 0 ||
              fallbackResult?.typhoons?.length > 0
            ) {
              setKnowledgeSearchResults(
                fallbackResult?.typhoons
                  ? fallbackResult
                  : { typhoons: fallbackResult },
              );
              setGraphContext({
                text: "使用传统搜索结果",
                keywords: [questionText],
              });
              setShowKnowledgePanel(true);
              console.log("✅ 已显示传统搜索结果面板");
            }
          } catch (fallbackError) {
            console.error("❌ 降级搜索也失败:", fallbackError);
          }
        } finally {
          setIsSearchingKnowledge(false);
        }
      }

      const aiMessageKey = `ai_${Date.now()}`;
      // 判断是否有知识图谱数据
      const hasKnowledgeContext =
        needsKnowledge &&
        (graphRAGResult?.quality_score >= 0.7 ||
          graphRAGResult?.quality_level === "high");
      const aiMessage = {
        key: aiMessageKey,
        role: "ai",
        content: "",
        reasoningContent: "",
        deepThinking: deepThinking, // 标记是否启用了深度思考模式
        timestamp: new Date().toISOString(),
        hasKnowledgeContext: hasKnowledgeContext, // 标记是否使用了高质量知识上下文
        graphData: graphDataToSave, // 保存知识图谱可视化数据，用于显示GraphRAG按钮
      };
      setMessages((prev) => [...prev, aiMessage]);
      setStreamingMessageKey(aiMessageKey);

      try {
        console.log("📤 开始发送问题到后端（流式传输）...", {
          sessionId: currentSessionId,
          question: questionText,
          graphResultLength: graphResult.length,
          hasGraphResult: graphResult.length > 0 ? "有" : "无",
          model: selectedModel,
          deepThinking: deepThinking,
        });

        await askAIQuestionStream(
          currentSessionId,
          questionText, // 传递原始问题
          selectedModel,
          deepThinking,
          graphResult, // 传递知识图谱检索结果
          graphDataToSave, // 传递完整的图谱可视化数据
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
        // 重置提交状态，允许新的提交
        isSubmittingRef.current = false;
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
      shouldUseKnowledgeRetrieval,
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
          // 根据 reasoning_content 是否存在判断是否是深度思考模式
          const hasReasoning =
            item.reasoning_content && item.reasoning_content.trim().length > 0;
          // 检查是否有知识图谱检索结果
          const hasGraphResult =
            item.graph_result && item.graph_result.trim().length > 0;
          // 检查是否有知识图谱可视化数据
          const hasGraphData = item.graph_data && item.graph_data.subgraph;
          historyMessages.push({
            key: `ai_${index}`,
            role: "ai",
            content: item.answer,
            reasoningContent: item.reasoning_content || "",
            deepThinking: hasReasoning, // 根据 reasoning_content 是否存在判断
            graphResult: item.graph_result || "", // 保存知识图谱检索结果
            graphData: item.graph_data || null, // 保存知识图谱可视化数据
            hasKnowledgeContext: hasGraphResult, // 标记是否有知识上下文
            hasGraphVisualization: hasGraphData, // 标记是否有图谱可视化数据
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

  const handleAvatarClick = useCallback(() => {
    navigate("/user-center");
  }, [navigate]);

  /**
   * 查看/切换历史知识图谱可视化
   * 如果面板已显示则隐藏，如果未显示则加载并显示
   */
  const handleViewGraphVisualization = useCallback(
    (msg) => {
      if (!msg.graphData) return;

      // 检查当前是否已经显示了知识图谱面板
      if (showKnowledgePanel) {
        // 如果面板已显示，则隐藏它
        setShowKnowledgePanel(false);
      } else {
        // 如果面板未显示，则加载数据并显示
        setKnowledgeSearchResults(msg.graphData.subgraph);
        setSeedEntities(msg.graphData.seed_entities);
        setTraversalStats(msg.graphData.traversal_stats);
        setReasoningPaths(msg.graphData.reasoning_paths || []);
        setGraphContext(msg.graphData.context);
        setShowKnowledgePanel(true);
      }
    },
    [showKnowledgePanel],
  );

  const handleLogout = useCallback(() => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    message.success("已退出登录");
    navigate("/login");
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

  // ==================== 会话管理功能 ====================

  /**
   * 删除会话
   */
  const handleDeleteSession = useCallback(
    async (sessionId) => {
      try {
        await deleteAISession(sessionId);
        message.success("会话已删除");

        // 更新会话列表
        setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));

        // 如果删除的是当前会话，创建新会话
        if (sessionId === currentSessionId) {
          await handleNewChat();
        }
      } catch (error) {
        console.error("删除会话失败:", error);
        message.error("删除会话失败");
      }
    },
    [currentSessionId, handleNewChat],
  );

  /**
   * 打开重命名对话框
   */
  const handleRenameSession = useCallback((sessionId, currentTitle) => {
    setRenameModal({
      visible: true,
      sessionId,
      title: currentTitle,
    });
  }, []);

  /**
   * 确认重命名
   */
  const confirmRename = useCallback(async () => {
    if (!renameModal.title.trim()) {
      message.warning("会话名称不能为空");
      return;
    }

    try {
      await renameAISession(renameModal.sessionId, renameModal.title.trim());
      message.success("重命名成功");

      // 更新会话列表
      setSessions((prev) =>
        prev.map((s) =>
          s.session_id === renameModal.sessionId
            ? { ...s, first_question: renameModal.title.trim() }
            : s,
        ),
      );

      setRenameModal({ visible: false, sessionId: null, title: "" });
    } catch (error) {
      console.error("重命名失败:", error);
      message.error("重命名失败");
    }
  }, [renameModal]);

  /**
   * 取消重命名
   */
  const cancelRename = useCallback(() => {
    setRenameModal({ visible: false, sessionId: null, title: "" });
  }, []);

  // ==================== 语音输入功能 ====================

  // 将 AudioBuffer 转换为 WAV 格式的 Blob
  const bufferToWave = useCallback((abuffer, len) => {
    let numOfChan = abuffer.numberOfChannels,
      length = len * numOfChan * 2 + 44,
      buffer = new ArrayBuffer(length),
      view = new DataView(buffer),
      channels = [],
      i,
      sample,
      offset = 0,
      pos = 0;

    // 写入 WAV 头部
    // "RIFF"
    setUint32(0x46464952);
    // file length - 8
    setUint32(length - 8);
    // "WAVE"
    setUint32(0x45564157);
    // "fmt " chunk
    setUint32(0x20746d66);
    // length = 16
    setUint32(16);
    // PCM (uncompressed)
    setUint16(1);
    // 声道数
    setUint16(numOfChan);
    // 采样率
    setUint32(abuffer.sampleRate);
    // 字节率
    setUint32(abuffer.sampleRate * 2 * numOfChan);
    // 块对齐
    setUint16(numOfChan * 2);
    // 位深度
    setUint16(16);
    // "data" chunk
    setUint32(0x61746164);
    // 数据长度
    setUint32(length - pos - 4);

    // 写入音频数据
    for (i = 0; i < abuffer.numberOfChannels; i++)
      channels.push(abuffer.getChannelData(i));

    while (pos < length) {
      for (i = 0; i < numOfChan; i++) {
        sample = Math.max(-1, Math.min(1, channels[i][offset]));
        sample = (0.5 + sample < 0 ? sample * 32768 : sample * 32767) | 0;
        view.setInt16(pos, sample, true);
        pos += 2;
      }
      offset++;
    }

    return new Blob([buffer], { type: "audio/wav" });

    function setUint16(data) {
      view.setUint16(pos, data, true);
      pos += 2;
    }

    function setUint32(data) {
      view.setUint32(pos, data, true);
      pos += 4;
    }
  }, []);

  /**
   * 调用后端 ASR 服务进行语音识别
   */
  const handleTranscribe = useCallback(async (blob) => {
    if (!blob) return;

    setIsTranscribing(true);
    try {
      // 使用 api.js 中的 transcribeAudio 函数
      const data = await transcribeAudio(blob, "auto");

      if (data.success) {
        // 将识别结果填入输入框
        setInputText((prev) => {
          const newText = prev + (prev ? " " : "") + data.text;
          return newText;
        });
        message.success(`语音转文字完成 (${data.language})`);
      } else {
        throw new Error(data.error || "识别失败");
      }
    } catch (error) {
      console.error("语音识别失败:", error);
      message.error(`语音转文字失败: ${error.message}`);
    } finally {
      setIsTranscribing(false);
      audioChunksRef.current = [];
    }
  }, []);

  /**
   * 停止录音
   */
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecordingRef.current) {
      // 停止录音并获取 WAV 格式的 Blob
      const audioBlob = mediaRecorderRef.current.stop();
      setIsRecording(false);
      isRecordingRef.current = false; // 更新 ref
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
      // 开始识别
      handleTranscribe(audioBlob);
    }
  }, [handleTranscribe]);

  // 将 stopRecording 存入 ref，供 startRecording 使用
  stopRecordingRef.current = stopRecording;

  /**
   * 开始录音 - 使用 Web Audio API 录制为 WAV 格式
   */
  const startRecording = useCallback(async () => {
    // 检查浏览器是否支持 getUserMedia
    console.log("录音诊断信息:", {
      userAgent: navigator.userAgent,
      mediaDevices: !!navigator.mediaDevices,
      getUserMedia: !!(
        navigator.mediaDevices && navigator.mediaDevices.getUserMedia
      ),
      isSecureContext: window.isSecureContext,
      location: window.location.href,
      protocol: window.location.protocol,
    });

    if (!navigator.mediaDevices) {
      message.error("navigator.mediaDevices 不可用，请检查浏览器权限设置");
      console.error("navigator.mediaDevices is undefined");
      return;
    }

    if (!navigator.mediaDevices.getUserMedia) {
      message.error(
        "您的浏览器不支持 getUserMedia API，请使用 Chrome、Edge 或 Safari 浏览器",
      );
      console.error("getUserMedia is not supported");
      return;
    }

    // 检查是否处于安全上下文（HTTPS 或 localhost）
    if (!window.isSecureContext) {
      message.error("语音输入需要在安全连接(HTTPS)或本地环境下使用");
      console.error("Not in secure context");
      return;
    }

    try {
      // 请求麦克风权限
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000, // 16kHz 采样率
          channelCount: 1, // 单声道
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      // 创建 AudioContext
      const audioContext = new (
        window.AudioContext || window.webkitAudioContext
      )({
        sampleRate: 16000,
      });

      // 创建音频源
      const source = audioContext.createMediaStreamSource(stream);

      // 创建处理器节点
      const processor = audioContext.createScriptProcessor(4096, 1, 1);

      // 存储音频数据
      const audioData = [];

      processor.onaudioprocess = (e) => {
        const channelData = e.inputBuffer.getChannelData(0);
        audioData.push(new Float32Array(channelData));
      };

      // 连接节点
      source.connect(processor);
      processor.connect(audioContext.destination);

      // 存储引用以便停止时使用
      mediaRecorderRef.current = {
        audioContext,
        processor,
        source,
        stream,
        audioData,
        stop: function () {
          this.processor.disconnect();
          this.source.disconnect();
          this.stream.getTracks().forEach((track) => track.stop());
          this.audioContext.close();

          // 合并音频数据
          const length = this.audioData.reduce(
            (acc, curr) => acc + curr.length,
            0,
          );
          const mergedData = new Float32Array(length);
          let offset = 0;
          this.audioData.forEach((chunk) => {
            mergedData.set(chunk, offset);
            offset += chunk.length;
          });

          // 创建 AudioBuffer
          const audioBuffer = audioContext.createBuffer(1, length, 16000);
          audioBuffer.getChannelData(0).set(mergedData);

          // 转换为 WAV
          return bufferToWave(audioBuffer, length);
        },
      };

      setIsRecording(true);
      isRecordingRef.current = true; // 更新 ref
      setRecordingTime(0);

      // 开始计时
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime((prev) => {
          // 限制最大录音时长为 60 秒
          if (prev >= 59) {
            stopRecordingRef.current?.();
            return 60;
          }
          return prev + 1;
        });
      }, 1000);

      message.info("开始录音，请点击麦克风图标停止");
    } catch (error) {
      console.error("录音失败:", error);
      if (error.name === "NotAllowedError") {
        message.error("麦克风权限被拒绝，请在浏览器设置中允许访问麦克风");
      } else if (error.name === "NotFoundError") {
        message.error("未找到麦克风设备");
      } else {
        message.error("无法访问麦克风，请检查设备");
      }
    }
  }, [bufferToWave]);

  // 清理函数
  useEffect(() => {
    return () => {
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
      }
      if (mediaRecorderRef.current && isRecordingRef.current) {
        mediaRecorderRef.current.stop();
      }
    };
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
        onDeleteSession={handleDeleteSession}
        onRenameSession={handleRenameSession}
      />

      {/* 重命名对话框 */}
      <Modal
        title={
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "8px",
                background: "linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 4px 12px rgba(99, 102, 241, 0.3)",
              }}
            >
              <EditOutlined style={{ color: "#fff", fontSize: "16px" }} />
            </div>
            <span style={{ fontSize: "16px", fontWeight: "600" }}>
              重命名对话
            </span>
          </div>
        }
        open={renameModal.visible}
        onOk={confirmRename}
        onCancel={cancelRename}
        okText="确认"
        cancelText="取消"
        centered
        width={520}
        okButtonProps={{
          type: "primary",
          style: {
            background: "linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%)",
            border: "none",
            boxShadow: "0 4px 12px rgba(99, 102, 241, 0.35)",
          },
        }}
        cancelButtonProps={{
          style: {
            borderRadius: "10px",
            height: "38px",
          },
        }}
      >
        <div style={{ marginBottom: "12px" }}>
          <Text
            type="secondary"
            style={{
              fontSize: "13px",
              color: "#64748B",
              lineHeight: "1.6",
            }}
          >
            请输入新的对话名称
          </Text>
        </div>
        <Input
          placeholder="请输入新的对话名称..."
          value={renameModal.title}
          onChange={(e) =>
            setRenameModal((prev) => ({ ...prev, title: e.target.value }))
          }
          onPressEnter={confirmRename}
          maxLength={50}
          showCount
          allowClear
          prefix={
            <EditOutlined
              style={{
                color: "#94A3B8",
                transition: "color 0.2s ease",
              }}
            />
          }
          style={{
            borderRadius: "10px",
          }}
        />
      </Modal>

      {/* 主内容区域 - 包含聊天区和知识面板 */}
      <div className="ai-agent-content-wrapper">
        <main
          className={`ai-agent-main ${showKnowledgePanel ? "with-knowledge-panel" : ""}`}
          role="main"
        >
          {/* 右上角用户头像 */}
          <div className="ai-agent-header-avatar">
            <Dropdown
              menu={{
                items: [
                  {
                    key: "user-center",
                    label: "用户中心",
                    icon: <UserOutlined />,
                    onClick: handleAvatarClick,
                  },
                  {
                    type: "divider",
                  },
                  {
                    key: "logout",
                    label: "退出登录",
                    icon: <LogoutOutlined />,
                    onClick: handleLogout,
                  },
                ],
              }}
              placement="bottomRight"
              trigger={["hover"]}
            >
              <Avatar
                src={userAvatar || undefined}
                icon={!userAvatar && <UserOutlined />}
                size={50}
                style={{
                  cursor: "pointer",
                  background:
                    "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
                  boxShadow: "0 4px 12px rgba(99, 102, 241, 0.35)",
                }}
              />
            </Dropdown>
          </div>

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
                username={username}
              />
            ) : (
              <MessageList
                messages={messages}
                bubbleListRef={bubbleListRef}
                streamingMessageKey={streamingMessageKey}
                chatEndRef={chatEndRef}
                userAvatar={userAvatar}
                onAvatarClick={handleAvatarClick}
                onViewGraphVisualization={handleViewGraphVisualization}
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
            isRecording={isRecording}
            recordingTime={recordingTime}
            isTranscribing={isTranscribing}
            onStartRecording={startRecording}
            onStopRecording={stopRecording}
          />

          {/* 知识检索指示器 */}
          {isSearchingKnowledge && (
            <div className="knowledge-search-indicator">
              <Spin size="small" />
              <span>正在检索知识图谱...</span>
            </div>
          )}
        </main>

        {/* 知识检索结果面板 - 放在内容区域内 */}
        <KnowledgeGraphPanel
          isVisible={showKnowledgePanel}
          searchResults={knowledgeSearchResults}
          graphContext={graphContext}
          onClose={() => setShowKnowledgePanel(false)}
          isLoading={isSearchingKnowledge}
          seedEntities={seedEntities}
          traversalStats={traversalStats}
          reasoningPaths={reasoningPaths}
        />
      </div>
    </div>
  );
}

export default AIAgent;
