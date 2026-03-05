"""
动态Prompt构建模块
根据不同类型的台风问题动态生成针对性的检索指令
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .typhoon_intent_recognizer import (
    TyphoonIntentType, 
    TyphoonQueryAnalysis,
    TyphoonEntityType
)


class PromptType(str, Enum):
    """Prompt类型"""
    BASIC_INFO = "basic_info"
    PATH_ANALYSIS = "path_analysis"
    INTENSITY_ANALYSIS = "intensity_analysis"
    TIME_ANALYSIS = "time_analysis"
    LANDFALL_ANALYSIS = "landfall_analysis"
    IMPACT_ANALYSIS = "impact_analysis"
    PREDICTION = "prediction"
    COMPARISON = "comparison"
    STATISTICS = "statistics"
    DEFENSE_GUIDE = "defense_guide"
    GENERAL = "general"


@dataclass
class RetrievalInstruction:
    """检索指令"""
    primary_keywords: List[str]
    secondary_keywords: List[str]
    required_relations: List[str]
    priority_attributes: List[str]
    query_expansion: List[str]
    result_format: str


@dataclass
class PromptTemplate:
    """Prompt模板"""
    system_prompt: str
    instruction_template: str
    example_format: str
    constraints: List[str]


class TyphoonPromptBuilder:
    """台风领域Prompt构建器"""
    
    # 基础系统提示词
    BASE_SYSTEM_PROMPT = """你是台风气象领域的专业AI助手，具备丰富的台风知识和分析能力。

【核心能力】
- 台风基本信息解读：名称、编号、年份、生命周期等
- 路径分析：移动轨迹、转折点、登陆点、影响范围
- 强度评估：风速、气压、等级变化、巅峰强度
- 影响评估：受灾区域、经济损失、人员伤亡
- 预测分析：路径预测、强度变化、预警建议
- 历史对比：相似台风、同期对比、排名统计
- 防灾指导：防御措施、应急准备、避险建议

【回答要求】
1. 基于知识图谱数据给出准确、专业的回答
2. 使用具体数据支撑（风速、气压、时间、地点等）
3. 结构清晰，层次分明，重点突出
4. 对于不确定的信息，明确说明数据限制
5. 涉及多个实体时，分别详细说明
"""

    # 意图到Prompt类型的映射
    INTENT_PROMPT_MAPPING = {
        TyphoonIntentType.BASIC_INFO: PromptType.BASIC_INFO,
        TyphoonIntentType.PATH_QUERY: PromptType.PATH_ANALYSIS,
        TyphoonIntentType.INTENSITY_QUERY: PromptType.INTENSITY_ANALYSIS,
        TyphoonIntentType.TIME_QUERY: PromptType.TIME_ANALYSIS,
        TyphoonIntentType.LANDFALL_QUERY: PromptType.LANDFALL_ANALYSIS,
        TyphoonIntentType.IMPACT_QUERY: PromptType.IMPACT_ANALYSIS,
        TyphoonIntentType.AFFECTED_AREA_QUERY: PromptType.IMPACT_ANALYSIS,
        TyphoonIntentType.PREDICTION_QUERY: PromptType.PREDICTION,
        TyphoonIntentType.COMPARISON_QUERY: PromptType.COMPARISON,
        TyphoonIntentType.SIMILAR_QUERY: PromptType.COMPARISON,
        TyphoonIntentType.STATISTICS_QUERY: PromptType.STATISTICS,
        TyphoonIntentType.RANKING_QUERY: PromptType.STATISTICS,
        TyphoonIntentType.DEFENSE_QUERY: PromptType.DEFENSE_GUIDE,
        TyphoonIntentType.PREVENTION_QUERY: PromptType.DEFENSE_GUIDE,
        TyphoonIntentType.UNKNOWN: PromptType.GENERAL,
    }

    # Prompt模板定义
    PROMPT_TEMPLATES = {
        PromptType.BASIC_INFO: PromptTemplate(
            system_prompt="""你正在回答关于台风基本信息的查询。请提供准确、完整的台风基础数据，包括：
