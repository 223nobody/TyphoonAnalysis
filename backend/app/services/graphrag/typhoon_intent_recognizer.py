"""
台风领域专用意图识别与实体抽取模块
针对台风问答场景，精准识别用户查询中的台风名称、时间、地点、影响范围等关键实体
"""

import re
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger


class TyphoonIntentType(str, Enum):
    """台风领域问题意图类型"""
    # 基础信息查询
    BASIC_INFO = "basic_info"  # 台风基本信息（名称、编号、年份）
    PATH_QUERY = "path_query"  # 路径查询（移动路径、轨迹）
    INTENSITY_QUERY = "intensity_query"  # 强度查询（风速、气压、等级）
    TIME_QUERY = "time_query"  # 时间查询（生成时间、消散时间、持续时间）
    
    # 登陆与影响
    LANDFALL_QUERY = "landfall_query"  # 登陆查询（登陆地点、时间、强度）
    IMPACT_QUERY = "impact_query"  # 影响查询（影响区域、受灾情况）
    AFFECTED_AREA_QUERY = "affected_area_query"  # 影响地区查询
    
    # 预测与对比
    PREDICTION_QUERY = "prediction_query"  # 预测查询（未来路径、强度预测）
    COMPARISON_QUERY = "comparison_query"  # 对比查询（多个台风对比）
    SIMILAR_QUERY = "similar_query"  # 相似台风查询
    
    # 统计与排名
    STATISTICS_QUERY = "statistics_query"  # 统计查询（某年台风数量、登陆次数）
    RANKING_QUERY = "ranking_query"  # 排名查询（最强、最弱、最早、最晚）
    
    # 防御与建议
    DEFENSE_QUERY = "defense_query"  # 防御措施查询
    PREVENTION_QUERY = "prevention_query"  # 防灾建议查询
    
    # 未知/通用
    UNKNOWN = "unknown"


class TyphoonEntityType(str, Enum):
    """台风领域实体类型"""
    TYPHOON_NAME = "typhoon_name"  # 台风名称
    TYPHOON_ID = "typhoon_id"  # 台风编号
    YEAR = "year"  # 年份
    MONTH = "month"  # 月份
    LOCATION = "location"  # 地理位置
    INTENSITY_LEVEL = "intensity_level"  # 强度等级
    WIND_SPEED = "wind_speed"  # 风速
    PRESSURE = "pressure"  # 气压
    DATE = "date"  # 具体日期
    DURATION = "duration"  # 持续时间
    REGION = "region"  # 区域（华南、华东等）


@dataclass
class TyphoonEntity:
    """台风领域实体"""
    entity_type: TyphoonEntityType
    value: str
    start_pos: int
    end_pos: int
    confidence: float = 1.0
    normalized_value: Optional[str] = None
    
    def __post_init__(self):
        if self.normalized_value is None:
            self.normalized_value = self.value


@dataclass
class TyphoonIntent:
    """台风领域意图"""
    intent_type: TyphoonIntentType
    confidence: float
    sub_intents: List[TyphoonIntentType] = field(default_factory=list)
    attributes: List[str] = field(default_factory=list)
    

@dataclass
class TyphoonQueryAnalysis:
    """台风查询分析结果"""
    original_query: str
    intent: TyphoonIntent
    entities: List[TyphoonEntity]
    query_type: str  # "single_typhoon", "multi_typhoon", "year_overview", "comparison"
    temporal_context: Dict = field(default_factory=dict)
    spatial_context: Dict = field(default_factory=dict)
    

