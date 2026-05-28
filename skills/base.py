from abc import ABC, abstractmethod


class BaseSkill(ABC):
    """所有 Skill 必须实现的基类。"""

    name: str = ""
    description: str = ""

    @abstractmethod
    async def execute(self, params: dict) -> dict:
        """执行技能逻辑，返回结果 dict。"""
        ...