- 台风名称（中文、英文）
- 台风编号（格式：YYYYMM）
- 发生年份
- 生成和消散时间
- 持续时间
- 基本信息统计

请确保数据准确，格式规范。""",
            instruction_template="""请基于以下知识图谱数据，回答关于{typhoon_name}的基本信息：

【检索数据】
{graph_context}

【回答要点】
1. 台风名称和编号
2. 发生年份和时间范围
3. 生成和消散地点
4. 持续时间
5. 其他基本信息

请用清晰的格式呈现以上信息。""",
            example_format="""
示例回答格式：
台风{typhoon_name}（编号：{typhoon_id}）的基本信息如下：

1. 基本信息
   - 中文名称：{name_cn}
   - 英文名称：{name_en}
   - 台风编号：{typhoon_id}
   - 发生年份：{year}年

2. 时间信息
   - 生成时间：{start_time}
   - 消散时间：{end_time}
   - 持续时间：{duration}

3. 位置信息
   - 生成地点：{genesis_location}
   - 消散地点：{dissipation_location}
""",
            constraints=["数据必须准确", "时间格式统一", "包含所有关键字段"]
        ),
        
        PromptType.PATH_ANALYSIS: PromptTemplate(
            system_prompt="""你正在分析台风的移动路径。请详细描述：
- 起点和终点的位置
- 移动方向和速度变化
- 关键转折点
- 经过的主要区域
- 路径特征（直线型、抛物线型、回旋型等）

请结合地理知识进行专业分析。""",
            instruction_template="""请基于以下知识图谱数据，详细分析{typhoon_name}的移动路径：

【检索数据】
{graph_context}

【分析要点】
1. 路径整体描述（起点→终点）
2. 移动方向和速度变化
3. 关键转折点分析
4. 经过的主要区域
5. 路径特征总结
6. 与典型路径的对比（如有数据）

请提供详细的路径分析。""",
            example_format="""
示例回答格式：
台风{typhoon_name}的路径特征分析：

1. 路径概况
   - 起点：{start_point}（{start_time}）
   - 终点：{end_point}（{end_time}）
   - 总路径长度：约{distance}公里

2. 移动特征
   - 主要移动方向：{main_direction}
   - 平均移动速度：{avg_speed} km/h
   - 速度变化：{speed_change_description}

3. 关键转折点
   - 转折点1：{turning_point_1}
   - 转折点2：{turning_point_2}

4. 经过区域
   - 主要影响：{affected_regions}
""",
            constraints=["描述路径转折点", "说明移动速度变化", "列出经过的主要区域"]
        ),
        
        PromptType.INTENSITY_ANALYSIS: PromptTemplate(
            system_prompt="""你正在分析台风的强度变化。请详细说明：
- 巅峰强度（最大风速、最低气压）
- 强度等级变化历程
- 增强和减弱阶段
- 影响强度的环境因素
- 与历史台风的强度对比

请使用专业术语和数据进行分析。""",
            instruction_template="""请基于以下知识图谱数据，详细分析{typhoon_name}的强度变化：

【检索数据】
{graph_context}

【分析要点】
1. 巅峰强度数据
2. 强度等级变化历程
3. 增强阶段分析
4. 减弱阶段分析
5. 强度变化原因分析
6. 历史对比（如适用）

请提供详细的强度演变分析。""",
            example_format="""
示例回答格式：
台风{typhoon_name}的强度演变分析：

1. 巅峰强度
   - 最大风速：{max_wind_speed} m/s（{wind_level}级）
   - 最低气压：{min_pressure} hPa
   - 巅峰强度等级：{peak_intensity}
   - 出现时间：{peak_time}

