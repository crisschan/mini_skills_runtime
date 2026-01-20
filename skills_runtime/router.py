"""
Skill Router

负责根据用户输入路由到合适的 Skill
支持 Embedding Matching 策略
"""

from typing import List, Dict, Any, Optional, Tuple
from skills_runtime.models import Skill


class RouterResult:
    """路由结果"""

    def __init__(self, skill_id: str, confidence: float, strategy: str, metadata: Dict[str, Any] = None):
        self.skill_id = skill_id
        self.confidence = confidence
        self.strategy = strategy
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "skill_id": self.skill_id,
            "confidence": self.confidence,
            "strategy": self.strategy,
            **self.metadata,
        }


class SkillRouter:
    """Skill 路由器"""

    def __init__(self, skills: Dict[str, Skill]):
        """
        初始化路由器

        Args:
            skills: Skill 字典 {skill_id: Skill}
        """
        self.skills = skills
        self.router_model = "simple-matcher-v1"

    def route(self, user_input: str, top_k: int = 3) -> List[RouterResult]:
        """
        路由用户输入到合适的 Skill

        Args:
            user_input: 用户输入
            top_k: 返回前 k 个结果

        Returns:
            RouterResult 列表（按置信度降序）
        """
        results = []

        # 简单匹配策略（实际可以使用 embedding）
        for skill_id, skill in self.skills.items():
            score = self._calculate_score(user_input, skill)
            if score > 0:
                results.append(RouterResult(
                    skill_id=skill_id,
                    confidence=score,
                    strategy="keyword",
                ))

        # 按分数排序
        results.sort(key=lambda x: x.confidence, reverse=True)

        return results[:top_k]

    def route_single(self, user_input: str) -> Optional[RouterResult]:
        """
        路由到单个最佳 Skill

        Args:
            user_input: 用户输入

        Returns:
            最佳 RouterResult
        """
        results = self.route(user_input, top_k=1)
        return results[0] if results else None

    def _calculate_score(self, user_input: str, skill: Skill) -> float:
        """
        计算输入与 Skill 的匹配分数

        Args:
            user_input: 用户输入
            skill: Skill 定义

        Returns:
            匹配分数 [0, 1]
        """
        score = 0.0
        user_input_lower = user_input.lower()

        # 检查 triggers（优先级高）
        if skill.routing and skill.routing.triggers:
            for trigger in skill.routing.triggers:
                if trigger.lower() in user_input_lower:
                    score += 0.7  # 触发词匹配给高分
                    if score > 0.9:
                        break

        # 检查 description（子串匹配，适合中文）
        if skill.metadata.description:
            desc_lower = skill.metadata.description.lower()
            # 计算子串覆盖率
            total_chars = len(desc_lower)
            matched_chars = 0
            for char in desc_lower:
                if char in user_input_lower:
                    matched_chars += 1
            desc_overlap = matched_chars / max(total_chars, 1)
            score += desc_overlap * 0.3

        return min(score, 1.0)

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """
        获取指定 Skill

        Args:
            skill_id: Skill ID

        Returns:
            Skill 对象
        """
        return self.skills.get(skill_id)

    def list_skills(self) -> List[str]:
        """列出所有 Skill ID"""
        return list(self.skills.keys())