class TyphoonIntentRecognizer:
    """台风领域意图识别器"""
    
    # 台风名称列表（扩展版）
    TYPHOON_NAMES = {
        # 近年台风
        "天琴", "凤凰", "海鸥", "风神", "娜基莉", "夏浪", "麦德姆", "博罗依",
        "浣熊", "桦加沙", "米娜", "塔巴", "琵琶", "蓝湖", "剑鱼", "玲玲",
        "杨柳", "白鹿", "罗莎", "竹节草", "范斯高", "韦帕", "百合", "丹娜丝",
        "木恩", "圣帕", "蝴蝶", "洛鞍", "银杏", "桃芝", "万宜", "天兔",
        "马力斯", "格美", "派比安", "玛莉亚", "山神", "安比", "悟空", "云雀",
        "珊珊", "摩羯", "丽琵", "贝碧嘉", "普拉桑", "苏力", "西马仑", "飞燕",
        "山竹", "百里嘉", "潭美", "康妮", "玉兔", "桃芝", "天兔", "万宜",
        # 历史著名台风
        "龙王", "利奇马", "烟花", "灿都", "查特安", "榕树", "艾利", "桑达",
        "圆规", "南川", "玛瑙", "妮亚图", "雷伊", "舒力基", "彩云", "小熊",
        "查帕卡", "卢碧", "银河", "妮妲", "奥麦斯", "康森", "灿鸿", "浪卡",
        "莫拉菲", "天鹅", "艾莎尼", "环高", "科罗旺", "杜鹃", "纳莎", "纳沙",
        "威马逊", "彩虹", "莫兰蒂", "鲇鱼", "海马", "莎莉嘉", "达维", "海葵",
        "启德", "天秤", "布拉万", "三巴", "杰拉华", "艾云尼", "马力斯",
        # 更多历史台风
        "珍珠", "碧利斯", "格美", "派比安", "桑美", "伊欧凯", "圣帕", "韦帕",
        "罗莎", "海燕", "菲特", "丹娜丝", "百合", "韦森特", "启德", "达维",
        "苏拉", "海葵", "天秤", "布拉万", "启德", "达维", "苏拉", "海葵",
    }
    
    # 地理关键词（扩展版）
    LOCATION_KEYWORDS = {
        # 省份
        "广东": "广东", "福建": "福建", "浙江": "浙江", "海南": "海南",
        "台湾": "台湾", "香港": "香港", "澳门": "澳门", "广西": "广西",
        "江苏": "江苏", "上海": "上海", "山东": "山东", "辽宁": "辽宁",
        "河北": "河北", "天津": "天津", "江西": "江西", "湖南": "湖南",
        "湖北": "湖北", "安徽": "安徽", "河南": "河南", "山西": "山西",
        "贵州": "贵州", "云南": "云南", "四川": "四川", "重庆": "重庆",
        # 主要城市
        "广州": "广州", "深圳": "深圳", "珠海": "珠海", "汕头": "汕头",
        "湛江": "湛江", "江门": "江门", "茂名": "茂名", "阳江": "阳江",
        "韶关": "韶关", "惠州": "惠州", "东莞": "东莞", "中山": "中山",
        "佛山": "佛山", "肇庆": "肇庆", "清远": "清远", "云浮": "云浮",
        "厦门": "厦门", "福州": "福州", "泉州": "泉州", "漳州": "漳州",
        "宁德": "宁德", "莆田": "莆田", "龙岩": "龙岩", "三明": "三明",
        "南平": "南平", "平潭": "平潭",
        "杭州": "杭州", "宁波": "宁波", "温州": "温州", "台州": "台州",
        "舟山": "舟山", "嘉兴": "嘉兴", "绍兴": "绍兴", "湖州": "湖州",
        "金华": "金华", "衢州": "衢州", "丽水": "丽水",
        "海口": "海口", "三亚": "三亚", "三沙": "三沙", "儋州": "儋州",
        "文昌": "文昌", "琼海": "琼海", "万宁": "万宁", "东方": "东方",
        "五指山": "五指山", "乐东": "乐东", "陵水": "陵水", "保亭": "保亭",
        "台北": "台北", "高雄": "高雄", "台中": "台中", "花莲": "花莲",
        "台南": "台南", "基隆": "基隆", "桃园": "桃园", "新竹": "新竹",
        "嘉义": "嘉义", "屏东": "屏东", "宜兰": "宜兰", "台东": "台东",
        "南京": "南京", "苏州": "苏州", "无锡": "无锡", "常州": "常州",
        "南通": "南通", "扬州": "扬州", "徐州": "徐州", "连云港": "连云港",
        "淮安": "淮安", "盐城": "盐城", "镇江": "镇江", "泰州": "泰州",
        "宿迁": "宿迁",
        "青岛": "青岛", "烟台": "烟台", "威海": "威海", "日照": "日照",
        "潍坊": "潍坊", "东营": "东营", "滨州": "滨州", "淄博": "淄博",
        "济南": "济南", "泰安": "泰安", "临沂": "临沂", "济宁": "济宁",
        # 区域
        "华南": "华南", "华东": "华东", "华北": "华北", "东北": "东北",
        "华中": "华中", "西南": "西南", "东南沿海": "东南沿海",
        "南海": "南海", "东海": "东海", "黄海": "黄海", "渤海": "渤海",
        "台湾海峡": "台湾海峡", "琼州海峡": "琼州海峡",
        "珠江口": "珠江口", "长江口": "长江口", "杭州湾": "杭州湾",
    }
    
    # 强度等级关键词
    INTENSITY_KEYWORDS = {
        "热带低压": "TD", "TD": "TD",
        "热带风暴": "TS", "TS": "TS",
        "强热带风暴": "STS", "STS": "STS",
        "台风": "TY", "TY": "TY",
        "强台风": "STY", "STY": "STY",
        "超强台风": "SuperTY", "SuperTY": "SuperTY",
    }
    
    # 意图识别模式
    INTENT_PATTERNS = {
        # 基础信息
        TyphoonIntentType.BASIC_INFO: {
            "patterns": [
                r"什么.*?(?:台风|飓风|气旋)", r"(?:台风|飓风|气旋).*?叫什么",
                r"(?:编号|代号|ID)", r"基本信息", r"简介", r"概况",
                r"哪一年.*?(?:台风|发生)", r"(?:台风|飓风).*?哪年",
            ],
            "keywords": ["名称", "编号", "年份", "基本信息", "简介", "概况"],
            "priority": 1
        },
        
        # 路径查询
        TyphoonIntentType.PATH_QUERY: {
            "patterns": [
                r"路径", r"轨迹", r"移动路线", r"走向", r"经过哪里",
                r"从哪里.*?(?:来|生成)", r"(?:去|消散|结束).*?哪里",
                r"怎么移动", r"移动方向", r"转折点",
            ],
            "keywords": ["路径", "轨迹", "路线", "走向", "移动", "经过"],
            "priority": 1
        },
        
        # 强度查询
        TyphoonIntentType.INTENSITY_QUERY: {
            "patterns": [
                r"(?:最大|最强).*?(?:风速|风力|风)",
                r"(?:最低|最小).*?(?:气压|压力)",
                r"(?:强度|等级).*?(?:多少|多大|是什么)",
                r"(?:几级|多大|多强)",
                r"(?:风速|风力).*?(?:多少|多大)",
                r"(?:中心气压|气压).*?(?:多少|多低)",
            ],
            "keywords": ["风速", "风力", "气压", "强度", "等级", "几级"],
            "priority": 1
        },
        
        # 时间查询
        TyphoonIntentType.TIME_QUERY: {
            "patterns": [
                r"(?:什么|哪个|哪段)?时间",
                r"(?:生成|形成|开始).*?(?:时间|日期)",
                r"(?:消散|结束|消失).*?(?:时间|日期)",
                r"持续.*?(?:多久|多长时间|几天)",
                r"(?:发生|出现).*?(?:时间|日期)",
                r"(?:哪年|哪月|哪天)",
            ],
            "keywords": ["时间", "日期", "生成", "消散", "持续", "多久"],
            "priority": 1
        },
        
        # 登陆查询
        TyphoonIntentType.LANDFALL_QUERY: {
            "patterns": [
                r"(?:登陆|登录|登入)",
                r"(?:哪里|何处).*?(?:登陆|登录)",
                r"(?:登陆|登录).*?(?:哪里|何处|地点|位置)",
                r"(?:登陆|登录).*?(?:时间|日期|何时)",
                r"(?:登陆|登录).*?(?:强度|等级|风力)",
                r"(?:几次|多少).*?(?:登陆|登录)",
            ],
            "keywords": ["登陆", "登录", "登入", "上岸", "登陆点"],
            "priority": 2
        },
        
        # 影响查询
        TyphoonIntentType.IMPACT_QUERY: {
            "patterns": [
                r"(?:影响|危害|灾害|损失|破坏|受灾)",
                r"(?:造成|导致|引发).*?(?:什么|哪些|多大)",
                r"(?:损失|伤亡|死亡|失踪|受伤)",
                r"(?:经济|财产).*?(?:损失|影响)",
                r"(?:受灾|影响).*?(?:范围|面积|人口)",
            ],
            "keywords": ["影响", "灾害", "损失", "伤亡", "破坏", "受灾", "危害"],
            "priority": 2
        },
        
        # 影响地区查询
        TyphoonIntentType.AFFECTED_AREA_QUERY: {
            "patterns": [
                r"(?:影响|波及|涉及).*?(?:哪里|哪些|区域|地区|城市)",
                r"(?:哪些|哪个).*?(?:地方|城市|省份|地区).*?(?:受|被).*?(?:影响|波及)",
                r"(?:影响范围|波及范围|影响区域)",
            ],
            "keywords": ["影响", "波及", "涉及", "范围", "区域"],
            "priority": 2
        },
        
        # 预测查询
        TyphoonIntentType.PREDICTION_QUERY: {
            "patterns": [
                r"(?:预测|预报|预计|估计).*?(?:路径|走向|方向)",
                r"(?:未来|接下来|之后).*?(?:怎么|如何|去哪|去哪)",
                r"(?:会|将|可能).*?(?:登陆|影响|去哪)",
                r"(?:强度|风力).*?(?:变化|增强|减弱)",
            ],
            "keywords": ["预测", "预报", "预计", "未来", "接下来"],
            "priority": 2
        },
        
        # 对比查询
        TyphoonIntentType.COMPARISON_QUERY: {
            "patterns": [
                r"(?:对比|比较|vs|VS|和|与).*?(?:相比|比较|哪个|谁)",
                r"(?:哪个|谁).*?(?:更强|更弱|更大|更小|更早|更晚)",
                r"(?:强|弱|大|小|早|晚).*?(?:还是|或者)",
            ],
            "keywords": ["对比", "比较", "vs", "相比", "哪个更"],
            "priority": 3
        },
        
        # 相似台风查询
        TyphoonIntentType.SIMILAR_QUERY: {
            "patterns": [
                r"(?:相似|类似|相近|差不多).*?(?:台风|的)",
                r"(?:类似|相同).*?(?:路径|强度|特征)",
                r"(?:还有哪些|还有谁).*?(?:类似|相似)",
            ],
            "keywords": ["相似", "类似", "相近", "差不多"],
            "priority": 3
        },
        
        # 统计查询
        TyphoonIntentType.STATISTICS_QUERY: {
            "patterns": [
                r"(?:多少|几个|数量|统计|哪些).*?(?:台风|个)",
                r"(?:共有|总共有|合计).*?(?:多少|几个|哪些)",
                r"(?:登陆|影响).*?(?:几次|多少次|几个)",
                r"(?:频率|次数|概率)",
                r"(?:出现|发生|生成).*?(?:哪些|什么)",
            ],
            "keywords": ["多少", "几个", "数量", "统计", "总共", "合计", "哪些", "出现", "发生"],
            "priority": 2
        },
        
        # 排名查询
        TyphoonIntentType.RANKING_QUERY: {
            "patterns": [
                r"(?:最强|最弱|最大|最小|最早|最晚|最多|最少)",
                r"(?:第几|排名|排行|前十|前\d+)",
                r"(?:历史上|有史以来|近年).*?(?:最强|最弱|最大)",
                r"(?:风速|强度|气压).*?(?:最高|最低|最大|最小)",
            ],
            "keywords": ["最强", "最弱", "最大", "最小", "排名", "第几", "前十"],
            "priority": 3
        },
        
        # 防御措施查询
        TyphoonIntentType.DEFENSE_QUERY: {
            "patterns": [
                r"(?:防御|防范|防护|抵御|应对).*?(?:措施|方法|建议|办法)",
                r"(?:怎么|如何).*?(?:防御|防范|应对|防护)",
                r"(?:应该|需要).*?(?:做|采取|准备).*?(?:什么|哪些)",
                r"(?:注意|警惕|小心).*?(?:什么|哪些|事项)",
            ],
            "keywords": ["防御", "防范", "防护", "应对", "措施", "建议"],
            "priority": 2
        },
        
        # 防灾建议查询
        TyphoonIntentType.PREVENTION_QUERY: {
            "patterns": [
                r"(?:防灾|减灾|预防|预警).*?(?:措施|建议|方法|办法)",
                r"(?:预警|警报|信号).*?(?:级别|等级|颜色)",
                r"(?:撤离|转移|疏散|避难)",
                r"(?:准备|储备).*?(?:物资|东西|物品)",
            ],
            "keywords": ["防灾", "减灾", "预警", "撤离", "转移", "准备"],
            "priority": 2
        },
    }
    
    def __init__(self):
        self.compiled_patterns = self._compile_patterns()
        
    def _compile_patterns(self) -> Dict[TyphoonIntentType, List[re.Pattern]]:
        """编译正则表达式模式"""
        compiled = {}
        for intent_type, config in self.INTENT_PATTERNS.items():
            compiled[intent_type] = [
                re.compile(pattern, re.IGNORECASE) 
                for pattern in config["patterns"]
            ]
        return compiled
    
    def recognize_intent(self, query: str) -> TyphoonIntent:
        """
        识别查询意图
        
        Args:
            query: 用户查询
            
        Returns:
            TyphoonIntent: 识别的意图
        """
        query_lower = query.lower()
        intent_scores = {}
        
        # 计算每个意图的匹配分数
        for intent_type, patterns in self.compiled_patterns.items():
            score = 0.0
            matched = False
            
            # 正则匹配
            for pattern in patterns:
                if pattern.search(query):
                    score += 1.0
                    matched = True
            
            # 关键词匹配
            config = self.INTENT_PATTERNS[intent_type]
            for keyword in config["keywords"]:
                if keyword in query:
                    score += 0.5
            
            # 优先级加权
            priority = config.get("priority", 1)
            score *= priority
            
            if matched or score > 0:
                intent_scores[intent_type] = score
        
        # 选择最高分的意图
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            best_score = intent_scores[best_intent]
            
            # 计算置信度 - 使用更合理的算法
            # 1. 基础分数：最佳意图的原始分数
            # 2. 竞争度：与其他意图的差距
            # 3. 匹配度：匹配的模式和关键词数量
            total_score = sum(intent_scores.values())
            
            # 基础置信度：最佳分数占总分的比例
            base_confidence = best_score / total_score if total_score > 0 else 0.5
            
            # 考虑匹配强度：根据匹配的模式数量和优先级调整
            # 如果只有一个意图匹配，降低置信度以避免过度自信
            matched_intent_count = len(intent_scores)
            if matched_intent_count == 1:
                # 单一匹配时，根据分数高低调整（最高0.85）
                confidence = min(base_confidence * 0.85, 0.85)
            else:
                # 多个意图匹配时，根据竞争度调整
                second_best_score = sorted(intent_scores.values(), reverse=True)[1] if matched_intent_count > 1 else 0
                gap = (best_score - second_best_score) / best_score if best_score > 0 else 0
                confidence = base_confidence * (0.7 + 0.3 * gap)  # 竞争度越高，置信度越高
            
            # 确保置信度在合理范围内
            confidence = max(0.3, min(confidence, 0.95))
            
            # 识别子意图（第二高的意图）
            sub_intents = sorted(
                [(k, v) for k, v in intent_scores.items() if k != best_intent],
                key=lambda x: x[1],
                reverse=True
            )[:2]
            
            return TyphoonIntent(
                intent_type=best_intent,
                confidence=round(confidence, 2),
                sub_intents=[intent for intent, _ in sub_intents],
                attributes=self._extract_intent_attributes(best_intent, query)
            )
        
        return TyphoonIntent(
            intent_type=TyphoonIntentType.UNKNOWN,
            confidence=0.3,
            sub_intents=[],
            attributes=[]
        )
    
    def extract_entities(self, query: str) -> List[TyphoonEntity]:
        """
        提取台风领域实体
        
        Args:
            query: 用户查询
            
        Returns:
            List[TyphoonEntity]: 提取的实体列表
        """
        entities = []
        
        # 1. 提取台风名称
        entities.extend(self._extract_typhoon_names(query))
        
        # 2. 提取台风编号（6位数字，格式YYYYMM）
        entities.extend(self._extract_typhoon_ids(query))
        
        # 3. 提取年份
        entities.extend(self._extract_years(query))
        
        # 4. 提取月份
        entities.extend(self._extract_months(query))
        
        # 5. 提取地理位置
        entities.extend(self._extract_locations(query))
        
        # 6. 提取强度等级
        entities.extend(self._extract_intensity_levels(query))
        
        # 7. 提取风速
        entities.extend(self._extract_wind_speeds(query))
        
        # 8. 提取气压
        entities.extend(self._extract_pressures(query))
        
        # 9. 提取日期
        entities.extend(self._extract_dates(query))
        
        # 10. 提取区域
        entities.extend(self._extract_regions(query))
        
        # 去重并按位置排序
        seen = set()
        unique_entities = []
        for entity in sorted(entities, key=lambda x: x.start_pos):
            key = (entity.entity_type, entity.value)
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)
        
        return unique_entities
    
    def _extract_typhoon_names(self, query: str) -> List[TyphoonEntity]:
        """提取台风名称"""
        entities = []
        
        # 格式1: XX台风 或 台风XX
        pattern1 = r"([\u4e00-\u9fa5]{2,6})(?=台风|飓风|气旋)"
        for match in re.finditer(pattern1, query):
            name = match.group(1)
            exclude_words = {"这个", "那个", "什么", "哪个", "一个", "热带", "强热带", "超强", "强"}
            if name not in exclude_words and len(name) >= 2:
                if name in self.TYPHOON_NAMES:
                    entities.append(TyphoonEntity(
                        entity_type=TyphoonEntityType.TYPHOON_NAME,
                        value=name,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        confidence=0.95
                    ))
        
        # 格式2: 台风XX
        pattern2 = r"台风([\u4e00-\u9fa5]{2,6})"
        for match in re.finditer(pattern2, query):
            name = match.group(1)
            if name in self.TYPHOON_NAMES:
                entities.append(TyphoonEntity(
                    entity_type=TyphoonEntityType.TYPHOON_NAME,
                    value=name,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.95
                ))
        
        # 直接匹配台风名称
        for name in self.TYPHOON_NAMES:
            if name in query and len(name) >= 2:
                # 检查是否已经被提取
                already_extracted = any(
                    e.value == name and e.entity_type == TyphoonEntityType.TYPHOON_NAME
                    for e in entities
                )
                if not already_extracted:
                    pos = query.find(name)
                    entities.append(TyphoonEntity(
                        entity_type=TyphoonEntityType.TYPHOON_NAME,
                        value=name,
                        start_pos=pos,
                        end_pos=pos + len(name),
                        confidence=0.9
                    ))
        
        return entities
    
    def _extract_typhoon_ids(self, query: str) -> List[TyphoonEntity]:
        """提取台风编号（6位数字，格式YYYYMM）"""
        entities = []
        pattern = r"\b(19|20)(\d{2})(0[1-9]|1[0-2])\b"
        
        for match in re.finditer(pattern, query):
            typhoon_id = match.group(0)
            year = int(typhoon_id[:4])
            if 1949 <= year <= 2100:
                entities.append(TyphoonEntity(
                    entity_type=TyphoonEntityType.TYPHOON_ID,
                    value=typhoon_id,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.95,
                    normalized_value=typhoon_id
                ))
        
        return entities
    
    def _extract_years(self, query: str) -> List[TyphoonEntity]:
        """提取年份"""
        entities = []
        
        # 4位年份
        pattern = r"(?:^|[^0-9])(19[6-9]\d|20[0-3]\d)(?:[^0-9]|$|年)"
        for match in re.finditer(pattern, query):
            year_str = match.group(1)
            year = int(year_str)
            if 1960 <= year <= 2035:
                entities.append(TyphoonEntity(
                    entity_type=TyphoonEntityType.YEAR,
                    value=year_str,
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.9,
                    normalized_value=str(year)
                ))
        
        return entities
    
    def _extract_months(self, query: str) -> List[TyphoonEntity]:
        """提取月份"""
        entities = []
        
        # 数字月份
        pattern = r"(\d{1,2})月"
        for match in re.finditer(pattern, query):
            month = int(match.group(1))
            if 1 <= month <= 12:
                entities.append(TyphoonEntity(
                    entity_type=TyphoonEntityType.MONTH,
                    value=match.group(0),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.9,
                    normalized_value=str(month)
                ))
        
        return entities
    
    def _extract_locations(self, query: str) -> List[TyphoonEntity]:
        """提取地理位置"""
        entities = []
        
        for location, normalized in self.LOCATION_KEYWORDS.items():
            if location in query:
                pos = query.find(location)
                entities.append(TyphoonEntity(
                    entity_type=TyphoonEntityType.LOCATION,
                    value=location,
                    start_pos=pos,
                    end_pos=pos + len(location),
                    confidence=0.9,
                    normalized_value=normalized
                ))
        
        return entities
    
    def _extract_intensity_levels(self, query: str) -> List[TyphoonEntity]:
        """提取强度等级"""
        entities = []
        
        for level_name, code in self.INTENSITY_KEYWORDS.items():
            if level_name in query:
                pos = query.find(level_name)
                entities.append(TyphoonEntity(
                    entity_type=TyphoonEntityType.INTENSITY_LEVEL,
                    value=level_name,
                    start_pos=pos,
                    end_pos=pos + len(level_name),
                    confidence=0.9,
                    normalized_value=code
                ))
        
        return entities
    
    def _extract_wind_speeds(self, query: str) -> List[TyphoonEntity]:
        """提取风速"""
        entities = []
        
        # 风速数值（支持 m/s, km/h, 级）
        pattern = r"(\d+(?:\.\d+)?)\s*(m/s|米/秒|km/h|公里/小时|级)"
        for match in re.finditer(pattern, query):
            entities.append(TyphoonEntity(
                entity_type=TyphoonEntityType.WIND_SPEED,
                value=match.group(0),
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.85
            ))
        
        return entities
    
    def _extract_pressures(self, query: str) -> List[TyphoonEntity]:
        """提取气压"""
        entities = []
        
        # 气压数值（支持 hPa, 百帕）
        pattern = r"(\d{3,4})\s*(hPa|百帕)"
        for match in re.finditer(pattern, query):
            entities.append(TyphoonEntity(
                entity_type=TyphoonEntityType.PRESSURE,
                value=match.group(0),
                start_pos=match.start(),
                end_pos=match.end(),
                confidence=0.85
            ))
        
        return entities
    
    def _extract_dates(self, query: str) -> List[TyphoonEntity]:
        """提取日期"""
        entities = []
        
        # 日期格式：YYYY-MM-DD 或 YYYY年MM月DD日
        patterns = [
            r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})",
            r"(\d{4})年(\d{1,2})月(\d{1,2})日",
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, query):
                entities.append(TyphoonEntity(
                    entity_type=TyphoonEntityType.DATE,
                    value=match.group(0),
                    start_pos=match.start(),
                    end_pos=match.end(),
                    confidence=0.9
                ))
        
        return entities
    
    def _extract_regions(self, query: str) -> List[TyphoonEntity]:
        """提取区域"""
        entities = []
        
        regions = ["华南", "华东", "华北", "东北", "华中", "西南", "东南沿海"]
        for region in regions:
            if region in query:
                pos = query.find(region)
                entities.append(TyphoonEntity(
                    entity_type=TyphoonEntityType.REGION,
                    value=region,
                    start_pos=pos,
                    end_pos=pos + len(region),
                    confidence=0.85
                ))
        
        return entities
    
    def _extract_intent_attributes(self, intent_type: TyphoonIntentType, query: str) -> List[str]:
        """提取意图相关的属性"""
        attributes = []
        
        attribute_mapping = {
            TyphoonIntentType.INTENSITY_QUERY: ["max_wind_speed", "min_pressure", "peak_intensity"],
            TyphoonIntentType.TIME_QUERY: ["start_time", "end_time", "duration_hours"],
            TyphoonIntentType.PATH_QUERY: ["start_lat", "start_lon", "end_lat", "end_lon", "total_distance_km"],
            TyphoonIntentType.LANDFALL_QUERY: ["landfall_count", "landed_at", "land_time"],
            TyphoonIntentType.IMPACT_QUERY: ["affected_area", "damage", "casualties"],
        }
        
        return attribute_mapping.get(intent_type, [])
    
    def analyze(self, query: str) -> TyphoonQueryAnalysis:
        """
        综合分析查询
        
        Args:
            query: 用户查询
            
        Returns:
            TyphoonQueryAnalysis: 完整的查询分析结果
        """
        # 识别意图
        intent = self.recognize_intent(query)
        
        # 提取实体
        entities = self.extract_entities(query)
        
        # 确定查询类型
        query_type = self._determine_query_type(entities, intent)
        
        # 提取时间和空间上下文
        temporal_context = self._extract_temporal_context(entities, query)
        spatial_context = self._extract_spatial_context(entities, query)
        
        return TyphoonQueryAnalysis(
            original_query=query,
            intent=intent,
            entities=entities,
            query_type=query_type,
            temporal_context=temporal_context,
            spatial_context=spatial_context
        )
    
    def _determine_query_type(self, entities: List[TyphoonEntity], intent: TyphoonIntent) -> str:
        """确定查询类型"""
        typhoon_names = [e for e in entities if e.entity_type == TyphoonEntityType.TYPHOON_NAME]
        years = [e for e in entities if e.entity_type == TyphoonEntityType.YEAR]
        
        # 对比查询
        if intent.intent_type == TyphoonIntentType.COMPARISON_QUERY:
            return "comparison"
        
        # 多个台风名称
        if len(typhoon_names) >= 2:
            return "multi_typhoon"
        
        # 年份查询（没有具体台风名称）
        if len(years) > 0 and len(typhoon_names) == 0:
            return "year_overview"
        
        # 单个台风查询
        if len(typhoon_names) == 1:
            return "single_typhoon"
        
        return "general"
    
    def _extract_temporal_context(self, entities: List[TyphoonEntity], query: str) -> Dict:
        """提取时间上下文"""
        context = {}
        
        years = [e for e in entities if e.entity_type == TyphoonEntityType.YEAR]
        months = [e for e in entities if e.entity_type == TyphoonEntityType.MONTH]
        dates = [e for e in entities if e.entity_type == TyphoonEntityType.DATE]
        
        if years:
            context["years"] = [e.normalized_value for e in years]
        if months:
            context["months"] = [e.normalized_value for e in months]
        if dates:
            context["dates"] = [e.value for e in dates]
        
        # 检测时间范围
        if "最近" in query or "近年" in query or "最新" in query:
            context["recent"] = True
        if "历史上" in query or "有史以来" in query:
            context["historical"] = True
        
        return context
    
    def _extract_spatial_context(self, entities: List[TyphoonEntity], query: str) -> Dict:
        """提取空间上下文"""
        context = {}
        
        locations = [e for e in entities if e.entity_type == TyphoonEntityType.LOCATION]
        regions = [e for e in entities if e.entity_type == TyphoonEntityType.REGION]
        
        if locations:
            context["locations"] = [e.normalized_value for e in locations]
        if regions:
            context["regions"] = [e.value for e in regions]
        
        # 检测空间关系
        if "附近" in query or "周边" in query:
            context["nearby"] = True
        if "经过" in query or "路过" in query:
            context["passed_through"] = True
        if "登陆" in query:
            context["landfall"] = True
        
        return context


# 全局实例
intent_recognizer = TyphoonIntentRecognizer()