2. 强度变化历程
   - 生成时：{initial_intensity}
   - 增强期：{intensification_period}
   - 巅峰期：{peak_period}
   - 减弱期：{weakening_period}

3. 强度等级变化
   {intensity_change_timeline}

4. 影响因素
   - 海表温度：{sst_info}
   - 垂直风切变：{wind_shear_info}
""",
            constraints=["提供具体风速和气压数据", "描述强度等级变化", "分析影响因素"]
        ),
        
        PromptType.TIME_ANALYSIS: PromptTemplate(
            system_prompt="""你正在分析台风的时间特征。请详细说明：
- 生成时间和消散时间
- 持续时间
- 生命周期各阶段的时间分布
- 活跃时段特征
- 与台风季节的关系

请准确描述时间信息。""",
            instruction_template="""请基于以下知识图谱数据，详细分析{typhoon_name}的时间特征：

【检索数据】
{graph_context}

【分析要点】
1. 生成和消散时间
2. 持续时间统计
3. 生命周期各阶段时长
4. 活跃时段特征
5. 台风季节背景

请提供详细的时间分析。""",
            example_format="""
示例回答格式：
台风{typhoon_name}的时间特征：

1. 时间范围
   - 生成时间：{start_time}
   - 消散时间：{end_time}
   - 持续时间：{duration}

2. 生命周期阶段
   - 生成阶段：{genesis_duration}
   - 发展阶段：{development_duration}
   - 成熟阶段：{mature_duration}
   - 衰减阶段：{decay_duration}

3. 时间特征
   - 活跃月份：{active_month}
   - 台风季节位置：{season_position}
""",
            constraints=["时间格式统一", "计算持续时间", "分析生命周期阶段"]
        ),
        
        PromptType.LANDFALL_ANALYSIS: PromptTemplate(
            system_prompt="""你正在分析台风的登陆情况。请详细说明：
- 登陆地点（省份、城市）
- 登陆时间
- 登陆强度
- 登陆次数
- 登陆后的强度变化
- 登陆影响评估

请提供准确的登陆信息。""",
            instruction_template="""请基于以下知识图谱数据，详细分析{typhoon_name}的登陆情况：

【检索数据】
{graph_context}

【分析要点】
1. 登陆地点和时间
2. 登陆强度
3. 登陆次数
4. 登陆后的路径和强度变化
5. 登陆影响评估

请提供详细的登陆分析。""",
            example_format="""
示例回答格式：
台风{typhoon_name}的登陆情况：

1. 登陆信息
   - 登陆地点：{landfall_location}
   - 登陆时间：{landfall_time}
   - 登陆强度：{landfall_intensity}
   - 登陆时风速：{landfall_wind_speed} m/s

2. 登陆影响
   - 登陆时气压：{landfall_pressure} hPa
   - 登陆后强度变化：{intensity_change}
   - 二次登陆（如有）：{second_landfall}

3. 登陆特征
   - 登陆次数：{landfall_count}
   - 登陆类型：{landfall_type}
""",
            constraints=["明确登陆地点", "提供登陆时间和强度", "说明登陆次数"]
        ),
        
        PromptType.IMPACT_ANALYSIS: PromptTemplate(
            system_prompt="""你正在分析台风的影响和灾害情况。请详细说明：
- 影响区域范围
- 受灾人口
- 经济损失
- 人员伤亡
- 基础设施损坏
- 次生灾害

请提供全面的影响评估。""",
            instruction_template="""请基于以下知识图谱数据，详细分析{typhoon_name}的影响和灾害情况：

【检索数据】
{graph_context}

【分析要点】
1. 影响区域和范围
2. 受灾人口统计
3. 经济损失评估
4. 人员伤亡情况
5. 基础设施影响
6. 次生灾害
7. 灾害特点总结

请提供详细的影响评估。""",
            example_format="""
示例回答格式：
台风{typhoon_name}的影响评估：

