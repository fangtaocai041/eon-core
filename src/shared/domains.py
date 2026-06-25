"""
senses/domains.py — 多学科领域感受器 (11 个领域)

每个领域感受器:
  1. 内置学科核心概念知识图谱
  2. 关键思想家/著作目录
  3. MCP 工具注入接口 (连接外部知识库)
  4. 遵循 SenseInput → SenseOutput 统一协议

领域列表:
  math        — 数学        (代数/几何/分析/拓扑/数论)
  physics     — 物理        (经典/量子/相对论/热力学)
  chemistry   — 化学        (有机/无机/物理化学/生化)
  biology     — 生物学      (分子/细胞/进化/生态)
  cs          — 计算机科学  (算法/系统/AI/理论)
  psychology  — 心理学      (认知/行为/发展/神经)
  philosophy  — 哲学        (形而上学/认识论/伦理/逻辑)
  marxism     — 马克思主义  (辩证唯物/历史唯物/政治经济)
  economics   — 经济学      (微观/宏观/制度/行为)
  literature  — 文学        (中外文学史/理论/批评)
  scifi       — 科幻        (科幻史/主题/思想家)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
import time


# ── 统一输出协议 ──

@dataclass
class DomainOutput:
    """领域感受器统一输出。"""
    domain: str = ""
    query: str = ""
    concepts_found: List[Dict[str, str]] = field(default_factory=list)
    thinkers: List[Dict[str, str]] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    error: Optional[str] = None


# ── 领域知识条目 ──

@dataclass
class KnowledgeEntry:
    """一条领域知识。"""
    concept: str
    definition: str
    category: str = ""
    related: List[str] = field(default_factory=list)


# ── 基类 ──

class DomainSense:
    """领域感受器基类。

    子类只需定义:
      domain       — 领域名称 (如 "mathematics")
      concepts     — List[KnowledgeEntry] 核心概念
      thinkers     — List[Dict] 关键思想家 [{name, works, contribution}]
      search_fn    — 可选 MCP 搜索工具注入
    """

    domain: str = ""
    concepts: List[KnowledgeEntry] = field(default_factory=list)  # type: ignore
    thinkers: List[Dict[str, str]] = field(default_factory=list)  # type: ignore
    aliases: List[str] = field(default_factory=list)  # type: ignore

    def __init__(self, search_fn: Optional[Callable] = None):
        self._search = search_fn
        self._concept_map: Dict[str, KnowledgeEntry] = {}
        for c in self.concepts:
            self._concept_map[c.concept.lower()] = c
            for r in c.related:
                self._concept_map[r.lower()] = c

    @property
    def is_wired(self) -> bool:
        return self._search is not None

    def search(self, query: str, **kwargs) -> dict:
        """搜索领域知识。"""
        t0 = time.time()
        q = query.lower()

        # 1. 本地知识图谱匹配
        concepts_found = []
        for key, entry in self._concept_map.items():
            if key in q or any(r in q for r in entry.related):
                concepts_found.append({
                    "concept": entry.concept,
                    "definition": entry.definition[:200],
                    "category": entry.category,
                })
                if len(concepts_found) >= 5:
                    break

        # 2. 关键思想家匹配
        thinkers_found = []
        for t in self.thinkers:
            name = t.get("name", "").lower()
            if name and name in q:
                thinkers_found.append(t)
                if len(thinkers_found) >= 3:
                    break

        # 3. 外部 MCP 查询
        external = ""
        if self._search:
            try:
                ext = self._search(q, max_results=3)
                if isinstance(ext, dict):
                    external = str(ext.get("results", ext.get("papers", [])))[:200]
            except Exception as e:
                external = f"error: {e}"

        return {
            "status": "ok",
            "domain": self.domain,
            "query": query,
            "concepts_found": concepts_found,
            "thinkers_found": thinkers_found,
            "local_match": len(concepts_found) > 0,
            "duration_ms": round((time.time() - t0) * 1000, 1),
        }


# ═══════════════════════════════════════════════════════════════
# 1. 数学
# ═══════════════════════════════════════════════════════════════

class MathSense(DomainSense):
    domain = "mathematics"
    aliases = ["math", "数学", "代数", "几何", "分析", "拓扑"]
    concepts = [
        KnowledgeEntry("微积分", "研究变化率和累积量的数学分支", "分析", ["calculus", "导数", "积分", "极限"]),
        KnowledgeEntry("线性代数", "研究向量空间和线性映射的代数分支", "代数", ["矩阵", "向量", "特征值"]),
        KnowledgeEntry("群论", "研究对称性的代数结构理论", "代数", ["对称", "群", "环", "域"]),
        KnowledgeEntry("拓扑学", "研究连续性和连通性的数学分支", "几何", ["拓扑空间", "同伦", "同调"]),
        KnowledgeEntry("数论", "研究整数性质的数学分支", "数论", ["素数", "同余", "丢番图"]),
        KnowledgeEntry("概率论", "研究随机现象数学规律的学科", "分析", ["概率", "统计", "随机"]),
        KnowledgeEntry("集合论", "研究集合作为数学基础的学科", "基础", ["集合", "基数", "公理"]),
        KnowledgeEntry("范畴论", "研究数学结构之间关系的抽象理论", "基础", ["范畴", "函子", "自然变换"]),
        KnowledgeEntry("微分方程", "描述函数及其导数关系的方程", "分析", ["ODE", "PDE", "动力系统"]),
        KnowledgeEntry("博弈论", "研究策略互动的数学模型", "应用", ["博弈", "策略", "纳什均衡"]),
    ]
    thinkers = [
        {"name": "欧拉", "field": "分析/数论", "works": "《无穷分析引论》"},
        {"name": "高斯", "field": "数论/代数", "works": "《算术研究》"},
        {"name": "黎曼", "field": "几何/分析", "works": "黎曼几何、黎曼猜想"},
        {"name": "希尔伯特", "field": "基础/代数", "works": "希尔伯特23问题"},
        {"name": "哥德尔", "field": "逻辑/基础", "works": "不完备定理"},
        {"name": "图灵", "field": "计算理论", "works": "图灵机、可计算性"},
        {"name": "陈省身", "field": "微分几何", "works": "陈示性类"},
        {"name": "陶哲轩", "field": "分析/组合", "works": "调和分析, 21世纪数学家"},
    ]


# ═══════════════════════════════════════════════════════════════
# 2. 物理
# ═══════════════════════════════════════════════════════════════

class PhysicsSense(DomainSense):
    domain = "physics"
    aliases = ["物理", "力学", "量子", "相对论"]
    concepts = [
        KnowledgeEntry("经典力学", "研究宏观物体运动的物理学分支", "经典", ["牛顿", "拉格朗日", "哈密顿"]),
        KnowledgeEntry("量子力学", "描述微观粒子行为的物理理论", "量子", ["波函数", "测不准", "纠缠"]),
        KnowledgeEntry("相对论", "爱因斯坦的时空理论", "相对论", ["狭义相对论", "广义相对论", "时空"]),
        KnowledgeEntry("热力学", "研究热现象和能量转化的物理学", "统计", ["熵", "温度", "能量守恒"]),
        KnowledgeEntry("电磁学", "研究电磁现象的物理学分支", "经典", ["麦克斯韦", "电场", "磁场"]),
        KnowledgeEntry("统计力学", "用统计方法研究多粒子系统", "统计", ["玻尔兹曼", "系综", "相变"]),
        KnowledgeEntry("粒子物理", "研究基本粒子和相互作用的物理学", "量子", ["标准模型", "夸克", "希格斯"]),
        KnowledgeEntry("宇宙学", "研究宇宙起源和演化的学科", "相对论", ["大爆炸", "暗物质", "暗能量"]),
        KnowledgeEntry("凝聚态物理", "研究固体和液体物理性质的学科", "量子", ["超导", "能带", "拓扑绝缘体"]),
        KnowledgeEntry("非线性动力学", "研究非线性系统的复杂行为", "经典", ["混沌", "分形", "孤子"]),
    ]
    thinkers = [
        {"name": "牛顿", "field": "经典力学", "works": "《自然哲学的数学原理》"},
        {"name": "麦克斯韦", "field": "电磁学", "works": "麦克斯韦方程组"},
        {"name": "玻尔兹曼", "field": "统计力学", "works": "熵的统计解释"},
        {"name": "爱因斯坦", "field": "相对论/量子", "works": "相对论、光电效应"},
        {"name": "玻尔", "field": "量子力学", "works": "哥本哈根诠释"},
        {"name": "海森堡", "field": "量子力学", "works": "测不准原理、矩阵力学"},
        {"name": "费曼", "field": "量子电动力学", "works": "费曼图、路径积分"},
        {"name": "杨振宁", "field": "粒子物理", "works": "杨-米尔斯规范场论"},
    ]


# ═══════════════════════════════════════════════════════════════
# 3. 化学
# ═══════════════════════════════════════════════════════════════

class ChemistrySense(DomainSense):
    domain = "chemistry"
    aliases = ["化学", "有机", "无机"]
    concepts = [
        KnowledgeEntry("元素周期律", "元素性质随原子序数周期性变化的规律", "基础", ["元素", "周期表", "原子"]),
        KnowledgeEntry("化学键", "原子间结合力的理论", "理论", ["共价键", "离子键", "金属键"]),
        KnowledgeEntry("化学反应动力学", "研究化学反应速率和机理的学科", "物化", ["速率", "活化能", "催化剂"]),
        KnowledgeEntry("热化学", "研究化学反应中热效应的分支", "物化", ["焓", "熵", "吉布斯自由能"]),
        KnowledgeEntry("有机化学", "研究碳化合物及其反应的化学分支", "有机", ["官能团", "聚合", "立体化学"]),
        KnowledgeEntry("量子化学", "用量子力学方法研究化学问题", "理论", ["分子轨道", "DFT", "ab initio"]),
    ]
    thinkers = [
        {"name": "门捷列夫", "field": "元素周期表", "works": "元素周期律的发现"},
        {"name": "拉瓦锡", "field": "现代化学", "works": "氧化理论、质量守恒"},
        {"name": "鲍林", "field": "量子化学", "works": "化学键的本质"},
        {"name": "克里克", "field": "生物化学", "works": "DNA双螺旋结构"},
    ]


# ═══════════════════════════════════════════════════════════════
# 4. 生物学 (扩展已有鱼类的生态学/基因组学)
# ═══════════════════════════════════════════════════════════════

class BiologySense(DomainSense):
    domain = "biology"
    aliases = ["生物", "生物学", "生态", "基因", "进化"]
    concepts = [
        KnowledgeEntry("进化论", "物种通过自然选择逐渐演化的理论", "进化", ["自然选择", "适应", "物种形成"]),
        KnowledgeEntry("分子生物学", "研究生物大分子结构与功能的学科", "分子", ["DNA", "RNA", "蛋白质"]),
        KnowledgeEntry("基因组学", "研究生物体全部基因的学科", "分子", ["基因组", "测序", "生物信息学"]),
        KnowledgeEntry("细胞生物学", "研究细胞结构与功能的学科", "细胞", ["细胞膜", "线粒体", "细胞周期"]),
        KnowledgeEntry("生态学", "研究生物与环境相互关系的学科", "生态", ["生态系统", "群落", "种群"]),
        KnowledgeEntry("神经科学", "研究神经系统的结构和功能", "神经", ["神经元", "突触", "脑"]),
        KnowledgeEntry("发育生物学", "研究生物体从受精到成体的发育过程", "发育", ["胚胎", "分化", "形态发生"]),
        KnowledgeEntry("鱼类学", "研究鱼类的分类/形态/生态/行为的学科", "动物", ["鱼类", "Ichthyology"]),
        KnowledgeEntry("保护生物学", "研究生物多样性保护的学科", "生态", ["濒危", "栖息地", "保护"]),
        KnowledgeEntry("系统发生学", "研究物种间进化关系", "进化", ["系统树", "分类", "支序"]),
    ]
    thinkers = [
        {"name": "达尔文", "field": "进化论", "works": "《物种起源》"},
        {"name": "孟德尔", "field": "遗传学", "works": "遗传定律"},
        {"name": "沃森/克里克", "field": "分子生物学", "works": "DNA双螺旋"},
        {"name": "威尔逊", "field": "社会生物学", "works": "《社会生物学:新的综合》"},
        {"name": "洛伦兹", "field": "动物行为学", "works": "印刻行为、动物行为学"},
    ]


# ═══════════════════════════════════════════════════════════════
# 5. 计算机科学
# ═══════════════════════════════════════════════════════════════

class ComputerScienceSense(DomainSense):
    domain = "computer_science"
    aliases = ["计算机", "cs", "编程", "算法", "AI"]
    concepts = [
        KnowledgeEntry("算法", "解决问题的明确定义的计算步骤", "理论", ["排序", "搜索", "图算法", "DP"]),
        KnowledgeEntry("数据结构", "组织和存储数据的方式", "理论", ["数组", "链表", "树", "哈希"]),
        KnowledgeEntry("计算理论", "研究计算本质和极限的学科", "理论", ["自动机", "可计算性", "复杂度"]),
        KnowledgeEntry("机器学习", "让计算机从数据中学习的AI方法", "AI", ["监督", "无监督", "强化学习"]),
        KnowledgeEntry("深度学习", "使用多层神经网络的学习方法", "AI", ["CNN", "RNN", "Transformer"]),
        KnowledgeEntry("操作系统", "管理计算机硬件资源的系统软件", "系统", ["进程", "内存", "文件系统"]),
        KnowledgeEntry("编程语言理论", "研究程序设计语言设计和分析的学科", "理论", ["类型系统", "语义", "编译"]),
        KnowledgeEntry("软件工程", "系统化开发和维护软件的工程学科", "工程", ["设计模式", "测试", "DevOps"]),
        KnowledgeEntry("计算机网络", "研究计算机间通信的学科", "系统", ["TCP/IP", "HTTP", "拓扑"]),
        KnowledgeEntry("数据库", "系统化管理数据的软件", "系统", ["SQL", "NoSQL", "事务"]),
        KnowledgeEntry("密码学", "研究安全通信的数学方法", "理论", ["加密", "签名", "零知识"]),
        KnowledgeEntry("人机交互", "研究人与计算机交互方式的学科", "工程", ["UI", "UX", "可用性"]),
    ]
    thinkers = [
        {"name": "图灵", "field": "计算理论", "works": "图灵机、图灵测试"},
        {"name": "冯·诺依曼", "field": "计算机架构", "works": "冯·诺依曼架构"},
        {"name": "香农", "field": "信息论", "works": "信息论、数字电路"},
        {"name": "高德纳", "field": "算法/程序设计", "works": "《计算机程序设计艺术》"},
        {"name": "乔姆斯基", "field": "形式语言", "works": "乔姆斯基层级"},
        {"name": "明斯基", "field": "AI", "works": "感知机、框架理论"},
        {"name": "辛顿", "field": "深度学习", "works": "反向传播、深度信念网络"},
        {"name": "姚期智", "field": "计算理论", "works": "姚氏最小元定理"},
    ]


# ═══════════════════════════════════════════════════════════════
# 6. 心理学
# ═══════════════════════════════════════════════════════════════

class PsychologySense(DomainSense):
    domain = "psychology"
    aliases = ["心理", "认知", "行为"]
    concepts = [
        KnowledgeEntry("认知心理学", "研究心理过程如注意/记忆/推理的学科", "认知", ["注意", "记忆", "决策"]),
        KnowledgeEntry("行为心理学", "研究可观察行为的心理学流派", "行为", ["条件反射", "强化", "惩罚"]),
        KnowledgeEntry("发展心理学", "研究人类从出生到死亡的心理变化", "发展", ["皮亚杰", "依恋", "生命周期"]),
        KnowledgeEntry("社会心理学", "研究个体在社会环境中行为的学科", "社会", ["从众", "偏见", "群体"]),
        KnowledgeEntry("神经心理学", "研究脑与行为关系的学科", "神经", ["脑区", "认知神经", "fMRI"]),
        KnowledgeEntry("人格心理学", "研究个体差异和人格结构的学科", "人格", ["大五", "特质", "自我"]),
        KnowledgeEntry("临床心理学", "研究和治疗心理障碍的学科", "临床", ["抑郁症", "焦虑", "CBT"]),
    ]
    thinkers = [
        {"name": "弗洛伊德", "field": "精神分析", "works": "《梦的解析》"},
        {"name": "荣格", "field": "分析心理学", "works": "集体无意识、原型"},
        {"name": "斯金纳", "field": "行为主义", "works": "操作条件反射"},
        {"name": "皮亚杰", "field": "发展心理学", "works": "认知发展阶段理论"},
        {"name": "卡尼曼", "field": "行为经济学", "works": "前景理论、快慢思考"},
    ]


# ═══════════════════════════════════════════════════════════════
# 7. 哲学
# ═══════════════════════════════════════════════════════════════

class PhilosophySense(DomainSense):
    domain = "philosophy"
    aliases = ["哲学", "形而上学", "认识论", "伦理"]
    concepts = [
        KnowledgeEntry("形而上学", "研究实在本质的哲学分支", "本体论", ["存在", "实体", "本体"]),
        KnowledgeEntry("认识论", "研究知识和信念的哲学分支", "认识论", ["知识", "信念", "证成", "怀疑"]),
        KnowledgeEntry("伦理学", "研究道德和善恶的哲学分支", "价值论", ["道德", "义务", "功利", "美德"]),
        KnowledgeEntry("逻辑学", "研究有效推理形式的哲学分支", "逻辑", ["演绎", "归纳", "谬误"]),
        KnowledgeEntry("现象学", "研究意识和经验结构的哲学方法", "欧陆", ["意向性", "胡塞尔", "此在"]),
        KnowledgeEntry("分析哲学", "以语言分析为方法的哲学传统", "分析", ["弗雷格", "罗素", "维特根斯坦"]),
        KnowledgeEntry("辩证法", "通过矛盾和对立统一理解发展的方法", "方法", ["正题", "反题", "合题"]),
        KnowledgeEntry("科学哲学", "研究科学方法和科学知识的哲学", "科学", ["证伪", "范式", "研究纲领"]),
        KnowledgeEntry("心灵哲学", "研究意识、心智和心灵的本质", "心灵", ["心身问题", "意向性", "感受质"]),
        KnowledgeEntry("语言哲学", "研究语言意义和指称的哲学", "语言", ["语义", "语用", "指称"]),
    ]
    thinkers = [
        {"name": "柏拉图", "field": "形而上学", "works": "《理想国》、理型论"},
        {"name": "亚里士多德", "field": "逻辑/伦理", "works": "《形而上学》《尼各马可伦理学》"},
        {"name": "康德", "field": "认识论/伦理", "works": "《纯粹理性批判》《实践理性批判》"},
        {"name": "黑格尔", "field": "辩证法", "works": "《精神现象学》"},
        {"name": "马克思", "field": "辩证唯物", "works": "《资本论》《德意志意识形态》"},
        {"name": "尼采", "field": "存在主义", "works": "《查拉图斯特拉如是说》"},
        {"name": "维特根斯坦", "field": "语言哲学", "works": "《逻辑哲学论》《哲学研究》"},
        {"name": "海德格尔", "field": "存在主义", "works": "《存在与时间》"},
        {"name": "罗素", "field": "分析哲学", "works": "《数学原理》"},
        {"name": "福柯", "field": "后结构主义", "works": "《词与物》《规训与惩罚》"},
    ]


# ═══════════════════════════════════════════════════════════════
# 7b. 中国哲学: 道家/儒家/儒释道三教合一
# ═══════════════════════════════════════════════════════════════

class ChinesePhilosophySense(DomainSense):
    domain = "chinese_philosophy"
    aliases = ["道家", "儒家", "儒释道", "中国哲学", "老子", "孔子", "庄子", "禅"]
    concepts = [
        # ── 道家 ──
        KnowledgeEntry("道", "宇宙万物的本源和运行规律", "道家", ["道可道", "非常道", "自然"]),
        KnowledgeEntry("无为", "顺应自然规律而不妄为的实践原则", "道家", ["无为而治", "自然", "不争"]),
        KnowledgeEntry("阴阳", "宇宙中对立统一的两大基本力量", "道家/儒家", ["太极", "阴阳平衡", "五行"]),
        KnowledgeEntry("五行", "金木水火土五种基本元素及其相生相克", "道家/中医", ["相生", "相克", "五行生克"]),
        KnowledgeEntry("气", "构成宇宙万物的基本能量/物质", "道家/中医", ["精气神", "元气", "气功"]),
        KnowledgeEntry("自然", "道的本质特征: 自己如此, 自然而然", "道家", ["道法自然", "无为"]),
        # ── 儒家 ──
        KnowledgeEntry("仁", "儒家核心德性: 爱人、推己及人", "儒家", ["仁者爱人", "己所不欲勿施于人"]),
        KnowledgeEntry("礼", "社会秩序和行为规范的总和", "儒家", ["礼节", "礼仪", "礼制"]),
        KnowledgeEntry("中庸", "不偏不倚、调和折中的处世哲学", "儒家", ["中和", "中庸之道", "过犹不及"]),
        KnowledgeEntry("天命", "天的意志和命令, 儒家伦理的形上基础", "儒家", ["天命之谓性", "知天命"]),
        KnowledgeEntry("修身齐家治国平天下", "儒家八条目的社会实践路径", "儒家", ["大学", "格物致知", "诚意正心"]),
        KnowledgeEntry("四书五经", "儒家核心经典体系", "儒家", ["论语", "孟子", "大学", "中庸", "诗经", "尚书"]),
        # ── 儒释道三教合一 ──
        KnowledgeEntry("儒释道三教合一", "宋明以后儒佛道三家思想融合的趋势", "三教", ["三教合一", "儒释道", "三教合流"]),
        KnowledgeEntry("禅宗", "佛教中国化的产物, 直指人心见性成佛", "佛教中国化", ["禅", "顿悟", "公案", "慧能"]),
        KnowledgeEntry("理学", "宋明时期融合儒释道的新儒学", "宋明理学", ["程朱理学", "陆王心学", "天理"]),
        KnowledgeEntry("心学", "陆九渊王守仁开创的'心即理'学派", "宋明理学", ["心即理", "致良知", "知行合一"]),
        KnowledgeEntry("周易", "群经之首, 包含哲学/占筮/宇宙观的经典", "儒家/道家", ["易经", "八卦", "卦象"]),
        KnowledgeEntry("道法自然", "道的根本特征是自然而然", "道家", ["自然", "无为"]),
        KnowledgeEntry("知行合一", "知识和行动不可分割, 真知必能行", "儒家/心学", ["王阳明", "致良知"]),
    ]
    thinkers = [
        {"name": "老子", "field": "道家", "works": "《道德经》"},
        {"name": "孔子", "field": "儒家", "works": "《论语》"},
        {"name": "庄子", "field": "道家", "works": "《庄子》(逍遥游、齐物论)"},
        {"name": "孟子", "field": "儒家", "works": "《孟子》(性善论、仁政)"},
        {"name": "慧能", "field": "禅宗", "works": "《六祖坛经》"},
        {"name": "朱熹", "field": "理学", "works": "《四书章句集注》"},
        {"name": "王阳明", "field": "心学", "works": "《传习录》(致良知)"},
        {"name": "苏轼", "field": "儒释道融合", "works": "融合三家思想的文学与哲学"},
    ]


# ═══════════════════════════════════════════════════════════════
# 8. 马克思主义
# ═══════════════════════════════════════════════════════════════

class MarxismSense(DomainSense):
    domain = "marxism"
    aliases = ["马克思", "马克思主义", "辩证唯物", "历史唯物"]
    concepts = [
        KnowledgeEntry("辩证唯物主义", "马克思和恩格斯创立的唯物辩证法哲学", "哲学", ["唯物", "辩证", "实践"]),
        KnowledgeEntry("历史唯物主义", "用物质生产方式解释历史发展的理论", "历史", ["生产力", "生产关系", "阶级"]),
        KnowledgeEntry("政治经济学", "研究社会生产关系和经济运行规律的学科", "经济", ["资本", "剩余价值", "商品"]),
        KnowledgeEntry("剩余价值理论", "揭示资本家剥削工人劳动的理论", "经济", ["剩余价值", "剥削", "资本积累"]),
        KnowledgeEntry("阶级斗争", "不同阶级之间基于利益冲突的斗争", "社会", ["阶级", "革命", "无产阶级"]),
        KnowledgeEntry("异化理论", "劳动者与其劳动产品相分离的理论", "哲学", ["异化", "劳动", "物化"]),
        KnowledgeEntry("科学社会主义", "关于无产阶级解放条件的学说", "政治", ["社会主义", "共产主义", "革命"]),
        KnowledgeEntry("实践论", "强调实践是认识基础的马克思主义认识论", "认识论", ["实践", "认识", "真理"]),
        KnowledgeEntry("矛盾论", "研究事物矛盾普遍性和特殊性的理论", "方法", ["矛盾", "主要矛盾", "转化"]),
        KnowledgeEntry("实事求是", "从实际出发探索客观规律的思想方法", "方法", ["实际", "规律", "调查"]),
    ]
    thinkers = [
        {"name": "马克思", "field": "哲学/政治经济", "works": "《资本论》《共产党宣言》"},
        {"name": "恩格斯", "field": "哲学/自然辩证", "works": "《反杜林论》《自然辩证法》"},
        {"name": "列宁", "field": "帝国主义论", "works": "《帝国主义是资本主义的最高阶段》"},
        {"name": "毛泽东", "field": "实践论/矛盾论", "works": "《实践论》《矛盾论》"},
        {"name": "葛兰西", "field": "文化霸权", "works": "《狱中札记》"},
        {"name": "卢卡奇", "field": "物化理论", "works": "《历史与阶级意识》"},
    ]


# ═══════════════════════════════════════════════════════════════
# 9. 经济学
# ═══════════════════════════════════════════════════════════════

class EconomicsSense(DomainSense):
    domain = "economics"
    aliases = ["经济", "经济学", "市场", "金融"]
    concepts = [
        KnowledgeEntry("微观经济学", "研究个体经济单位行为的学科", "微观", ["供需", "价格", "市场"]),
        KnowledgeEntry("宏观经济学", "研究经济总体运行的学科", "宏观", ["GDP", "通胀", "失业"]),
        KnowledgeEntry("制度经济学", "研究制度对经济行为影响的学科", "制度", ["产权", "交易成本", "制度变迁"]),
        KnowledgeEntry("行为经济学", "结合心理学研究经济决策的学科", "行为", ["偏差", "前景理论", "助推"]),
        KnowledgeEntry("计量经济学", "用统计方法检验经济理论的学科", "方法", ["回归", "因果推断", "时间序列"]),
        KnowledgeEntry("发展经济学", "研究经济发展和贫困问题的学科", "发展", ["增长", "不平等", "贫困"]),
        KnowledgeEntry("国际经济学", "研究跨国经济关系的学科", "国际", ["贸易", "汇率", "全球化"]),
        KnowledgeEntry("货币经济学", "研究货币和银行体系的学科", "宏观", ["货币政策", "利率", "银行"]),
    ]
    thinkers = [
        {"name": "亚当·斯密", "field": "古典经济学", "works": "《国富论》"},
        {"name": "凯恩斯", "field": "宏观经济学", "works": "《就业、利息和货币通论》"},
        {"name": "马克思", "field": "政治经济学", "works": "《资本论》"},
        {"name": "哈耶克", "field": "奥地利学派", "works": "《通往奴役之路》"},
        {"name": "萨缪尔森", "field": "新古典综合", "works": "《经济学》教科书"},
        {"name": "科斯", "field": "制度经济学", "works": "企业的性质、社会成本问题"},
        {"name": "阿马蒂亚·森", "field": "发展经济学", "works": "贫困与饥荒、能力方法"},
        {"name": "皮凯蒂", "field": "不平等研究", "works": "《21世纪资本论》"},
    ]


# ═══════════════════════════════════════════════════════════════
# 10. 文学
# ═══════════════════════════════════════════════════════════════

class LiteratureSense(DomainSense):
    domain = "literature"
    aliases = ["文学", "小说", "诗歌", "戏剧"]
    concepts = [
        KnowledgeEntry("中国古典文学", "从先秦到清末的中国文学传统", "中国", ["诗经", "楚辞", "唐诗", "宋词"]),
        KnowledgeEntry("西方文学", "从古希腊到现代的西方文学传统", "西方", ["荷马", "莎士比亚", "但丁"]),
        KnowledgeEntry("现代主义文学", "20世纪初反传统文学流派", "现代", ["意识流", "卡夫卡", "乔伊斯"]),
        KnowledgeEntry("后现代文学", "对现代主义进行反思和解构的文学", "后现代", ["元叙事", "戏仿", "拼接"]),
        KnowledgeEntry("文学理论", "研究文学本质和阐释方法的学科", "理论", ["形式主义", "结构主义", "解构"]),
        KnowledgeEntry("科幻文学", "基于科学想象的文学类型", "类型", ["科幻", "赛博朋克", "太空歌剧"]),
        KnowledgeEntry("魔幻现实主义", "融合现实与幻想的文学流派", "流派", ["马尔克斯", "博尔赫斯"]),
    ]
    thinkers = [
        {"name": "曹雪芹", "field": "中国古典小说", "works": "《红楼梦》"},
        {"name": "鲁迅", "field": "中国现代文学", "works": "《呐喊》《彷徨》"},
        {"name": "莎士比亚", "field": "西方戏剧", "works": "《哈姆雷特》《李尔王》"},
        {"name": "托尔斯泰", "field": "俄罗斯文学", "works": "《战争与和平》《安娜·卡列尼娜》"},
        {"name": "博尔赫斯", "field": "后现代文学", "works": "《小径分岔的花园》"},
        {"name": "马尔克斯", "field": "魔幻现实主义", "works": "《百年孤独》"},
        {"name": "卡尔维诺", "field": "后现代文学", "works": "《看不见的城市》"},
    ]


# ═══════════════════════════════════════════════════════════════
# 11. 科幻 (扩展 cosmic.py 的文学基础)
# ═══════════════════════════════════════════════════════════════

class SciFiSense(DomainSense):
    domain = "science_fiction"
    aliases = ["科幻", "sf", "science fiction", "三体"]
    concepts = [
        KnowledgeEntry("三体问题", "刘慈欣的科幻三部曲，探讨文明存亡", "中国科幻", ["三体", "黑暗森林", "死神永生"]),
        KnowledgeEntry("赛博朋克", "高科技低生活的科幻子类型", "子类型", ["神经漫游者", "银翼杀手", "攻壳"]),
        KnowledgeEntry("太空歌剧", "以太空旅行为背景的宏大科幻", "子类型", ["基地", "沙丘", "星际迷航"]),
        KnowledgeEntry("时间旅行", "关于穿越时间的故事和理论", "主题", ["时间悖论", "平行世界", "因果"]),
        KnowledgeEntry("AI觉醒", "人工智能获得自我意识的主题", "主题", ["机器人", "意识", "奇点"]),
        KnowledgeEntry("第一类接触", "人类与外星文明首次接触的主题", "主题", ["外星人", "费米悖论", "黑暗森林"]),
        KnowledgeEntry("反乌托邦", "表面完美实则极权的未来社会", "子类型", ["1984", "美丽新世界", "我们"]),
        KnowledgeEntry("生物朋克", "基于生物技术的科幻子类型", "子类型", ["基因工程", "进化", "生化"]),
    ]
    thinkers = [
        {"name": "刘慈欣", "field": "硬科幻", "works": "《三体》三部曲、《流浪地球》"},
        {"name": "阿西莫夫", "field": "科幻", "works": "《基地》系列、《机器人》系列"},
        {"name": "克拉克", "field": "硬科幻", "works": "《2001太空漫游》、《与拉玛相会》"},
        {"name": "海因莱因", "field": "社会科幻", "works": "《星船伞兵》、《异乡异客》"},
        {"name": "莱姆", "field": "哲学科幻", "works": "《索拉里斯星》、《机器人大师》"},
        {"name": "吉布森", "field": "赛博朋克", "works": "《神经漫游者》"},
        {"name": "赫胥黎", "field": "反乌托邦", "works": "《美丽新世界》"},
        {"name": "姜峯楠", "field": "语言/认知", "works": "《你一生的故事》《呼吸》"},
        {"name": "王晋康", "field": "中国科幻", "works": "《类人》《生命之歌》"},
        {"name": "韩松", "field": "科幻/寓言", "works": "《地铁》《红色海洋》"},
    ]


# ── 领域注册表 ──

ALL_DOMAIN_SENSES = {
    "math": MathSense,
    "physics": PhysicsSense,
    "chemistry": ChemistrySense,
    "biology": BiologySense,
    "cs": ComputerScienceSense,
    "psychology": PsychologySense,
    "philosophy": PhilosophySense,
    "chinese_philosophy": ChinesePhilosophySense,
    "marxism": MarxismSense,
    "economics": EconomicsSense,
    "literature": LiteratureSense,
    "scifi": SciFiSense,
}

ALL_DOMAIN_NAMES = list(ALL_DOMAIN_SENSES.keys())


def create_all_domains() -> List[DomainSense]:
    """创建所有领域感受器实例。"""
    return [cls() for cls in ALL_DOMAIN_SENSES.values()]


def create_domain(name: str, search_fn=None) -> Optional[DomainSense]:
    """按名称创建单个领域感受器。"""
    cls = ALL_DOMAIN_SENSES.get(name)
    if cls:
        return cls(search_fn=search_fn)
    return None


# ═══════════════════════════════════════════════════════════
# 跨学科拓扑权重矩阵
# 参考: TopoNets (ICLR 2025 Spotlight) — 拓扑组织提升 20% 效率
# ═══════════════════════════════════════════════════════════

# 定义: w_ij = 学科 i 和学科 j 之间的连接强度 [0, 1]
# 自连接 = 1.0 (同一学科内的概念应该嵌入更近)
# 强关联 > 0.6 (频繁共现、互相引用)
# 弱关联 < 0.3 (偶尔交叉)
# 无关联 = 0.0 (几乎不相关)

DOMAIN_TOPOLOGY_MATRIX: Dict[str, Dict[str, float]] = {
    "math":             {"math": 1.0, "physics": 0.8, "cs": 0.7, "economics": 0.4,
                         "philosophy": 0.3, "chemistry": 0.3, "biology": 0.2},
    "physics":          {"physics": 1.0, "math": 0.8, "chemistry": 0.6, "cs": 0.4,
                         "philosophy": 0.4, "scifi": 0.3, "biology": 0.2},
    "chemistry":        {"chemistry": 1.0, "physics": 0.6, "biology": 0.5,
                         "math": 0.3, "philosophy": 0.1},
    "biology":          {"biology": 1.0, "chemistry": 0.5, "psychology": 0.4,
                         "scifi": 0.3, "philosophy": 0.3, "cs": 0.2, "math": 0.2},
    "cs":               {"cs": 1.0, "math": 0.7, "physics": 0.4, "psychology": 0.4,
                         "scifi": 0.4, "philosophy": 0.3, "biology": 0.2},
    "psychology":       {"psychology": 1.0, "biology": 0.4, "cs": 0.4, "philosophy": 0.5,
                         "literature": 0.3, "economics": 0.3},
    "philosophy":       {"philosophy": 1.0, "chinese_philosophy": 0.7, "marxism": 0.6,
                         "psychology": 0.5, "physics": 0.4, "cs": 0.3, "literature": 0.4,
                         "math": 0.3, "biology": 0.3, "scifi": 0.3},
    "chinese_philosophy": {"chinese_philosophy": 1.0, "philosophy": 0.7, "marxism": 0.4,
                           "literature": 0.5, "biology": 0.2},
    "marxism":          {"marxism": 1.0, "philosophy": 0.6, "economics": 0.7,
                         "literature": 0.3, "chinese_philosophy": 0.4},
    "economics":        {"economics": 1.0, "marxism": 0.7, "math": 0.4, "cs": 0.3,
                         "psychology": 0.3, "philosophy": 0.3},
    "literature":       {"literature": 1.0, "scifi": 0.5, "philosophy": 0.4,
                         "chinese_philosophy": 0.5, "psychology": 0.3, "marxism": 0.3},
    "scifi":            {"scifi": 1.0, "literature": 0.5, "cs": 0.4, "physics": 0.3,
                         "philosophy": 0.3, "biology": 0.3},
}


def get_domain_topology(domain_a: str, domain_b: str) -> float:
    """获取两个学科之间的拓扑连接强度。

    参考 TopoNets: 相邻学科在概念空间中嵌入更近。
    """
    row = DOMAIN_TOPOLOGY_MATRIX.get(domain_a, {})
    w = row.get(domain_b, 0.0)
    if w == 0.0:
        # 检查反向
        row = DOMAIN_TOPOLOGY_MATRIX.get(domain_b, {})
        w = row.get(domain_a, 0.0)
    return w


def get_domain_neighbors(domain: str, threshold: float = 0.3) -> List[Tuple[str, float]]:
    """获取指定学科的强关联邻居学科。

    TopoNets 原理: 拓扑组织意味着邻居学科共享计算策略。
    """
    row = DOMAIN_TOPOLOGY_MATRIX.get(domain, {})
    neighbors = [(d, w) for d, w in row.items() if d != domain and w >= threshold]
    neighbors.sort(key=lambda x: x[1], reverse=True)
    return neighbors
