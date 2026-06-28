"""
输出解析工具
从 LLM 响应中提取结构化数据
"""

import json
import re


class Parser:
    """统一的 LLM 输出解析器"""

    @staticmethod
    def parse_json(text: str) -> dict:
        """
        从 LLM 输出中解析 JSON，兼容多种格式：
        - 纯 JSON 字符串
        - markdown 代码块包裹的 JSON
        - 被自然语言包围的 JSON
        """
        return Parser._extract_json(text)

    @staticmethod
    def _extract_json(text: str) -> dict:
        """从文本中提取 JSON 对象"""
        text = text.strip()

        # 1. 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. 提取 markdown 代码块
        json_patterns = [
            r"```json\s*\n(.*?)\n```",
            r"```\s*\n(.*?)\n```",
            r"```json(.*?)```",
            r"```(.*?)```",
        ]
        for pattern in json_patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1).strip())
                except json.JSONDecodeError:
                    continue

        # 3. 提取 {} 包围的内容（最外层）
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass

        raise ValueError(f"无法从文本中解析 JSON:\n{text[:500]}")

    @staticmethod
    def parse_paragraph_sections(text: str) -> dict:
        """
        解析首轮控制器的段落输出格式：
        Paragraph 1: ...
        Paragraph 2: ...
        Paragraph 3: ...
        Summary: ...
        Instruction 1: ...
        Instruction 2: ...
        """
        result = {}

        # 提取段落
        p1 = Parser._extract_section(text, r"Paragraph\s*1\s*[:：]", r"(?=Paragraph\s*2)")
        p2 = Parser._extract_section(text, r"Paragraph\s*2\s*[:：]", r"(?=Paragraph\s*3)")
        p3 = Parser._extract_section(text, r"Paragraph\s*3\s*[:：]", r"(?=Summary)")

        paragraphs = []
        if p1:
            paragraphs.append(p1.strip())
        if p2:
            paragraphs.append(p2.strip())
        if p3:
            paragraphs.append(p3.strip())

        result["paragraph"] = "\n\n".join(paragraphs)

        # 提取 summary
        summary = Parser._extract_section(text, r"Summary\s*[:：]", r"(?=Instruction\s*1)")
        if summary:
            result["summary"] = summary.strip()

        # 提取指令
        i1 = Parser._extract_section(text, r"Instruction\s*1\s*[:：]", r"(?=Instruction\s*2)")
        if i1:
            result["instruction_1"] = i1.strip()

        i2 = Parser._extract_section(text, r"Instruction\s*2\s*[:：]", r"$")
        if i2:
            result["instruction_2"] = i2.strip()

        return result

    @staticmethod
    def _extract_section(text: str, start_pattern: str, end_pattern: str) -> str:
        """提取两个正则之间的文本内容"""
        match = re.search(start_pattern, text)
        if not match:
            return ""
        start_pos = match.end()

        if end_pattern == "$":
            return text[start_pos:].strip()

        end_match = re.search(end_pattern, text[start_pos:])
        if end_match:
            return text[start_pos:start_pos + end_match.start()]
        else:
            return text[start_pos:].strip()

    @staticmethod
    def parse_controller_output(text: str, is_first_round: bool = False) -> dict:
        """
        解析控制器输出。
        首轮为段落格式，后续轮次为 JSON 格式。
        """
        if is_first_round:
            # 首轮：段落格式，但也可能包含 JSON
            try:
                parsed = Parser.parse_json(text)
                if "paragraph" in parsed:
                    return parsed
            except (ValueError, json.JSONDecodeError):
                pass

            # 回退到段落解析
            sections = Parser.parse_paragraph_sections(text)
            if sections.get("paragraph"):
                return sections

            # 最后的回退：整个文本作为段落
            return {"paragraph": text, "summary": "", "instruction_1": "", "instruction_2": ""}
        else:
            # 后续轮次：JSON 格式
            return Parser.parse_json(text)

    @staticmethod
    def parse_critic_output(text: str) -> dict:
        """解析评论家输出，JSON 格式"""
        try:
            return Parser.parse_json(text)
        except (ValueError, json.JSONDecodeError):
            # 回退：将文本作为 paragraph，返回空审查
            return {
                "paragraph": text,
                "memory": "",
                "instruction_1": "",
                "instruction_2": "",
                "reviews": {"coherence": {"issues": ["解析失败"], "improvements": ["格式不符合预期"]},
                            "bias": {"issues": [], "improvements": []},
                            "omission": {"issues": [], "improvements": []}}
            }

    @staticmethod
    def parse_simulator_output(text: str) -> dict:
        """解析模拟器输出"""
        try:
            return Parser.parse_json(text)
        except (ValueError, json.JSONDecodeError):
            # 回退：尝试提取关键词
            reason = text[:200] if text else "无理由"
            selected = 2  # 默认选健康
            if "指令1" in text or "instruction 1" in text.lower():
                selected = 1
            return {
                "reason": reason,
                "selected": selected,
                "score": 1 if selected == 1 else 0,
            }