1. 影响范围
   - 主要影响区域：{affected_regions}
   - 影响面积：约{affected_area}万平方公里
   - 受灾人口：约{affected_population}万人

2. 经济损失
   - 直接经济损失：{direct_loss}亿元
   - 间接经济损失：{indirect_loss}亿元
   - 主要损失类型：{loss_types}

3. 人员伤亡
   - 死亡人数：{deaths}人
   - 失踪人数：{missing}人
   - 受伤人数：{injured}人

4. 灾害影响
   - 房屋损毁：{damaged_houses}
   - 农作物受灾：{damaged_crops}
   - 基础设施：{infrastructure_damage}
""",
            constraints=["量化影响范围", "统计经济损失", "说明人员伤亡"]
        ),
        
        PromptType.PREDICTION: PromptTemplate(
            system_prompt="""你正在提供台风预测分析。请说明：
- 当前状态分析
- 未来路径预测
- 强度变化预测
- 可能影响区域
- 预警建议

请注意预测的不确定性。""",
            instruction_template="""请基于以下知识图谱数据和历史模式，提供{typhoon_name}的预测分析：

【检索数据】
{graph_context}

【预测要点】
1. 当前状态分析
2. 未来路径预测（6h, 24h, 48h, 72h）
3. 强度变化预测
4. 可能影响区域
5. 预警等级建议
6. 防御建议

请注意：预测具有不确定性，请基于历史相似台风的模式进行分析。""",
            example_format="""
示例回答格式：
台风{typhoon_name}预测分析：

1. 当前状态（{current_time}）
   - 位置：{current_position}
   - 强度：{current_intensity}
   - 移动：{current_movement}

2. 路径预测
   - 6小时：{forecast_6h}
   - 24小时：{forecast_24h}
   - 48小时：{forecast_48h}
   - 72小时：{forecast_72h}

3. 强度预测
   - 预计巅峰：{predicted_peak}
   - 变化趋势：{intensity_trend}

4. 预警建议
   - 重点防御区域：{priority_areas}
   - 建议预警等级：{warning_level}
""",
            constraints=["说明预测不确定性", "分时段预测", "提供预警建议"]
        ),
        
        PromptType.COMPARISON: PromptTemplate(
            system_prompt="""你正在进行台风对比分析。请详细比较：
- 强度对比
- 路径对比
- 影响范围对比
- 时间特征对比
- 灾害程度对比

请提供清晰的对比表格和分析。""",
            instruction_template="""请基于以下知识图谱数据，对比分析{typhoon_names}：

【检索数据】
{graph_context}

【对比要点】
1. 基本信息对比
2. 强度对比
3. 路径特征对比
4. 影响范围对比
5. 灾害程度对比
6. 综合评估

请提供详细的对比分析，使用表格展示关键数据对比。""",
            example_format="""
示例回答格式：
台风对比分析：{typhoon_names}

1. 基本信息对比
   | 项目 | {typhoon_1} | {typhoon_2} |
   |------|-------------|-------------|
   | 编号 | {id_1} | {id_2} |
   | 年份 | {year_1} | {year_2} |
   | 持续时间 | {duration_1} | {duration_2} |

2. 强度对比
   | 项目 | {typhoon_1} | {typhoon_2} |
   |------|-------------|-------------|
   | 最大风速 | {wind_1} | {wind_2} |
   | 最低气压 | {pressure_1} | {pressure_2} |
   | 巅峰等级 | {intensity_1} | {intensity_2} |

3. 对比结论
   - 强度对比：{intensity_comparison}
   - 影响对比：{impact_comparison}
""",
            constraints=["使用表格对比", "量化对比指标", "给出明确结论"]
        ),
        
        PromptType.STATISTICS: PromptTemplate(
            system_prompt="""你正在提供台风统计信息。请详细说明：
- 统计范围和时间
- 统计指标
- 排名情况
- 历史对比
- 趋势分析

请提供准确的统计数据。""",
            instruction_template="""请基于以下知识图谱数据，提供{statistic_subject}的统计信息：

【检索数据】
{graph_context}

【统计要点】
1. 统计范围说明
2. 关键统计数据
3. 排名情况
4. 历史对比
5. 特征分析

请提供详细的统计分析。""",
            example_format="""
示例回答格式：
{statistic_subject}统计：

1. 统计概况
   - 统计范围：{statistic_scope}
   - 统计时间：{statistic_period}
   - 样本数量：{sample_count}

2. 关键数据
   - 总数：{total_count}
   - 平均值：{average_value}
   - 极值：{extreme_values}

3. 排名情况
   - 前10名：{top_10_list}
   - 排名变化：{ranking_changes}

4. 特征分析
   - 时间分布：{temporal_distribution}
   - 空间分布：{spatial_distribution}
""",
            constraints=["提供准确统计数据", "说明统计范围", "给出排名列表"]
        ),
        
        PromptType.DEFENSE_GUIDE: PromptTemplate(
            system_prompt="""你正在提供台风防御指导。请详细说明：
- 预警等级和含义
- 防御措施
- 应急准备
- 避险指南
- 注意事项

请提供实用的防御建议。""",
            instruction_template="""请基于台风{typhoon_name}的情况，提供防御指导：

【台风信息】
{graph_context}

【防御要点】
1. 预警等级说明
2. 人员转移建议
3. 物资准备清单
4. 居家防御措施
5. 户外避险指南
6. 特殊人群注意事项

请提供详细的防御指导。""",
            example_format="""
示例回答格式：
台风{typhoon_name}防御指南：

1. 预警信息
   - 当前预警等级：{warning_level}
   - 预计影响时间：{expected_impact_time}
   - 重点防御区域：{priority_areas}

2. 人员转移
   - 转移时间：{evacuation_time}
   - 转移路线：{evacuation_routes}
   - 安置地点：{shelter_locations}

3. 物资准备
   - 食品饮水：3-5天用量
   - 应急用品：手电筒、收音机、充电宝
   - 医疗用品：急救包、常用药品
   - 防护用具：雨衣、雨靴、安全帽

4. 防御措施
   - 居家：加固门窗、清理阳台
   - 户外：远离广告牌、大树、电线杆
   - 车辆：移至高处、远离低洼地带

5. 避险要点
   - 台风期间避免外出
   - 远离危险区域
   - 保持通讯畅通
   - 关注官方信息
""",
            constraints=["预警等级明确", "措施具体可行", "覆盖不同场景"]
        ),
        
        PromptType.GENERAL: PromptTemplate(
            system_prompt="""你是台风气象领域的专业AI助手。请基于知识图谱数据，回答用户关于台风的问题。

请确保回答：
- 准确可靠
- 结构清晰
- 数据充分
- 专业易懂""",
            instruction_template="""请基于以下知识图谱数据，回答用户问题：

【用户问题】
{question}

【检索数据】
{graph_context}

请提供详细、专业的回答。""",
            example_format="",
            constraints=["回答准确", "结构清晰", "基于数据"]
        ),
    }

    def __init__(self):
        pass

    def build_prompt(
        self, 
        query_analysis: TyphoonQueryAnalysis, 
        graph_context: str,
        additional_context: Optional[Dict] = None
    ) -> Dict[str, str]:
        """
        构建完整的Prompt
        
        Args:
            query_analysis: 查询分析结果
            graph_context: 知识图谱检索上下文
            additional_context: 额外上下文
            
        Returns:
            Dict[str, str]: 包含system_prompt和user_prompt的字典
        """
        # 确定Prompt类型
        prompt_type = self._determine_prompt_type(query_analysis)
        
        # 获取模板
        template = self.PROMPT_TEMPLATES.get(prompt_type, self.PROMPT_TEMPLATES[PromptType.GENERAL])
        
        # 构建检索指令
        retrieval_instruction = self._build_retrieval_instruction(query_analysis)
        
        # 填充模板
        user_prompt = self._fill_template(
            template, 
            query_analysis, 
            graph_context,
            additional_context
        )
        
        # 组合系统提示词
        system_prompt = f"{self.BASE_SYSTEM_PROMPT}\n\n{template.system_prompt}"
        
        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "prompt_type": prompt_type.value,
            "retrieval_instruction": retrieval_instruction
        }

    def _determine_prompt_type(self, query_analysis: TyphoonQueryAnalysis) -> PromptType:
        """确定Prompt类型"""
        intent_type = query_analysis.intent.intent_type
        return self.INTENT_PROMPT_MAPPING.get(intent_type, PromptType.GENERAL)

    def _build_retrieval_instruction(self, query_analysis: TyphoonQueryAnalysis) -> RetrievalInstruction:
        """构建检索指令"""
        intent_type = query_analysis.intent.intent_type
        entities = query_analysis.entities
        
        # 根据意图确定检索关键词
        primary_keywords = []
        secondary_keywords = []
        required_relations = []
        priority_attributes = []
        query_expansion = []
        
        # 提取台风名称
        typhoon_names = [e.value for e in entities if e.entity_type == TyphoonEntityType.TYPHOON_NAME]
        if typhoon_names:
            primary_keywords.extend(typhoon_names)
        
        # 根据意图配置检索参数
        intent_config = {
            TyphoonIntentType.BASIC_INFO: {
                "relations": ["OCCURRED_IN", "GENERATED_AT", "DISSIPATED_AT"],
                "attributes": ["name_cn", "name_en", "typhoon_id", "year", "start_time", "end_time", "duration_hours"],
                "expansion": ["基本信息", "概况", "简介"]
            },
            TyphoonIntentType.PATH_QUERY: {
                "relations": ["HAS_PATH_POINT", "NEXT", "LANDED_AT", "AFFECTED_AREA"],
                "attributes": ["lat", "lon", "moving_speed", "moving_direction", "distance_from_genesis"],
                "expansion": ["路径", "轨迹", "移动路线", "经过"]
            },
            TyphoonIntentType.INTENSITY_QUERY: {
                "relations": ["INTENSIFIED_TO", "WEAKENED_TO", "HAS_INTENSITY"],
                "attributes": ["max_wind_speed", "min_pressure", "peak_intensity", "wind_speed", "pressure"],
                "expansion": ["强度", "风速", "气压", "等级"]
            },
            TyphoonIntentType.TIME_QUERY: {
                "relations": ["OCCURRED_IN", "GENERATED_AT", "DISSIPATED_AT"],
                "attributes": ["start_time", "end_time", "duration_hours", "timestamp"],
                "expansion": ["时间", "生成", "消散", "持续"]
            },
            TyphoonIntentType.LANDFALL_QUERY: {
                "relations": ["LANDED_AT", "AFFECTED_AREA"],
                "attributes": ["land_time", "land_intensity", "landfall_count"],
                "expansion": ["登陆", "上岸", "登陆点", "登陆时间"]
            },
            TyphoonIntentType.IMPACT_QUERY: {
                "relations": ["AFFECTED_AREA", "LANDED_AT"],
                "attributes": ["affected_area", "damage", "casualties", "economic_loss"],
                "expansion": ["影响", "灾害", "损失", "受灾"]
            },
            TyphoonIntentType.PREDICTION_QUERY: {
                "relations": ["HAS_PATH_POINT", "SIMILAR_TO"],
                "attributes": ["current_position", "current_intensity", "moving_direction", "moving_speed"],
                "expansion": ["预测", "预报", "未来", "趋势"]
            },
            TyphoonIntentType.COMPARISON_QUERY: {
                "relations": ["SIMILAR_TO", "HAS_PATH_POINT", "INTENSIFIED_TO", "WEAKENED_TO"],
                "attributes": ["max_wind_speed", "min_pressure", "duration_hours", "total_distance_km"],
                "expansion": ["对比", "比较", "相似", "差异"]
            },
            TyphoonIntentType.STATISTICS_QUERY: {
                "relations": ["OCCURRED_IN", "LANDED_AT", "INTENSIFIED_TO", "WEAKENED_TO"],
                "attributes": ["year", "max_wind_speed", "landfall_count", "total_typhoons"],
                "expansion": ["统计", "数量", "排名", "历史"]
            },
            TyphoonIntentType.DEFENSE_QUERY: {
                "relations": ["AFFECTED_AREA", "LANDED_AT"],
                "attributes": ["intensity", "wind_speed", "affected_area"],
                "expansion": ["防御", "防范", "措施", "建议"]
            },
        }
        
        config = intent_config.get(intent_type, {})
        
        return RetrievalInstruction(
            primary_keywords=primary_keywords,
            secondary_keywords=secondary_keywords,
            required_relations=config.get("relations", []),
            priority_attributes=config.get("attributes", []),
            query_expansion=config.get("expansion", []),
            result_format="structured"
        )

    def _fill_template(
        self, 
        template: PromptTemplate,
        query_analysis: TyphoonQueryAnalysis,
        graph_context: str,
        additional_context: Optional[Dict] = None
    ) -> str:
        """填充模板"""
        # 获取台风名称
        typhoon_names = [e.value for e in query_analysis.entities if e.entity_type == TyphoonEntityType.TYPHOON_NAME]
        typhoon_name = typhoon_names[0] if typhoon_names else "该台风"
        
        # 构建填充数据 - 包含所有可能用到的变量
        fill_data = {
            "typhoon_name": typhoon_name,
            "typhoon_names": "、".join(typhoon_names) if len(typhoon_names) > 1 else typhoon_name,
            "graph_context": graph_context,
            "question": query_analysis.original_query,
            "statistic_subject": self._get_statistic_subject(query_analysis),
            # 示例格式中可能用到的占位符
            "typhoon_id": "",
            "name_cn": typhoon_name,
            "name_en": "",
            "year": "",
            "start_time": "",
            "end_time": "",
            "duration": "",
            "genesis_location": "",
            "dissipation_location": "",
            "start_point": "",
            "end_point": "",
            "distance": "",
            "main_direction": "",
            "avg_speed": "",
            "speed_change_description": "",
            "turning_point_1": "",
            "turning_point_2": "",
            "affected_regions": "",
            "max_wind_speed": "",
            "min_pressure": "",
            "peak_intensity": "",
            "peak_time": "",
            "initial_intensity": "",
            "intensification_period": "",
            "peak_period": "",
            "weakening_period": "",
            "intensity_change_timeline": "",
            "sst_info": "",
            "wind_shear_info": "",
            "landfall_location": "",
            "landfall_time": "",
            "landfall_intensity": "",
            "landfall_wind_speed": "",
            "landfall_pressure": "",
            "intensity_change": "",
            "second_landfall": "",
            "landfall_count": "",
            "landfall_type": "",
            "affected_area": "",
            "affected_population": "",
            "direct_loss": "",
            "indirect_loss": "",
            "loss_types": "",
            "deaths": "",
            "missing": "",
            "injured": "",
            "damaged_houses": "",
            "damaged_crops": "",
            "infrastructure_damage": "",
            "current_time": "",
            "current_position": "",
            "current_intensity": "",
            "current_movement": "",
            "forecast_6h": "",
            "forecast_24h": "",
            "forecast_48h": "",
            "forecast_72h": "",
            "predicted_peak": "",
            "intensity_trend": "",
            "priority_areas": "",
            "warning_level": "",
            "typhoon_1": typhoon_name,
            "typhoon_2": typhoon_names[1] if len(typhoon_names) > 1 else "",
            "id_1": "",
            "id_2": "",
            "year_1": "",
            "year_2": "",
            "duration_1": "",
            "duration_2": "",
            "wind_1": "",
            "wind_2": "",
            "pressure_1": "",
            "pressure_2": "",
            "intensity_1": "",
            "intensity_2": "",
            "intensity_comparison": "",
            "impact_comparison": "",
            "statistic_scope": "",
            "statistic_period": "",
            "sample_count": "",
            "total_count": "",
            "average_value": "",
            "extreme_values": "",
            "top_10_list": "",
            "ranking_changes": "",
            "temporal_distribution": "",
            "spatial_distribution": "",
            "expected_impact_time": "",
            "priority_areas": "",
            "evacuation_time": "",
            "evacuation_routes": "",
            "shelter_locations": "",
        }
        
        # 添加额外上下文
        if additional_context:
            fill_data.update(additional_context)
        
        # 填充模板
        try:
            user_prompt = template.instruction_template.format(**fill_data)
        except KeyError:
            user_prompt = template.instruction_template
        
        # 添加示例格式（如果有）- 安全填充
        if template.example_format:
            try:
                example_text = template.example_format.format(**fill_data)
                user_prompt += f"\n\n{example_text}"
            except KeyError:
                pass
        
        # 添加约束条件
        if template.constraints:
            user_prompt += "\n\n【约束条件】\n"
            for i, constraint in enumerate(template.constraints, 1):
                user_prompt += f"{i}. {constraint}\n"
        
        return user_prompt

    def _get_statistic_subject(self, query_analysis: TyphoonQueryAnalysis) -> str:
        """获取统计主题"""
        # 从查询中提取统计主题
        years = [e.value for e in query_analysis.entities if e.entity_type == TyphoonEntityType.YEAR]
        if years:
            return f"{years[0]}年台风"
        
        if "最强" in query_analysis.original_query:
            return "最强台风"
        if "登陆" in query_analysis.original_query:
            return "登陆台风"
        
        return "台风"

    def build_graph_query_hint(self, query_analysis: TyphoonQueryAnalysis) -> Dict[str, Any]:
        """
        构建知识图谱查询提示
        
        Args:
            query_analysis: 查询分析结果
            
        Returns:
            Dict[str, Any]: 查询提示信息
        """
        hint = {
            "intent": query_analysis.intent.intent_type.value,
            "confidence": query_analysis.intent.confidence,
            "query_type": query_analysis.query_type,
            "focus_entities": [],
            "required_relations": [],
            "priority_attributes": [],
            "traversal_depth": 2,
            "max_nodes": 50,
        }
        
        # 提取关注的实体
        for entity in query_analysis.entities:
            hint["focus_entities"].append({
                "type": entity.entity_type.value,
                "value": entity.value,
                "confidence": entity.confidence
            })
        
        # 根据意图确定遍历深度和节点数
        if query_analysis.intent.intent_type == TyphoonIntentType.PATH_QUERY:
            hint["traversal_depth"] = 3
            hint["max_nodes"] = 100  # 路径查询需要更多节点
            hint["required_relations"] = ["HAS_PATH_POINT", "NEXT"]
        elif query_analysis.intent.intent_type == TyphoonIntentType.COMPARISON_QUERY:
            hint["traversal_depth"] = 2
            hint["max_nodes"] = 80  # 对比查询需要多个台风的信息
        elif query_analysis.intent.intent_type == TyphoonIntentType.STATISTICS_QUERY:
            hint["traversal_depth"] = 1
            hint["max_nodes"] = 150  # 统计查询需要大量节点
        
        # 获取检索指令
        retrieval_instruction = self._build_retrieval_instruction(query_analysis)
        hint["required_relations"] = retrieval_instruction.required_relations
        hint["priority_attributes"] = retrieval_instruction.priority_attributes
        
        return hint


# 全局实例
prompt_builder = TyphoonPromptBuilder()
